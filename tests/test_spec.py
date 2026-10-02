"""verify 의 사후조건 인자가 action `spec.verify_args(ActionSpec)` 와 그대로 맞물리나 (CMD-H3).

ActionSpec(action-spec/1, BD-109)이 사후조건 · 창의 집이다. MS 가 런타임에서 `verify(cmd, ..., **verify_args(spec))` 로 부른다(CMD-M23).
verify 의 공개 서명 · verification-record/1 은 바꾸지 않았다.
"""
import unittest

from action import ActionCommand, ContractError
from action.spec import ActionSpec, verify_args

from health import verify
from health.verification import _clause_errors

RUN = "r1"
SUBJ = {"scope": RUN, "agent": f"agent:{RUN}", "task": f"task:{RUN}", "runtime": f"runtime:{RUN}"}
T0 = 1_000.0


def spec(**kw):
    base = dict(name="throttle", version="1", target_model="Server", params={}, preconditions=(), risk="local",
                postcondition=({"entity": "$target", "pred": ["status", "in", ["ok", "cool"]]},
                               {"entity": "$run.agent", "pred": ["execution_health", "!=", "UNRESOLVED_FAILURES"]}),
                window_ms=10_000)
    base.update(kw)
    return ActionSpec(**base)


def cmd(target="srv1"):
    return ActionCommand(intent_id="int-" + "0" * 16, decision_ref="dec-x", action="throttle", target=target,
                         args={}, issued_at=T0, deadline=None)


def rd(value, at=T0 + 1_000):
    return {"value": value, "status": "OBSERVED", "freshness": "FRESH", "observed_at": at, "time_base": "unix_ms"}


READS = {("srv1", "status"): rd("ok"), (f"agent:{RUN}", "execution_health"): rd("RECOVERED_FAILURES")}


class VerifyArgs(unittest.TestCase):
    def test_keys_are_verify_parameters(self):
        self.assertEqual(set(verify_args(spec())), {"spec", "postcondition", "window_ms"})

    def test_verify_takes_verify_args_as_is(self):
        s = spec()
        r = verify(cmd(), run=RUN, subjects=SUBJ, reads=READS, evaluated_at=T0 + 2_000, **verify_args(s))
        self.assertEqual((r.result, r.reason, r.spec), ("VERIFIED", "MET", s.ref))
        self.assertEqual(r.window, {"start_ms": T0, "end_ms": T0 + s.window_ms, "time_base": "unix_ms"})
        self.assertEqual([dict(c, pred=list(c["pred"])) for c in r.postcondition], verify_args(s)["postcondition"])

    def test_same_record_as_spelled_out(self):
        s = spec()
        a = verify(cmd(), run=RUN, subjects=SUBJ, reads=READS, evaluated_at=T0 + 2_000, **verify_args(s))
        b = verify(cmd(), run=RUN, subjects=SUBJ, reads=READS, evaluated_at=T0 + 2_000, spec="throttle@1",
                   postcondition=[{"entity": "$target", "pred": ["status", "in", ["ok", "cool"]]},
                                  {"entity": "$run.agent", "pred": ["execution_health", "!=", "UNRESOLVED_FAILURES"]}],
                   window_ms=10_000)
        self.assertEqual(a.to_dict(), b.to_dict())

    def test_every_clause_actionspec_accepts_verify_accepts(self):
        """명세가 받은 절은 verify 도 받는다(명세 ⊆ verify). 거꾸로는 아니다 -- 아래 시험."""
        clauses = [
            {"entity": "$target", "pred": ["s", "exists"]},
            {"entity": "$run.task", "pred": ["s", "missing"]},
            {"entity": "$run.runtime", "pred": ["n", ">=", 3]},
            {"entity": "tool:r1:WebFetch", "pred": ["s", "not_in", ["A", "B"]]},
            {"entity": "dependency:r1:api", "pred": ["s", "==", None]},
        ]
        for c in clauses:
            s = spec(postcondition=(c,))
            self.assertEqual(_clause_errors(0, verify_args(s)["postcondition"][0]), [], c)

    def test_shapes_both_refuse(self):
        for c in ({"entity": "$who", "pred": ["s", "==", 1]}, {"entity": "$target", "pred": ["s", ">=", {"prop": "t"}]},
                  {"entity": "$target", "pred": ["", "==", 1]}, {"entity": "$target", "pred": ["s", "~", 1]},
                  {"entity": "$target", "pred": ["s"]}, {"entity": "$target"}):
            with self.assertRaises(ContractError, msg=c):
                spec(postcondition=(c,))
            self.assertNotEqual(_clause_errors(0, c), [], c)

    def test_verify_is_looser_on_entity_whitespace(self):
        """다른 점(보고함): 명세는 실체 id 에 빈칸을 거절하고(ENTITY_REF), verify 는 받는다. verification-record/1 이 동결이라 그대로 둔다.
        명세를 지난 절만 verify 로 오므로 판정에는 영향이 없다."""
        c = {"entity": "tool:r1:Web Fetch", "pred": ["s", "==", 1]}
        with self.assertRaises(ContractError):
            spec(postcondition=(c,))
        self.assertEqual(_clause_errors(0, c), [])

    def test_spec_without_postcondition(self):
        """사후조건 없는 명세: verify_args 는 창이 None 이다. verify 는 창 없이 기록을 지을 수 없어 거절한다(지금 동작 -- 보고함).
        spec 을 None 으로, 창을 주고 부르면 NO_SPEC 기록이 선다."""
        s = spec(postcondition=(), window_ms=None)
        self.assertEqual(verify_args(s), {"spec": "throttle@1", "postcondition": [], "window_ms": None})
        with self.assertRaises(ContractError):
            verify(cmd(), run=RUN, subjects=SUBJ, reads=READS, evaluated_at=T0 + 2_000, **verify_args(s))
        r = verify(cmd(), run=RUN, subjects=SUBJ, reads=READS, evaluated_at=T0 + 2_000, spec=s.ref, postcondition=[],
                   window_ms=1)
        self.assertEqual((r.result, r.reason), ("UNKNOWN", "NO_SPEC"))

    def test_target_less_spec_cannot_name_target(self):
        """겨냥 없는 행동(target_model=None)에 $target 을 쓰면 명세가 거절한다 -- verify 의 UNRESOLVED_ENTITY 에 앞서 막힌다."""
        with self.assertRaises(ContractError):
            spec(target_model=None)
        s = spec(target_model=None, postcondition=({"entity": "$run.agent", "pred": ["execution_health", "==", "X"]},))
        r = verify(cmd(target=None), run=RUN, subjects=SUBJ, reads=READS, evaluated_at=T0 + 20_000, **verify_args(s))
        self.assertEqual((r.result, r.reason), ("NOT_VERIFIED", "UNMET_AT_CLOSE"))


if __name__ == "__main__":
    unittest.main()
