"""변이 시험 -- 판정 · 꼴 코드를 일부러 망가뜨려 시험이 빨개지는지 본다. 하나라도 초록으로 남으면 그 시험은 헛돈다.

    python3 eval/mutation.py            # 복사본에서 변이마다 시험을 돌린다. 원본은 건드리지 않는다

baseline#9 CMD-H2 끝난 기준 3 의 셋은 맨 앞에 있다(명령 전 관측 · action.result · 닫힌 창의 PENDING).
옆에 MS 가 있으면 MS_REPO 로 넘겨 술어 대조 시험도 함께 돈다.
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
V, P = "health/verification.py", "health/predicate.py"
# (이름, 파일, 바꿀 글, 바꿀 것)
MUTANTS = [
    # ── CMD-H2 가 이름으로 요구한 셋 ──
    ("명령 전 관측을 근거로 씀", V, "    if at < start:", "    if False:"),
    ("action.result 를 판정에 넣음(실패 → NOT_VERIFIED)", V, "    if no_spec:\n        result, reason",
     "    if outcome is not None and outcome.is_error:\n        result, reason = \"NOT_VERIFIED\", \"UNMET_AT_CLOSE\"\n"
     "    elif no_spec:\n        result, reason"),
    ("action.result 를 판정에 넣음(성공 → VERIFIED)", V, "    elif all(t is True for t in truth):",
     "    elif all(t is True for t in truth) or (outcome is not None and outcome.is_error is False):"),
    ("창이 닫혔는데 PENDING(경계)", V, '    elif evaluated_at < window["end_ms"]:', '    elif evaluated_at <= window["end_ms"]:'),
    ("창이 닫혔는데 PENDING(늘)", V, '    elif evaluated_at < window["end_ms"]:', "    elif True:"),
    ("닫힌 창의 PENDING 을 꼴이 받음", V, '    if self.result == "PENDING" and _is_num(self.evaluated_at)',
     '    if False and _is_num(self.evaluated_at)'),
    # ── 쓸 만한가 ──
    ("유효성을 보지 않음", V, "read.get(\"status\") not in USABLE_STATUS or ", ""),
    ("신선도를 보지 않음", V, " or read.get(\"freshness\") not in USABLE_FRESHNESS", ""),
    ("시각 기준을 보지 않음", V, "    if read.get(\"time_base\") != TIME_BASE:\n        return \"TIME_BASE_MISMATCH\"\n", ""),
    ("미래 관측을 받음", V, "    if at > now:\n        return \"NOT_USABLE\"\n", ""),
    ("모름을 거짓으로(술어를 모든 값에)", V, "truth.append(None if reason else predicate.holds(",
     "truth.append(False if reason else predicate.holds("),
    ("거짓 하나로 정하지 않음(모두 쓸 만해야)", V, "    elif any(t is False for t in truth):",
     "    elif all(t is False or t is True for t in truth):"),
    ("겨냥을 풀지 않음", V, "        return command.target\n", "        return spec_entity\n"),
    ("창 시작을 판정 시각으로", V, "    start = command.issued_at\n", "    start = evaluated_at - 1\n"),
    ("다른 명령의 결과를 받음", V, "        if outcome.command_id != command.id:", "        if False:"),
    # ── 꼴 ──
    ("꼴을 연다(모르는 칸 허용)", V, 'errs = [f"모르는 칸 {k!r}" for k in sorted(set(d) - known, key=str)]', "errs = []"),
    ("빠진 칸을 허용", V, 'errs += [f"빠진 칸 {k!r}" for k in sorted(known - set(d))]', "pass"),
    ("id 를 다시 계산하지 않음", V, "        if d[cls.ID] != obj.id:", "        if False:"),
    ("판본을 보지 않음", V, "        if self.schema != SCHEMA:", "        if False:"),
    ("까닭과 결과가 어긋나도 받음", V, "        elif REASONS[self.reason] != self.result:", "        elif False:"),
    ("final 을 보지 않음", V, "self.final != (self.result != \"PENDING\")", "False"),
    ("근거에 값을 실음", V, 'keys = {"clause", "entity", "state", "observed_at", "time_base"}',
     'keys = {"clause", "entity", "state", "observed_at", "time_base", "value"}'),
    ("해시가 칸 하나(evaluated_at)를 빠뜨림", V, "for f in fields(self)}", 'for f in fields(self) if f.name != "evaluated_at"}'),
    ("모르는 실체 지정을 받음", V, 'elif ent.startswith("$") and ent != "$target"', "elif False"),
    # ── 술어 ──
    ("값이 없어도 견줌", P, "    if values.get(prop) is None:\n        return False\n", ""),
    ("in 을 뒤집음", P, '"in": lambda a, b: a in b,', '"in": lambda a, b: a not in b,'),
    ("속성 참조를 받음", P, '        return [f"속성 참조는 verification-record/1 에서 받지 않는다: {pred!r}"]', "        pass"),
    ("견줄 수 없으면 참", P, "    except TypeError:\n        return False", "    except TypeError:\n        return True"),
]


def _ms_repo():
    for p in filter(None, [os.environ.get("MS_REPO"), ROOT.parent / "MS", ROOT.parent / "ms", ROOT.parent / "cogito5170" / "ms"]):
        if (pathlib.Path(p) / "ms" / "predicate.py").exists():
            return str(p)
    return None


def run(tree: pathlib.Path, env) -> bool:
    r = subprocess.run([sys.executable, "-m", "unittest", "-q"], cwd=tree, capture_output=True, text=True, env=env)
    return r.returncode == 0


def main() -> int:
    env = dict(os.environ)
    ms = _ms_repo()
    if ms:
        env["MS_REPO"] = ms
    print(f"MS 술어 대조: {'함께 돈다 (' + ms + ')' if ms else '건너뜀 -- 옆에 MS 없음'}")
    survived = []
    with tempfile.TemporaryDirectory() as tmp:
        base = pathlib.Path(tmp) / "health"
        shutil.copytree(ROOT, base, ignore=shutil.ignore_patterns(".git", "__pycache__"))
        if not run(base, env):
            print("원본이 초록이 아니다 -- 변이를 돌리지 않는다")
            return 2
        for name, rel, old, new in MUTANTS:
            path = base / rel
            orig = path.read_text(encoding="utf-8")
            if orig.count(old) != 1:
                print(f"?? {name}: 바꿀 글이 {orig.count(old)} 번 나온다")
                survived.append(name)
                continue
            path.write_text(orig.replace(old, new), encoding="utf-8")
            try:
                green = run(base, env)
            finally:
                path.write_text(orig, encoding="utf-8")
            print(f"{'SURVIVED' if green else 'RED     '}  {name}")
            if green:
                survived.append(name)
    print(f"\n{len(MUTANTS) - len(survived)}/{len(MUTANTS)} RED")
    return 1 if survived else 0


if __name__ == "__main__":
    sys.exit(main())
