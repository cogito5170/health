"""술어 -- `[상태 이름, 연산, 값]`. **MS `ms/predicate.py` 의 꼴 그대로**다(사전조건 · 파생 상태 · 질의 거르개가 쓰는 것).

사후조건에 새 술어 꼴을 짓지 않는다(DUP, baseline#9). MS 를 import 하지 않으려고(Health 의 의존은 action 계약뿐) 연산표를
여기 다시 적는다. 같은 뜻인지는 `tests/test_predicate.py` 가 옆에 MS 가 있으면 대조한다.

MS 와 다른 점 하나: 값 자리의 속성 참조(`{"prop": …, "mul": …}`)는 **받지 않는다**(verification-record/1). 사후조건 절은 한 실체의
한 상태만 본다. 다른 상태와 견주는 절이 필요하면 판본을 올려 더한다.

값이 없으면 거짓이다(MS 와 같다). 그래서 VERIFY 는 이것을 부르기 **전에** 근거가 쓸 만한지를 가른다 -- '모름' 이 '거짓' 이 되지 않게.
"""
from __future__ import annotations

OPS = {
    "==": lambda a, b: a == b,
    "!=": lambda a, b: a != b,
    "<": lambda a, b: a < b,
    "<=": lambda a, b: a <= b,
    ">": lambda a, b: a > b,
    ">=": lambda a, b: a >= b,
    "in": lambda a, b: a in b,
    "not_in": lambda a, b: a not in b,
}
UNARY = ("exists", "missing")


def check(pred) -> "list[str]":
    """모양이 틀린 술어를 잡는다. 문제 목록(비었으면 성하다)."""
    if not isinstance(pred, (list, tuple)) or len(pred) not in (2, 3):
        return [f"술어는 [상태, 연산, 값] 이어야 한다: {pred!r}"]
    if not isinstance(pred[0], str) or not pred[0]:
        return [f"술어의 첫 칸은 상태 이름(빈 것 아닌 문자열)이어야 한다: {pred!r}"]
    if len(pred) == 2:
        return [] if pred[1] in UNARY else [f"값 없는 연산은 exists · missing 뿐: {pred!r}"]
    if pred[1] not in OPS:
        return [f"모르는 연산 {pred[1]!r} (쓸 수 있는 것: {', '.join(OPS)} · exists · missing)"]
    if pred[1] in ("in", "not_in") and not isinstance(pred[2], (list, tuple)):
        return [f"{pred[1]} 의 값은 목록이어야 한다: {pred!r}"]
    if isinstance(pred[2], dict):
        return [f"속성 참조는 verification-record/1 에서 받지 않는다: {pred!r}"]
    return []


def holds(pred, values: dict) -> bool:
    """MS `predicate.holds` 와 같은 뜻(속성 참조 제외). 값이 없거나 견줄 수 없으면 거짓."""
    prop, op = pred[0], pred[1]
    if op == "exists":
        return values.get(prop) is not None
    if op == "missing":
        return values.get(prop) is None
    if values.get(prop) is None:
        return False
    try:
        return bool(OPS[op](values[prop], pred[2]))
    except TypeError:
        return False
