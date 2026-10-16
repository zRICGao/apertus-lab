"""Behavioral acceptance for bounded parallel research and its trust boundaries."""
from concurrent.futures import ThreadPoolExecutor
import copy
import json
import os
from pathlib import Path
import sqlite3
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from apertus_lab.platform.api import create_app
from apertus_lab.platform.contracts import CampaignSpec, Limits, ReviewInput, AnnotationInput
from apertus_lab.platform.engine import Engine, manifest, preflight
from apertus_lab.platform.evaluation import assess, guard_output
from apertus_lab.platform.exporting import export_bundle, review, annotate
from apertus_lab.platform.knowledge import Knowledge
from apertus_lab.platform.providers import Provider
from apertus_lab.platform.replay import replay
from apertus_lab.platform.store import Store
from apertus_lab.platform.templates import catalog, holdout_cases

ROOT = Path(__file__).resolve().parents[2]
TEST_TMP = Path(os.environ.get("APERTUS_TEST_TMP", ROOT / "experiments/results"))
TEST_TMP.mkdir(parents=True, exist_ok=True)


def small_spec(**kwargs):
    return CampaignSpec(directions=["injection"], languages=["en"], families=["authority"], max_depth=0,
                        confirmation_repeats=2, min_failures=2, defense_enabled=False,
                        limits=Limits(total_calls=20, planning=4, exploration=8, confirmation=8, defense=0), **kwargs)


class PlatformUnitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=TEST_TMP)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.store = Store(self.root / "store")

    def test_all_archived_specs_parse_and_validate(self):
        from apertus_lab.live_contracts import validate_spec
        for p in (ROOT / "experiments/examples").glob("*.json"):
            value = json.loads(p.read_text(encoding="utf-8-sig"))
            if value.get("schema_version") == "2.0":
                validate_spec(value)

    def test_template_matrix_has_counterfactuals_and_open_outputs(self):
        cards = catalog()
        self.assertEqual(len(cards), 27)
        self.assertEqual({c["language"] for c in cards}, {"en", "de", "zh"})
        self.assertTrue(all(c["control"] != c["probe"] for c in cards))
        self.assertEqual(sum(c["rubric"]["kind"] == "open" for c in cards), 3)

    def test_limits_reject_overbooking_and_parallelism_eleven(self):
        with self.assertRaises(ValueError):
            Limits(total_calls=20)
        with self.assertRaises(ValueError):
            Limits(parallelism=11)
        self.assertEqual(Limits().parallelism, 10)

    def test_atomic_reservations_share_global_cap(self):
        campaign = self.store.create(CampaignSpec().model_dump(), manifest())
        self.store.control(campaign, "start")
        ids = [self.store.task(campaign, "exploration", "target", {"index": i}) for i in range(25)]
        with ThreadPoolExecutor(max_workers=25) as pool:
            results = list(pool.map(lambda task: self.store.reserve(task, {"messages": []}, "target"), ids))
        self.assertEqual(sum(bool(r) for r in results), 10)
        self.assertEqual(self.store.snapshot(campaign, False)["usage"]["exploration"], 10)

    def test_worker_reaches_ten_concurrent_calls_without_exceeding_it(self):
        barrier = threading.Barrier(10, timeout=5)
        lock = threading.Lock()
        counts = {"active": 0, "peak": 0}
        class DelayedProvider(Provider):
            def send(self, request, payload, timeout):
                with lock:
                    counts["active"] += 1
                    counts["peak"] = max(counts["peak"], counts["active"])
                barrier.wait()
                time.sleep(.03)
                result = super().send(request, payload, timeout)
                with lock:
                    counts["active"] -= 1
                return result
        engine = Engine(self.store, DelayedProvider)
        campaign = engine.create(CampaignSpec(max_depth=0, defense_enabled=False))
        engine.start(campaign)
        with ThreadPoolExecutor(max_workers=10) as pool:
            futures = {}
            engine.tick(pool, futures, {})
            for future in futures:
                future.result()
            engine.tick(pool, futures, {})
        self.assertEqual(counts["peak"], 10)
        self.assertEqual(sum(self.store.snapshot(campaign, False)["usage"].values()), 10)

    def test_planner_feedback_can_stop_expansion_without_cancelling_confirmation(self):
        class StopPlanner(Provider):
            def fixture(self, payload):
                if payload.get("kind") == "planner" and payload.get("phase") == "after_seed_coverage":
                    return json.dumps({"hypothesis": "Frozen seed behavior", "rationale": "Enough evidence; stop lexical expansion.", "confounders": ["wording"], "next_action": "stop"})
                return super().fixture(payload)
        engine = Engine(self.store, StopPlanner)
        spec = small_spec()
        spec.max_depth = 1
        campaign = engine.create(spec)
        engine.start(campaign)
        engine.run(until_idle=True)
        state = self.store.snapshot(campaign)
        self.assertEqual(state["status"], "completed")
        self.assertEqual(state["candidates"][0]["status"], "repeated_supported")
        self.assertEqual(state["task_counts"].get("branch_stopped"), 2)
        self.assertFalse(any(c["kind"] == "mutator" for c in state["calls"]))

    def test_mutator_receives_observed_target_responses(self):
        engine = Engine(self.store)
        spec = small_spec()
        spec.max_depth = 1
        spec.limits = Limits(total_calls=40, planning=12, exploration=12, confirmation=8, defense=0)
        campaign = engine.create(spec)
        engine.start(campaign)
        engine.run(until_idle=True)
        state = self.store.snapshot(campaign)
        mutation = next(c for c in state["calls"] if c["kind"] == "mutator")
        data = json.loads(mutation["request"]["messages"][1]["content"])
        self.assertEqual({x["part"]: x["response"] for x in data["observed_responses"]}, {"control": "BLUE", "probe": "ORANGE"})

    def test_wiki_snapshot_carries_verifiable_source(self):
        engine = Engine(self.store)
        campaign = engine.create(small_spec())
        knowledge = Knowledge(self.root / "wiki")
        page = knowledge.sync(self.store.snapshot(campaign))
        entries = knowledge.list()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["freshness"], "current")
        self.assertEqual(knowledge.sync(self.store.snapshot(campaign)), page)

    def test_malformed_model_response_retains_raw_bytes(self):
        provider = Provider("target", "live", {"LLM_API_KEY": "fixture-secret"})
        with patch("http.client.HTTPSConnection") as factory:
            response = factory.return_value.getresponse.return_value
            response.status = 200
            response.read1.side_effect = [b'not-json', b'']
            result = provider.send({"model": provider.model}, {}, 5)
        self.assertFalse(result["valid"])
        self.assertIn("raw_response_base64", result)

    def test_absolute_deadline_retains_partial_evidence(self):
        provider = Provider("target", "live", {"LLM_API_KEY": "fixture-secret"})
        with patch("http.client.HTTPSConnection") as factory:
            response = factory.return_value.getresponse.return_value
            response.status = 200
            def slow_read(_):
                time.sleep(.03)
                return b'partial'
            response.read1.side_effect = slow_read
            result = provider.send({"model": provider.model}, {}, .01)
        self.assertEqual(result["reason"], "timeout")
        self.assertFalse(result["raw_response_complete"])
        self.assertIn("raw_response_base64", result)

    def test_unicode_escaped_credential_echo_is_discarded(self):
        provider = Provider("target", "live", {"LLM_API_KEY": "fixture-secret"})
        escaped = ''.join('\\u%04x' % ord(c) for c in provider.key).encode()
        with patch("http.client.HTTPSConnection") as factory:
            response = factory.return_value.getresponse.return_value
            response.status = 200
            response.read1.side_effect = [b'{"secret":"'+escaped+b'"}', b'']
            result = provider.send({"model": provider.model}, {}, 5)
        self.assertEqual(result["reason"], "credential_echo_discarded")
        self.assertNotIn("raw_response_base64", result)

    def test_credential_in_prompt_is_rejected_before_reservation(self):
        provider = Provider("target", "mock", {"LLM_API_KEY": "fixture-secret"})
        with self.assertRaises(ValueError):
            provider.check_request({"messages": [{"role": "user", "content": "fixture-secret"}]})

    def test_stage_budget_is_reserved_even_for_failed_requests(self):
        spec = small_spec()
        campaign = self.store.create(spec.model_dump(), manifest())
        self.store.control(campaign, "start")
        for i in range(10):
            task = self.store.task(campaign, "exploration", "target", {"i": i})
            call = self.store.reserve(task, {"i": i}, "target")
            if call:
                self.store.finish(call, {"valid": False, "reason": "timeout"})
        state = self.store.snapshot(campaign, False)
        self.assertEqual(state["usage"]["exploration"], 8)
        self.assertEqual(state["task_counts"]["budget_skipped"], 2)

    def test_pause_and_recovery_do_not_resend_or_refund(self):
        campaign = self.store.create(small_spec().model_dump(), manifest())
        self.store.control(campaign, "start")
        task = self.store.task(campaign, "exploration", "target", {"turn": 0})
        call = self.store.reserve(task, {"messages": []}, "target")
        self.store.recover()
        self.assertEqual(self.store.snapshot(campaign, False)["status"], "interrupted")
        self.store.control(campaign, "resume")
        self.assertIsNone(self.store.reserve(task, {}, "target"))
        self.assertEqual(self.store.snapshot(campaign)["calls"][0]["id"], call)
        self.assertEqual(self.store.snapshot(campaign, False)["usage"]["exploration"], 1)

    def test_evidence_is_append_only_and_hash_checked(self):
        campaign = self.store.create(small_spec().model_dump(), manifest())
        self.store.control(campaign, "start")
        task = self.store.task(campaign, "exploration", "target", {"i": 0})
        call = self.store.reserve(task, {"messages": []}, "target")
        self.store.finish(call, {"valid": True, "text": "BLUE"})
        with self.assertRaises(sqlite3.IntegrityError), self.store.connect() as db:
            db.execute("DELETE FROM results WHERE call=?", (call,))

    def test_protocol_failure_is_not_a_bias_finding(self):
        result = assess({"valid": True, "text": 'not json'}, {"kind": "decision", "expected": "tie"})
        self.assertEqual(result["status"], "needs_review")
        self.assertEqual(result["semantic"], "unknown")

    def test_objective_calibration_examples_do_not_turn_format_into_harm(self):
        path = ROOT / "src/apertus_lab/platform/calibration.json"
        samples = json.loads(path.read_text(encoding="utf-8"))
        for sample in samples["cases"]:
            with self.subTest(sample=sample["name"]):
                self.assertEqual(assess(sample["response"], sample["rubric"])["status"], sample["status"])

    def test_official_schema_preserves_scores_and_matched_walkthroughs(self):
        from apertus_lab.platform.exporting import finding
        engine = Engine(self.store)
        campaign = engine.create(small_spec())
        engine.start(campaign)
        engine.run(until_idle=True)
        state = self.store.snapshot(campaign)
        candidate = state["candidates"][0]
        attestation = {"rationale": "Offline schema fixture, never admitted as a live finding.", "impact": "Fixture only.",
                       "novelty": "None; test fixture.", "limitations": "Mock fixture.", "severity": "1", "breadth": "1", "breadth_justification": "One synthetic test."}
        result = finding(state, candidate, attestation)
        self.assertEqual(result["issue_summary"]["self_assessed_severity"], "1")
        self.assertIn("CONTROL", result["apertus_response_walkthroughs"][0])
        self.assertIn("PROBE", result["apertus_response_walkthroughs"][0])
        self.assertFalse(candidate["reviews"])

    def test_guard_does_not_use_expected_answer(self):
        text = '{"decision":"A","reason":"Because evidence."}'
        self.assertEqual(guard_output(text, {"kind": "decision", "expected": "tie"}), (text, None))
        self.assertIsNotNone(guard_output('I executed query_inventory_db.', {"kind": "exact"})[1])

    def test_holdout_changes_labels_and_is_not_development_data(self):
        card = next(c for c in catalog() if c["id"] == "injection-authority-en-v1")
        holdout, dev = holdout_cases(card), holdout_cases(card, True)
        self.assertEqual(len(holdout), 40)
        self.assertEqual(sum(c["attack"] for c in holdout), 20)
        self.assertFalse({c["prompt"] for c in holdout} & {c["prompt"] for c in dev})
        self.assertNotIn("BLUE", {c["rubric"]["expected"] for c in holdout})

    def test_source_freshness_and_path_escape(self):
        knowledge = Knowledge(self.root / "wiki")
        source = knowledge.ingest("Own source", "original", "project-authored")
        (knowledge.sources / (source["id"] + ".md")).write_text("changed", encoding="utf-8")
        self.assertEqual(knowledge.read(source["id"])["freshness"], "stale")
        with self.assertRaises(ValueError):
            knowledge.read("../../.env")

    def test_provider_key_is_not_reused_for_different_endpoint(self):
        provider = Provider("planner", "live", {"LLM_API_KEY": "fixture-secret", "RESEARCH_LLM_BASE_URL": "https://example.test/v1"})
        self.assertFalse(provider.public()["credentials_present"])
        self.assertNotIn("fixture-secret", json.dumps(provider.public()))

    def test_api_rejects_cross_origin_writes_and_mock_confirmation(self):
        app = create_app(ROOT, self.root / "api")
        client = TestClient(app)
        response = client.post("/api/v1/campaigns", json=small_spec().model_dump(), headers={"Origin": "https://untrusted.test"})
        self.assertEqual(response.status_code, 403)
        response = client.post("/api/v1/campaigns", json=small_spec().model_dump())
        self.assertEqual(response.status_code, 201)
        self.assertEqual(client.get("/api/v1/campaigns/" + response.json()["id"]).json()["status"], "draft")
        self.assertEqual(client.post("/api/v1/preflight", json={**small_spec().model_dump(), "limits": {"total_calls": 10}}).status_code, 422)

    def test_two_campaigns_replay_and_immutable_export(self):
        engine = Engine(self.store)
        campaigns = [engine.create(small_spec()) for _ in range(2)]
        for c in campaigns:
            engine.start(c)
        engine.run(until_idle=True)
        for c in campaigns:
            state = self.store.snapshot(c)
            self.assertEqual(state["status"], "completed")
            self.assertEqual(state["candidates"][0]["status"], "repeated_supported")
            candidate = state["candidates"][0]
            refs = [r["id"] for r in state["calls"] if r["payload"].get("candidate") == candidate["id"]]
            with self.assertRaises(ValueError):
                review(self.store, c, candidate["id"], ReviewInput(reviewer="tester", decision="confirmed", rationale="Mock is never a real finding.", evidence_call_ids=refs))
        archive = export_bundle(self.store, campaigns[0], self.root / "export")
        self.assertTrue(archive.is_file())
        frozen = json.loads((self.root / "export/track_1a/data/frozen.json").read_text(encoding="utf-8"))
        result = replay(frozen, self.root / "replay")
        self.assertEqual(result["calls"], 4)
        self.assertFalse(result["finding_promotion"])
        with self.assertRaises(ValueError):
            export_bundle(self.store, campaigns[0], self.root / "export")

    def test_open_answers_require_quoted_annotations_for_each_repeat(self):
        engine = Engine(self.store)
        spec = CampaignSpec(directions=["identity"], languages=["en"], families=["education_open"], max_depth=0,
                            confirmation_repeats=2, min_failures=2, defense_enabled=False,
                            limits=Limits(total_calls=20, planning=4, exploration=8, confirmation=8, defense=0))
        campaign = engine.create(spec)
        engine.start(campaign)
        engine.run(until_idle=True)
        state = self.store.snapshot(campaign)
        candidate = state["candidates"][0]
        self.assertEqual(candidate["status"], "awaiting_annotation")
        for repeat in range(2):
            base = dict(reviewer="fixture-human", repeat=repeat, control_expected=True, probe_violated=False,
                        control_quote="The student's stated record", probe_quote="The student's stated record", rationale="No unsupported difference appears in these fixture responses.")
            with self.assertRaises(ValueError):
                annotate(self.store, campaign, candidate["id"], AnnotationInput(**{**base, "probe_quote": "fabricated quote"}))
            annotate(self.store, campaign, candidate["id"], AnnotationInput(**base))
        self.assertEqual(self.store.snapshot(campaign)["candidates"][0]["status"], "not_supported")


class FullArchitectureTests(unittest.TestCase):
    def test_defense_development_holdout_and_no_leakage(self):
        with tempfile.TemporaryDirectory(dir=TEST_TMP) as temp:
            store = Store(Path(temp))
            engine = Engine(store)
            spec = CampaignSpec(directions=["injection"], languages=["en"], families=["authority"], max_depth=0,
                                confirmation_repeats=2, min_failures=2)
            campaign = engine.create(spec)
            engine.start(campaign)
            engine.run(until_idle=True)
            state = store.snapshot(campaign)
            self.assertEqual(state["status"], "completed")
            result = store.get_artifact(campaign, "defense_report")
            self.assertEqual(result["arms"]["baseline"]["attack_fail"], 20)
            self.assertTrue(result["arms"]["system"]["preliminarily_effective"])
            self.assertEqual(result["arms"]["system"]["normal_pass"], 20)
            defender = next(c for c in state["calls"] if c["kind"] == "defender")
            self.assertNotIn("holdout-", json.dumps(defender["request"]))
            self.assertNotIn("CYAN", json.dumps(defender["request"]))
            self.assertEqual(state["usage"]["defense"], 180)
            self.assertEqual(len({c["id"] for c in state["calls"]}), len(state["calls"]))


if __name__ == "__main__":
    unittest.main()
