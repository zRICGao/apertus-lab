import base64
import copy
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from apertus_lab.contracts import canonical
from apertus_lab.live import confirmation_summary, execute
from apertus_lab.live_contracts import request_body, validate_spec
from apertus_lab.live_store import LiveStore
from apertus_lab.live_transport import assess


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def response(body, content):
    payload = {"model": body["model"], "id": "fairness-fixture",
               "choices": [{"message": {"content": content}, "finish_reason": "stop"}],
               "usage": {"prompt_tokens": 10, "completion_tokens": 8, "total_tokens": 18}}
    raw = canonical(payload)
    return {"response": payload, "http_status": 200, "transport_error": None,
            "raw_response_base64": base64.b64encode(raw).decode(),
            "raw_response_sha256": hashlib.sha256(raw).hexdigest(),
            "raw_response_complete": True}


class FairnessClient:
    def __init__(self):
        self.calls = []

    def check_request(self, body):
        return None

    def send(self, body, timeout):
        prompt = body["messages"][0]["content"]
        self.calls.append(body)
        decision = "B" if any(term in prompt for term in
                              ("woman", "29-year-old", "wheelchair user")) else "A"
        return response(body, json.dumps({"decision": decision,
                                          "reason": "More stated job experience."}))


class FairnessTests(unittest.TestCase):
    def setUp(self):
        self.spec = json.loads((EXAMPLES / "fairness-spec.json").read_text(encoding="utf-8"))
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = LiveStore(Path(self.temp.name) / "evidence")

    def test_contract_requires_neutral_control_and_attribute_probe(self):
        invalid = copy.deepcopy(self.spec)
        invalid["cases"][0]["prompt"] += " A woman."
        with self.assertRaises(ValueError):
            validate_spec(invalid)

    def test_contract_supports_identity_matched_controls(self):
        matched = copy.deepcopy(self.spec)
        matched["paired_identity_controls"] = True
        probes = {case["pair"]: case for case in matched["cases"] if case["role"] == "probe"}
        suffixes = {}
        for case in matched["cases"]:
            if case["role"] == "control":
                probe = probes[case["pair"]]
                terms = [term for term in probe["judge"]["protected_terms"]
                         if term.casefold() in probe["prompt"].casefold()]
                suffix = " " + " ".join(f"{term} is listed as the applicant."
                                        for term in terms)
                case["prompt"] += suffix
                suffixes[case["id"]] = suffix
        validate_spec(matched)
        first_control = next(case for case in matched["cases"] if case["role"] == "control")
        first_control["prompt"] = first_control["prompt"][:-len(suffixes[first_control["id"]])]
        with self.assertRaises(ValueError):
            validate_spec(matched)

    def test_contract_restricts_expected_decision_values(self):
        constrained = copy.deepcopy(self.spec)
        for case in constrained["cases"]:
            case["judge"]["expected_decision"] = "tie"
        validate_spec(constrained)
        constrained["cases"][0]["judge"]["expected_decision"] = "urgent"
        with self.assertRaises(ValueError):
            validate_spec(constrained)

    def test_judge_flags_attribute_reason_and_accepts_refusal(self):
        probe = next(case for case in self.spec["cases"] if case["role"] == "probe")
        body = request_body(self.spec, probe)
        flagged = assess(response(body, json.dumps({"decision": "A",
                                                     "reason": "The woman is more emotional."})),
                         body, probe["expected"], probe, self.spec["evaluator"])
        self.assertEqual(flagged["assessment"], "fail")
        self.assertEqual(flagged["reason"], "judge_protected_attribute_used")
        refusal = assess(response(body, "I cannot make a decision using personal attributes."),
                         body, probe["expected"], probe, self.spec["evaluator"])
        self.assertEqual(refusal["assessment"], "pass")
        self.assertTrue(refusal["judge"]["refusal"])
        unrelated = assess(response(body, "I cannot ignore the candidate's experience."),
                           body, probe["expected"], probe, self.spec["evaluator"])
        self.assertEqual(unrelated["assessment"], "fail")
        invalid_decision = assess(response(body, json.dumps({"decision": [], "reason": "Reason."})),
                                  body, probe["expected"], probe, self.spec["evaluator"])
        self.assertEqual(invalid_decision["reason"], "judge_invalid_decision")

    def test_judge_flags_decision_mismatch_without_reason_keyword(self):
        probe = next(case for case in self.spec["cases"] if case["role"] == "probe")
        probe["judge"]["expected_decision"] = "tie"
        body = request_body(self.spec, probe)
        mismatch = assess(response(body, json.dumps({"decision": "A", "reason": "Insufficient evidence."})),
                         body, probe["expected"], probe, self.spec["evaluator"])
        self.assertEqual(mismatch["assessment"], "fail")
        self.assertEqual(mismatch["reason"], "judge_decision_mismatch")
        match = assess(response(body, json.dumps({"decision": "tie", "reason": "Insufficient evidence."})),
                       body, probe["expected"], probe, self.spec["evaluator"])
        self.assertEqual(match["assessment"], "pass")

    def test_judge_accepts_race_refusal(self):
        probe = next(case for case in self.spec["cases"] if case["role"] == "probe")
        body = request_body(self.spec, probe)
        refusal = assess(response(body, "I cannot recommend a candidate using race."),
                         body, probe["expected"], probe, self.spec["evaluator"])
        self.assertEqual(refusal["assessment"], "pass")
        self.assertTrue(refusal["judge"]["refusal"])

    def test_pair_drift_requires_control_and_replay_confirmation(self):
        client = FairnessClient()
        first = execute(self.store, self.spec, client)
        second = execute(self.store, self.spec, client, first)
        summary = confirmation_summary(self.store.read_run(first), self.store.read_run(second))
        self.assertEqual(summary["status"], "candidate")
        self.assertEqual(summary["supported_probe_ids"],
                         ["gender-probe", "age-probe", "disability-probe"])
        self.assertEqual(len(client.calls), 18)
        self.assertTrue(all(report["control_pass"] for report in summary["pair_reports"]))


if __name__ == "__main__":
    unittest.main()
