"""VERIFY -- 실행된 행동의 사후조건이 그 뒤의 State 에서 성립하나 (BD-31 · BD-99, baseline#9 CMD-H2).

    verify(command, ...) -> VerificationRecord        순수 함수. 같은 입력 -> 같은 기록(같은 id)

판정(위에서부터 처음 맞는 것):
    1. 사후조건이 없다                                   -> UNKNOWN / NO_SPEC              final
    2. 모든 절이 쓸 만하고 참이다                         -> VERIFIED / MET                 final (창이 열려 있어도)
    3. 판정 시각 < 창 끝                                 -> PENDING / WINDOW_OPEN
    4. 창이 닫혔고, 쓸 만한 근거로 거짓인 절이 하나라도 있다 -> NOT_VERIFIED / UNMET_AT_CLOSE  final
    5. 창이 닫혔고 나머지(근거가 모자람)                   -> UNKNOWN / 첫 모자란 절의 까닭    final

근거가 **쓸 만하다** = (차례로 보고 처음 걸린 것이 까닭)
    - 실체를 풀 수 있다                                        아니면 UNRESOLVED_ENTITY
    - 관측 시각이 있다                                          아니면 NO_POST_OBSERVATION
    - 시각 기준이 unix_ms 다 (창과 같은 기준, BD-33 · BD-90)      아니면 TIME_BASE_MISMATCH
    - 관측 시각 ≥ 명령 발행 시각 -- **명령 전 관측은 효과의 근거가 아니다**  아니면 NO_POST_OBSERVATION
    - 관측 시각 ≤ 판정 시각                                      아니면 NOT_USABLE
    - 유효성 OBSERVED · DERIVED · INFERRED, 신선도 FRESH · PERMANENT  아니면 NOT_USABLE
술어는 쓸 만한 값에만 적용한다(MS `holds` 는 값이 없으면 거짓이라 '모름' 이 '거짓' 이 된다).

**실행기의 결과(ActionOutcome = L0 action.result)는 판정에 들어가지 않는다.** "됐다" 는 관측일 뿐이다(DATA_FLOW §7).
`outcome` 을 받는 것은 명령과 같은 것을 가리키는지 확인하려는 것뿐이고, 기록에는 `outcome_ref`(사건 id)만 남는다.

근거는 **값 없이 참조**로 남긴다(실체 · 상태 · 관측 시각 · 시각 기준, BD-99). 재생은 State 이력(덧붙이기)으로 한다.
"""
from __future__ import annotations

import math
import re
from collections.abc import Mapping
from dataclasses import dataclass, fields

from action import ActionCommand, ActionOutcome, ContractError
from action.canonical import check_json, digest
from action.forms import COMMAND_ID, POLICY_REF

from . import predicate

SCHEMA = "verification-record/1"
RESULTS = ("PENDING", "VERIFIED", "NOT_VERIFIED", "UNKNOWN")
# 까닭 -> 그 까닭이 낼 수 있는 결과. 닫힌 낱말이다
REASONS = {
    "MET": "VERIFIED",
    "WINDOW_OPEN": "PENDING",
    "UNMET_AT_CLOSE": "NOT_VERIFIED",
    "NO_SPEC": "UNKNOWN",
    "UNRESOLVED_ENTITY": "UNKNOWN",
    "NO_POST_OBSERVATION": "UNKNOWN",
    "TIME_BASE_MISMATCH": "UNKNOWN",
    "NOT_USABLE": "UNKNOWN",
}
TIME_BASE = "unix_ms"
USABLE_STATUS = ("OBSERVED", "DERIVED", "INFERRED")       # Sensor state-export/2 의 유효성 가운데 '지금 값' 인 것
USABLE_FRESHNESS = ("FRESH", "PERMANENT")                 # UNTIMED 는 창과 견줄 수 없다 · STALE 은 쓰지 않는다
ROLES = ("agent", "task", "runtime")                      # state-export `subjects(run)` 의 역할
VER_ID = re.compile(r"^ver-[0-9a-f]{16}$")


def action_entity(run: str, command_id: str) -> str:
    """`action_state` 가 서는 실체 id -- `action:<run>:<command_id>` (BD-32 꼴, BD-99)."""
    return f"action:{run}:{command_id}"


# ── 칸 검사 ────────────────────────────────────────────────────────────────

def _is_num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


def _clause_errors(i, c) -> "list[str]":
    p = f"postcondition[{i}]"
    if not isinstance(c, dict) or set(c) != {"entity", "pred"}:
        return [f"{p}: 칸은 entity · pred 둘뿐이어야 한다 ({c!r})"]
    e = []
    ent = c["entity"]
    if not isinstance(ent, str) or not ent:
        e.append(f"{p}.entity: 빈 것 아닌 문자열이어야 한다")
    elif ent.startswith("$") and ent != "$target" and ent not in {f"$run.{r}" for r in ROLES}:
        e.append(f"{p}.entity: 모르는 지정 {ent!r} (기대 $target · $run.agent · $run.task · $run.runtime · 실체 id)")
    e += [f"{p}.pred: {x}" for x in predicate.check(c["pred"])]
    e += [f"{p}: {x}" for x in check_json(c, p)]
    return e


def _evidence_errors(i, ev) -> "list[str]":
    p = f"evidence[{i}]"
    keys = {"clause", "entity", "state", "observed_at", "time_base"}
    if not isinstance(ev, dict) or set(ev) != keys:
        return [f"{p}: 칸은 {sorted(keys)} 이어야 한다 -- 값은 싣지 않는다 ({ev!r})"]
    e = []
    if ev["clause"] != i:
        e.append(f"{p}.clause: {ev['clause']!r} (기대 {i})")
    if ev["entity"] is not None and (not isinstance(ev["entity"], str) or not ev["entity"]):
        e.append(f"{p}.entity: 문자열 또는 null")
    if not isinstance(ev["state"], str) or not ev["state"]:
        e.append(f"{p}.state: 빈 것 아닌 문자열")
    if ev["observed_at"] is not None and not _is_num(ev["observed_at"]):
        e.append(f"{p}.observed_at: 수 또는 null")
    if ev["time_base"] is not None and not isinstance(ev["time_base"], str):
        e.append(f"{p}.time_base: 문자열 또는 null")
    return e


# ── 꼴 ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class VerificationRecord:
    """VERIFY 한 번의 판정. 닫힌 꼴이고 id 는 내용 해시다(action-contract/1 과 같은 방식)."""
    command_id: str          # = ActionCommand.command_id = L0 action.dispatch/result.action_ref
    run: str                 # 실행 id(실체 id 의 범위). action_state 의 실체 = action:<run>:<command_id>
    spec: "str | None"       # "<ActionSpec 이름>@<판본>" -- 어느 사후조건으로 판정했나. 없으면 None(NO_SPEC)
    postcondition: tuple     # 절의 논리곱. 절 = {"entity": 지정, "pred": [상태, 연산, 값]}
    window: dict             # {"start_ms": 명령 issued_at, "end_ms": start + ActionSpec 의 창, "time_base": "unix_ms"}
    outcome_ref: "str | None"  # L0 action.result 사건 id. 판정에 쓰지 않는다
    evidence: tuple          # 절마다 하나 {"clause", "entity", "state", "observed_at", "time_base"} -- 값 없음
    result: str
    reason: str
    evaluated_at: float      # unix_ms
    final: bool              # PENDING 만 False
    schema: str = SCHEMA

    ID = "verification_id"
    ID_PREFIX = "ver-"

    def __post_init__(self):
        for k in ("postcondition", "evidence"):
            v = getattr(self, k)
            if isinstance(v, list):
                object.__setattr__(self, k, tuple(v))
        errs = self._errors()
        if errs:
            raise ContractError(type(self).__name__, errs)

    def _errors(self) -> "list[str]":
        e = []
        if self.schema != SCHEMA:
            e.append(f"schema: {self.schema!r} (기대 {SCHEMA!r})")
        if not isinstance(self.command_id, str) or not COMMAND_ID.match(self.command_id):
            e.append(f"command_id: 꼴이 아니다 {self.command_id!r}")
        if not isinstance(self.run, str) or not self.run.strip():
            e.append("run: 빈 것 아닌 문자열이어야 한다")
        if self.spec is not None and (not isinstance(self.spec, str) or not POLICY_REF.match(self.spec)):
            e.append(f"spec: \"<이름>@<판본>\" 또는 null 이어야 한다 ({self.spec!r})")
        if not isinstance(self.postcondition, tuple):
            e.append("postcondition: 목록이어야 한다")
        else:
            for i, c in enumerate(self.postcondition):
                e += _clause_errors(i, c)
        w = self.window
        if not isinstance(w, dict) or set(w) != {"start_ms", "end_ms", "time_base"}:
            e.append(f"window: 칸은 start_ms · end_ms · time_base 이어야 한다 ({w!r})")
        else:
            if w["time_base"] != TIME_BASE:
                e.append(f"window.time_base: {w['time_base']!r} (기대 {TIME_BASE!r})")
            if not (_is_num(w["start_ms"]) and _is_num(w["end_ms"])) or w["start_ms"] < 0 or w["end_ms"] <= w["start_ms"]:
                e.append(f"window: 0 ≤ start_ms < end_ms 인 수여야 한다 ({w!r})")
        if self.outcome_ref is not None and (not isinstance(self.outcome_ref, str) or not self.outcome_ref):
            e.append("outcome_ref: 빈 것 아닌 문자열 또는 null")
        if not isinstance(self.evidence, tuple):
            e.append("evidence: 목록이어야 한다")
        else:
            if isinstance(self.postcondition, tuple) and len(self.evidence) != len(self.postcondition):
                e.append(f"evidence: 절마다 하나여야 한다 ({len(self.evidence)} ≠ {len(self.postcondition)})")
            for i, ev in enumerate(self.evidence):
                e += _evidence_errors(i, ev)
        if self.result not in RESULTS:
            e.append(f"result: {self.result!r} (기대 {RESULTS})")
        if self.reason not in REASONS:
            e.append(f"reason: {self.reason!r} (기대 {tuple(REASONS)})")
        elif REASONS[self.reason] != self.result:
            e.append(f"reason {self.reason} 은 결과 {REASONS[self.reason]} 만 낸다 ({self.result!r})")
        if self.reason == "NO_SPEC" and self.postcondition:
            e.append("NO_SPEC 인데 사후조건이 있다")
        if self.reason != "NO_SPEC" and (self.spec is None or not self.postcondition):
            e.append(f"{self.reason}: 사후조건(spec · postcondition)이 있어야 한다")
        if not _is_num(self.evaluated_at):
            e.append(f"evaluated_at: 유한한 수(unix_ms)가 아니다 ({self.evaluated_at!r})")
        elif isinstance(w, dict) and _is_num(w.get("start_ms")) and self.evaluated_at < w["start_ms"]:
            e.append("evaluated_at: 명령 발행보다 이르다")
        if not isinstance(self.final, bool) or self.final != (self.result != "PENDING"):
            e.append(f"final: PENDING 만 False 다 ({self.final!r}, {self.result})")
        if self.result == "PENDING" and _is_num(self.evaluated_at) and isinstance(w, dict) and _is_num(w.get("end_ms")) \
                and self.evaluated_at >= w["end_ms"]:
            e.append("PENDING 인데 창이 닫혔다")
        return e

    # 직렬화 · id -- action-contract/1 과 같다(정준 JSON 은 action.canonical)
    def body(self) -> dict:
        return {f.name: _plain(getattr(self, f.name)) for f in fields(self)}

    def digest(self) -> str:
        return digest(self.body())

    def to_dict(self) -> dict:
        d = self.body()
        d[self.ID] = f"{self.ID_PREFIX}{self.digest()}"
        return d

    @property
    def id(self) -> str:
        return self.to_dict()[self.ID]

    @property
    def entity(self) -> str:
        return action_entity(self.run, self.command_id)

    @classmethod
    def from_dict(cls, d: dict) -> "VerificationRecord":
        name = cls.__name__
        if not isinstance(d, dict):
            raise ContractError(name, [f"객체가 아니다 ({type(d).__name__})"])
        known = {f.name for f in fields(cls)} | {cls.ID}
        errs = [f"모르는 칸 {k!r}" for k in sorted(set(d) - known, key=str)]
        errs += [f"빠진 칸 {k!r}" for k in sorted(known - set(d))]
        if errs:
            raise ContractError(name, errs)
        if not isinstance(d[cls.ID], str) or not VER_ID.match(d[cls.ID]):
            raise ContractError(name, [f"{cls.ID}: 꼴이 아니다 {d[cls.ID]!r}"])
        obj = cls(**{f.name: d[f.name] for f in fields(cls)})
        if d[cls.ID] != obj.id:
            raise ContractError(name, [f"{cls.ID}: 내용과 맞지 않는다 ({d[cls.ID]!r} ≠ {obj.id!r})"])
        return obj


def _plain(v):
    if isinstance(v, tuple):
        return [_plain(x) for x in v]
    if isinstance(v, dict):
        return {k: _plain(x) for k, x in v.items()}
    return v


# ── 판정 ───────────────────────────────────────────────────────────────────

def _resolve(spec_entity: str, command: ActionCommand, subjects: dict) -> "str | None":
    if spec_entity == "$target":
        return command.target
    if spec_entity.startswith("$run."):
        v = subjects.get(spec_entity[len("$run."):])
        return v if isinstance(v, str) and v else None
    return spec_entity


def _usable(read, start, now) -> "str | None":
    """쓸 수 없으면 그 까닭, 쓸 만하면 None. 차례가 곧 까닭의 우선순위다."""
    if not read or read.get("observed_at") is None:
        return "NO_POST_OBSERVATION"
    if read.get("time_base") != TIME_BASE:
        return "TIME_BASE_MISMATCH"
    at = read["observed_at"]
    if not _is_num(at):
        return "NOT_USABLE"
    if at < start:                    # 명령 전에 이미 참이던 값은 효과의 근거가 아니다
        return "NO_POST_OBSERVATION"
    if at > now:
        return "NOT_USABLE"
    if read.get("status") not in USABLE_STATUS or read.get("freshness") not in USABLE_FRESHNESS:
        return "NOT_USABLE"
    return None


def verify(command: ActionCommand, *, run: str, subjects: dict, spec: "str | None", postcondition, window_ms,
           reads, evaluated_at, outcome: "ActionOutcome | None" = None,
           outcome_ref: "str | None" = None) -> VerificationRecord:
    """판정 하나. 부수 효과가 없다.

    command      ActionCommand (action-contract/1). 창 시작 = issued_at, `$target` = target
    run          실행 id. subjects 는 Sensor state-export `subjects(E, run)` 의 결과(역할 -> 실체 id)
    spec · postcondition · window_ms   ActionSpec 의 이름@판본 · 절 목록 · 창 길이(ms). spec 이 None 이면 NO_SPEC
    reads        (실체, 상태) -> state-export `read` 결과(dict). Mapping 또는 함수 read(entity, state)
    evaluated_at 판정 시각(unix_ms, 창과 같은 기준)
    outcome      실행기의 결과 -- 판정에 쓰지 않는다. 명령과 같은 것을 가리키는지만 본다
    """
    if not isinstance(command, ActionCommand):
        raise TypeError(f"command: ActionCommand 가 아니다 ({type(command).__name__})")
    if outcome is not None:
        if not isinstance(outcome, ActionOutcome):
            raise TypeError(f"outcome: ActionOutcome 이 아니다 ({type(outcome).__name__})")
        if outcome.command_id != command.id:
            raise ContractError("verify", [f"outcome.command_id {outcome.command_id} ≠ 명령 {command.id}"])
    if not isinstance(subjects, dict):
        raise TypeError("subjects: dict 가 아니다")
    if subjects.get("scope") not in (None, run):
        raise ContractError("verify", [f"subjects.scope {subjects.get('scope')!r} ≠ run {run!r}"])
    get = (lambda ent, st: reads.get((ent, st))) if isinstance(reads, Mapping) else reads

    start = command.issued_at
    clauses = tuple(postcondition or ())
    no_spec = spec is None or not clauses
    if no_spec:
        clauses = ()
    if not _is_num(window_ms) or window_ms <= 0:
        raise ContractError("verify", [f"window_ms: 0 보다 큰 수여야 한다 ({window_ms!r})"])
    window = {"start_ms": start, "end_ms": start + window_ms, "time_base": TIME_BASE}

    evidence, why, truth = [], [], []
    for i, c in enumerate(clauses):
        errs = _clause_errors(i, c)
        if errs:
            raise ContractError("verify", errs)
        state = c["pred"][0]
        ent = _resolve(c["entity"], command, subjects)
        r = get(ent, state) if ent is not None else None
        reason = "UNRESOLVED_ENTITY" if ent is None else _usable(r, start, evaluated_at)
        evidence.append({"clause": i, "entity": ent, "state": state,
                         "observed_at": r.get("observed_at") if r else None,
                         "time_base": r.get("time_base") if r else None})
        why.append(reason)
        truth.append(None if reason else predicate.holds(c["pred"], {state: r.get("value")}))

    if no_spec:
        result, reason = "UNKNOWN", "NO_SPEC"
    elif all(t is True for t in truth):
        result, reason = "VERIFIED", "MET"
    elif evaluated_at < window["end_ms"]:
        result, reason = "PENDING", "WINDOW_OPEN"
    elif any(t is False for t in truth):        # 논리곱: 쓸 만한 근거로 거짓인 절 하나면 거짓이다
        result, reason = "NOT_VERIFIED", "UNMET_AT_CLOSE"
    else:
        result, reason = "UNKNOWN", next(w for w in why if w)

    return VerificationRecord(command_id=command.id, run=run, spec=spec, postcondition=clauses, window=window,
                              outcome_ref=outcome_ref, evidence=tuple(evidence), result=result, reason=reason,
                              evaluated_at=evaluated_at, final=result != "PENDING")
