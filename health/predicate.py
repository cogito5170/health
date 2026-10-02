"""술어 -- action 의 한 벌(`action.predicate`, CMD-A4 · BD-108)을 **사후조건 자리의 모드**로 묶은 것뿐이다. 자기 구현은 없다(CMD-H3).

사후조건 자리(verification-record/1)는 `check(p, refs=False, named=True)` 다(action `docs/PREDICATE.md` §1):
    refs=False   값 자리의 속성 참조 `{"prop", "mul"}` 를 받지 않는다 -- 절은 한 실체의 한 상태만 본다
    named=True   첫 칸(상태 이름)이 빈 것 아닌 문자열이어야 한다
`holds` 는 한 벌의 것 그대로다. 값이 없으면 거짓이므로, VERIFY 는 이것을 부르기 **전에** 근거가 쓸 만한지를 가른다.

이 모듈을 남기는 까닭: 모드를 한 곳에서 정하고(verification.py 가 이것을 쓴다), action 의 대조 시험이 `health.predicate` 를 읽는다.
"""
from __future__ import annotations

from action import predicate as _one

OPS = _one.OPS
UNARY = _one.UNARY
holds = _one.holds


def check(pred) -> "list[str]":
    """사후조건 자리의 모양 검사 = 한 벌의 `check(pred, refs=False, named=True)`."""
    return _one.check(pred, refs=False, named=True)
