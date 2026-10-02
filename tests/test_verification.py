"""verification-record/1 · verify (baseline#9 CMD-H2 의 끝난 기준 1 · 2)."""
import dataclasses
import json
import unittest

from action import ActionCommand, ActionOutcome, ContractError

from health import VerificationRecord, action_entity, verify

T0 = 1_759_400_000_000          # 명령 발행(unix_ms)
WIN = 60_000                    # 창 1 분
RUN = "cc_stream:demo"
SUBJECTS = {"scope": RUN, "agent": f"agent:{RUN}", "task": f"task:{RUN}", "runtime": f"runtime:{RUN}",
            "tool": [f"tool:{RUN}:WebFetch"]}
SPEC = "retry_tool@1"
POST = ({"entity": "$target", "pred": ["tool_execution_health", "in", ["NO_FAILURE_OBSERVED", "RECOVERED_FAILURES"]]},
        {"entity": "$run.agent", "pred": ["execution_health", "!=", "UNRESOLVED_FAILURES"]})


def command(**kw):
    base = dict(intent_id="int-0123456789abcdef", decision_ref="dec-1", action="retry_tool",
                target=f"tool:{RUN}:WebFetch", args={}, issued_at=T0, deadline=None)
    base.update(kw)
    return ActionCommand(**base)


def read(value, at, *, status="INFERRED", freshness="FRESH", time_base="unix_ms"):
    """Sensor state-export/2 `read` 결과의 모의(판정에 쓰는 칸만)."""
    return {"value": value, "status": status, "freshness": freshness, "observed_at": at, "time_base": time_base}


def good(at=T0 + 1_000):
    return {(f"tool:{RUN}:WebFetch", "tool_execution_health"): read("RECOVERED_FAILURES", at),
            (f"agent:{RUN}", "execution_health"): read("RECOVERED_FAILURES", at)}


def run_verify(reads, now, **kw):
    cmd = kw.pop("cmd", None) or command()
    args = dict(run=RUN, subjects=SUBJECTS, spec=SPEC, postcondition=POST, window_ms=WIN, reads=reads, evaluated_at=now)
    args.update(kw)
    return verify(cmd, **args)


class FiveBranches(unittest.TestCase):
    """판정 다섯 갈래."""

    def test_1_no_spec(self):
        for spec, post in ((None, POST), (SPEC, ()), (None, ())):
            r = run_verify(good(), T0 + 5_000, spec=spec, postcondition=post)
            self.assertEqual((r.result, r.reason, r.final, r.postcondition), ("UNKNOWN", "NO_SPEC", True, ()))

    def test_2_verified_even_while_window_open(self):
        r = run_verify(good(), T0 + 5_000)
        self.assertEqual((r.result, r.reason, r.final), ("VERIFIED", "MET", True))

    def test_3_pending_while_open(self):
        for reads in ({}, {**good(), (f"agent:{RUN}", "execution_health"): read("UNRESOLVED_FAILURES", T0 + 1)}):
            r = run_verify(reads, T0 + WIN - 1)
            self.assertEqual((r.result, r.reason, r.final), ("PENDING", "WINDOW_OPEN", False))

    def test_4_not_verified_at_close(self):
        reads = {**good(), (f"agent:{RUN}", "execution_health"): read("UNRESOLVED_FAILURES", T0 + 2_000)}
        r = run_verify(reads, T0 + WIN)
        self.assertEqual((r.result, r.reason, r.final), ("NOT_VERIFIED", "UNMET_AT_CLOSE", True))

    def test_4_one_false_clause_decides_even_if_another_is_unknown(self):
        # 논리곱에서 거짓 하나면 거짓이다. 다른 절이 모름이어도 NOT_VERIFIED
        reads = {(f"agent:{RUN}", "execution_health"): read("UNRESOLVED_FAILURES", T0 + 2_000)}
        r = run_verify(reads, T0 + WIN)
        self.assertEqual((r.result, r.reason), ("NOT_VERIFIED", "UNMET_AT_CLOSE"))

    def test_5_unknown_at_close_names_first_missing_reason(self):
        cases = {
            "NO_POST_OBSERVATION": {},
            "TIME_BASE_MISMATCH": {k: read(v["value"], 5, time_base="monotonic_ms") for k, v in good().items()},
            "NOT_USABLE": {k: read(v["value"], v["observed_at"], status="UNKNOWN") for k, v in good().items()},
        }
        for want, reads in cases.items():
            r = run_verify(reads, T0 + WIN + 1)
            self.assertEqual((r.result, r.reason, r.final), ("UNKNOWN", want, True), want)


class Usability(unittest.TestCase):
    def test_observation_before_command_is_not_evidence(self):
        r = run_verify(good(at=T0 - 1), T0 + 5_000)
        self.assertEqual(r.result, "PENDING")
        r = run_verify(good(at=T0 - 1), T0 + WIN)
        self.assertEqual((r.result, r.reason), ("UNKNOWN", "NO_POST_OBSERVATION"))
        self.assertEqual(run_verify(good(at=T0), T0 + 5_000).result, "VERIFIED")     # 발행과 같은 시각은 받는다

    def test_stale_untimed_future_are_not_usable(self):
        for kw, at in (({"freshness": "STALE"}, T0 + 1), ({"freshness": "UNTIMED"}, T0 + 1), ({}, T0 + WIN + 10)):
            reads = {k: read(v["value"], at, **kw) for k, v in good().items()}
            r = run_verify(reads, T0 + WIN + 5)
            self.assertEqual((r.result, r.reason), ("UNKNOWN", "NOT_USABLE"), kw)

    def test_permanent_is_usable(self):
        reads = {k: read(v["value"], v["observed_at"], freshness="PERMANENT") for k, v in good().items()}
        self.assertEqual(run_verify(reads, T0 + 5_000).result, "VERIFIED")

    def test_unresolved_entity(self):
        r = run_verify(good(), T0 + WIN, cmd=command(target=None))
        self.assertEqual((r.result, r.reason), ("UNKNOWN", "UNRESOLVED_ENTITY"))
        self.assertIsNone(r.evidence[0]["entity"])
        r = run_verify(good(), T0 + WIN, subjects={"scope": RUN})
        self.assertEqual(r.reason, "UNRESOLVED_ENTITY")

    def test_reads_may_be_a_function(self):
        g = good()
        r = run_verify(lambda e, s: g.get((e, s)), T0 + 5_000)
        self.assertEqual(r.to_dict(), run_verify(g, T0 + 5_000).to_dict())


class OutcomeIsNotEvidence(unittest.TestCase):
    """실행기의 결과는 판정에 들어가지 않는다."""

    def test_outcome_does_not_change_result(self):
        cmd = command()
        for reads, now in ((good(), T0 + 5_000), ({}, T0 + WIN), ({}, T0 + 1)):
            base = run_verify(reads, now, cmd=cmd).to_dict()
            for is_error in (True, False, None):
                o = ActionOutcome(command_id=cmd.id, is_error=is_error, exit_code=1 if is_error else 0)
                got = run_verify(reads, now, cmd=cmd, outcome=o).to_dict()
                self.assertEqual(got, base, (is_error, now))

    def test_outcome_must_be_the_same_command(self):
        o = ActionOutcome(command_id="cmd-" + "0" * 16)
        with self.assertRaises(ContractError):
            run_verify(good(), T0 + 5_000, outcome=o)


class Record(unittest.TestCase):
    def setUp(self):
        self.rec = run_verify(good(), T0 + 5_000, outcome_ref="evt-42")

    def test_round_trip_bytes(self):
        d = self.rec.to_dict()
        s = json.dumps(d, sort_keys=True, ensure_ascii=False)
        back = VerificationRecord.from_dict(json.loads(s))
        self.assertEqual(back.to_dict(), d)
        self.assertEqual(back.id, self.rec.id)

    def test_entity_id(self):
        self.assertEqual(self.rec.entity, f"action:{RUN}:{self.rec.command_id}")
        self.assertEqual(action_entity("r", "cmd-x"), "action:r:cmd-x")

    def test_evidence_is_reference_only(self):
        for ev in self.rec.evidence:
            self.assertEqual(set(ev), {"clause", "entity", "state", "observed_at", "time_base"})
        d = self.rec.to_dict()
        d["evidence"][0]["value"] = "RECOVERED_FAILURES"
        with self.assertRaises(ContractError):
            VerificationRecord.from_dict(d)

    def test_unknown_missing_field_and_schema_rejected(self):
        d = self.rec.to_dict()
        for bad in ({**d, "extra": 1}, {k: v for k, v in d.items() if k != "reason"}, {**d, "schema": "verification-record/2"}):
            with self.assertRaises(ContractError):
                VerificationRecord.from_dict(bad)

    def test_tampered_id_rejected(self):
        d = self.rec.to_dict()
        d["result"], d["reason"] = "NOT_VERIFIED", "UNMET_AT_CLOSE"
        with self.assertRaises(ContractError):
            VerificationRecord.from_dict(d)

    def test_inconsistent_records_rejected(self):
        b = self.rec
        bad = [
            dict(result="UNKNOWN"),                                   # MET 은 VERIFIED 만
            dict(final=False),                                        # VERIFIED 는 final
            dict(result="PENDING", reason="WINDOW_OPEN", final=False, evaluated_at=T0 + WIN),  # 창이 닫혔는데 PENDING
            dict(evaluated_at=T0 - 1),
            dict(window={"start_ms": T0, "end_ms": T0, "time_base": "unix_ms"}),
            dict(window={"start_ms": T0, "end_ms": T0 + WIN, "time_base": "monotonic_ms"}),
            dict(evidence=b.evidence[:1]),
            dict(spec="retry_tool"),
            dict(postcondition=({"entity": "$who", "pred": ["x", "==", 1]},) + b.postcondition[1:]),
            dict(postcondition=({"entity": "$target", "pred": ["x", "~", 1]},) + b.postcondition[1:]),
            dict(postcondition=({"entity": "$target", "pred": ["x", ">=", {"prop": "y"}]},) + b.postcondition[1:]),
            dict(result="UNKNOWN", reason="NO_SPEC"),                 # NO_SPEC 인데 사후조건이 있다
            dict(command_id="cmd-1"),
            dict(outcome_ref=""),
            dict(schema="verification-record/2"),                     # 해시가 맞아도 다른 판본은 거절
        ]
        for kw in bad:
            with self.assertRaises(ContractError, msg=kw):
                dataclasses.replace(b, **kw)

    def test_hash_is_stable_and_order_free(self):
        d = self.rec.to_dict()
        self.assertEqual(VerificationRecord.from_dict(dict(reversed(list(d.items())))).id, self.rec.id)
        self.assertEqual(self.rec.id, GOLDEN)

    def test_every_field_changes_the_id(self):
        b = self.rec
        variants = [dict(run="other"), dict(outcome_ref="evt-43"), dict(evaluated_at=T0 + 5_001),
                    dict(spec="retry_tool@2"), dict(evidence=({**b.evidence[0], "observed_at": T0 + 2},) + b.evidence[1:])]
        ids = {dataclasses.replace(b, **kw).id for kw in variants} | {b.id}
        self.assertEqual(len(ids), len(variants) + 1)

    def test_deterministic(self):
        self.assertEqual(run_verify(good(), T0 + 5_000, outcome_ref="evt-42").to_dict(), self.rec.to_dict())


GOLDEN = "ver-90fbfad9687348e6"   # 꼴 · 정준 JSON 이 바뀌면 판본을 올리고 이 값을 고친다

if __name__ == "__main__":
    unittest.main()
