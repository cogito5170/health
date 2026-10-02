"""CMD-H3 대조 -- 술어를 action 한 벌로 옮기기 **전**(git 의 한 커밋)과 **지금** 이 같은 판정을 내나.

    python3 eval/predicate_migration.py [전 커밋]          # 기본 a07d833 (CMD-H2 · BD-100 문서 고침, 자기 술어)

견주는 것:
    술어   holds -- 술어 × 값의 모든 짝 · check -- 받느냐(글은 한 벌의 것으로 바뀌었다)
    판정   verify -- 사후조건 · 근거 · 판정 시각 · 겨냥의 격자에서 나온 기록(to_dict, id 까지) 전부
전 커밋의 health 패키지는 임시 디렉터리에 꺼내 `health_before` 로 읽는다. 원본은 건드리지 않는다.
"""
from __future__ import annotations

import importlib
import itertools
import pathlib
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent

PREDS = [
    ["s", "==", "A"], ["s", "!=", "A"], ["s", "in", ["A", "B"]], ["s", "not_in", ["A"]], ["n", "<", 3], ["n", "<=", 3],
    ["n", ">", 3], ["n", ">=", 3], ["n", "==", 1], ["b", "==", True], ["s", "exists"], ["s", "missing"],
    ["n", "in", [1, 2.0]], ["s", "==", None],
]
BAD = [["s"], ["s", "~", 1], ["s", "in", "A"], ["s", "exists", 1], ["", "==", 1], [1, "==", 1], [None, "exists"],
       ["s", ">=", {"prop": "t"}], ["s", ">=", {"prop": "t", "mul": 2}], "s == 1", ("s", "==", 1), ["s", "==", 1, 2]]
VALUES = [{}, {"s": "A", "n": 3, "b": True}, {"s": "B", "n": 2.0, "b": 1}, {"s": None, "n": "x", "b": False},
          {"s": 0, "n": None}, {"s": ["A"], "n": True}]


def _load_before(rev: str, tmp: pathlib.Path):
    pkg = tmp / "health_before"
    pkg.mkdir()
    for name in ("__init__.py", "predicate.py", "verification.py"):
        src = subprocess.run(["git", "show", f"{rev}:health/{name}"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
        (pkg / name).write_text(src.replace("from health", "from health_before"), encoding="utf-8")
    sys.path.insert(0, str(tmp))
    return importlib.import_module("health_before")


def main(rev: str = "a07d833") -> int:
    sys.path.insert(0, str(ROOT))
    import health as now
    from action import ActionCommand
    with tempfile.TemporaryDirectory() as tmp:
        before = _load_before(rev, pathlib.Path(tmp))
        bad = []
        n_holds = 0
        for p, v in itertools.product(PREDS, VALUES):
            n_holds += 1
            if before.predicate.holds(p, v) != now.predicate.holds(p, v):
                bad.append(("holds", p, v))
        n_check = 0
        for p in PREDS + BAD:
            n_check += 1
            if (before.predicate.check(p) == []) != (now.predicate.check(p) == []):
                bad.append(("check", p))

        run, t0, win = "r1", 1_000.0, 10_000
        subj = {"scope": run, "agent": f"agent:{run}", "task": f"task:{run}", "runtime": f"runtime:{run}"}
        posts = [[{"entity": "$target", "pred": p}] for p in PREDS] + \
                [[{"entity": "$target", "pred": ["s", "==", "A"]}, {"entity": "$run.agent", "pred": ["n", ">=", 3]}], []]
        reads_for = []
        for (val, at, st, fr, tb) in itertools.product(["A", "B", 3, None], [t0 - 1, t0, t0 + 500, t0 + 99_999],
                                                       ["OBSERVED", "UNKNOWN"], ["FRESH", "STALE"], ["unix_ms", "monotonic_ms"]):
            r = {"value": val, "status": st, "freshness": fr, "observed_at": at, "time_base": tb}
            reads_for.append(r)
        n_verify = 0
        for post, r, now_t, target, spec in itertools.product(posts, reads_for, [t0 + 1_000, t0 + win, t0 + win + 1],
                                                              ["srv1", None], ["throttle@1", None]):
            cmd = ActionCommand(intent_id="int-" + "0" * 16, decision_ref="d", action="throttle", target=target,
                                args={}, issued_at=t0, deadline=None)
            reads = {}
            for c in post:
                ent = {"$target": target, "$run.agent": subj["agent"]}[c["entity"]]
                reads[(ent, c["pred"][0])] = r
            kw = dict(run=run, subjects=subj, spec=spec, postcondition=post, window_ms=win, reads=reads, evaluated_at=now_t)
            outs = []
            for mod in (before, now):
                try:
                    outs.append(("ok", mod.verify(cmd, **kw).to_dict()))
                except Exception as e:                       # 둘 다 같은 까닭으로 거절해야 한다
                    outs.append(("err", type(e).__name__))
            n_verify += 1
            if outs[0] != outs[1]:
                bad.append(("verify", post, r, now_t, target, spec, outs))
        print(f"전 {rev} 대 지금: holds {n_holds} 짝 · check {n_check} 개 · verify {n_verify} 경우")
        print(f"다름 {len(bad)}")
        for b in bad[:10]:
            print("  ", b)
        return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
