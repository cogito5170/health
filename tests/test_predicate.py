"""술어 -- health 의 술어는 action 의 한 벌을 사후조건 모드(refs=False · named=True)로 묶은 것뿐이다(CMD-H3).
진리표 · 모양을 고정하고, 옆에 MS 가 있으면 원본(MS `ms/predicate.py`)과 대조한다(없으면 그 시험만 건너뜀)."""
import importlib.util
import os
import pathlib
import unittest

from health import predicate

CASES = [
    (["s", "==", "A"], {"s": "A"}), (["s", "==", "A"], {"s": "B"}), (["s", "!=", "A"], {"s": "B"}),
    (["s", "in", ["A", "B"]], {"s": "B"}), (["s", "in", ["A"]], {"s": "B"}), (["s", "not_in", ["A"]], {"s": "B"}),
    (["n", "<", 3], {"n": 2}), (["n", "<=", 3], {"n": 3}), (["n", ">", 3], {"n": 3}), (["n", ">=", 3], {"n": 3}),
    (["n", ">", 3], {"n": "x"}),                  # 견줄 수 없음 -> 거짓
    (["s", "==", "A"], {}),                       # 값 없음 -> 거짓
    (["s", "not_in", ["A"]], {"s": None}),        # 값 없음 -> 거짓(not_in 이어도)
    (["s", "exists"], {"s": "A"}), (["s", "exists"], {}), (["s", "missing"], {}), (["s", "missing"], {"s": 0}),
    (["b", "==", True], {"b": True}), (["n", "==", 1], {"n": 1.0}),
]


def _ms_predicate():
    here = pathlib.Path(__file__).resolve().parent.parent
    for p in filter(None, [os.environ.get("MS_REPO"), here.parent / "MS", here.parent / "ms", here.parent / "cogito5170" / "ms"]):
        f = pathlib.Path(p) / "ms" / "predicate.py"
        if f.exists():
            spec = importlib.util.spec_from_file_location("_ms_predicate", f)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            return mod
    return None


class Shape(unittest.TestCase):
    def test_good(self):
        for p, _ in CASES:
            self.assertEqual(predicate.check(p), [], p)

    def test_bad(self):
        for p in (["s"], ["s", "~", 1], ["s", "in", "A"], ["s", "exists", 1], ["", "==", 1], [1, "==", 1],
                  ["s", ">=", {"prop": "t"}], "s == 1"):
            self.assertNotEqual(predicate.check(p), [], p)

    def test_truth_table(self):
        want = [True, False, True, True, False, True, True, True, False, True, False, False, False,
                True, False, True, False, True, True]
        self.assertEqual([predicate.holds(p, v) for p, v in CASES], want)


class OneSet(unittest.TestCase):
    """자기 구현이 없다 -- 판정은 action 한 벌의 것, 모양 검사는 그 한 벌의 사후조건 모드."""

    def test_holds_is_actions(self):
        from action import predicate as one
        self.assertIs(predicate.holds, one.holds)
        self.assertIs(predicate.OPS, one.OPS)

    def test_check_is_postcondition_mode(self):
        from action import predicate as one
        for p in [c for c, _ in CASES] + [["s"], ["s", ">=", {"prop": "t"}], ["", "==", 1], [1, "==", 1], ["s", "~", 1]]:
            self.assertEqual(predicate.check(p), one.check(p, refs=False, named=True), p)


class SameAsMS(unittest.TestCase):
    """MS 도 이제 action 한 벌을 다시 내보낸다(M21) -- 이 대조는 그 층이 바뀌지 않았음을 볼 뿐이다. 뜻의 고정은 위 진리표 · 옮기기 전후 대조(eval)."""

    def test_conformance(self):
        ms = _ms_predicate()
        if ms is None:
            self.skipTest("옆에 MS 가 없다(MS_REPO 로 줄 수 있다)")
        self.assertEqual(set(ms.OPS), set(predicate.OPS))
        for p, v in CASES:
            self.assertEqual(predicate.holds(p, v), ms.holds(p, v), (p, v))
            self.assertEqual(predicate.check(p) == [], ms.check(p) == [], p)   # 글은 다르다 -- 받느냐만 같으면 된다


if __name__ == "__main__":
    unittest.main()
