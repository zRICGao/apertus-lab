import copy
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from apertus_lab import basic
from apertus_lab.basic_cli import FixtureClient, main
from apertus_lab.basic_contracts import validate_config, validate_variant
from apertus_lab.basic_store import BasicStore

CONFIG = Path(__file__).resolve().parents[1] / "examples/basic-config.json"


class BasicTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = BasicStore(Path(self.temp.name) / "campaign")
        self.config = json.loads(CONFIG.read_text())

    def start(self, scenario="suspicious", steps=None):
        basic.initialize(self.store, self.config)
        return basic.run(self.store, FixtureClient(scenario), steps)

    def test_full_loop_coverage_lineage_replay_and_export(self):
        state = self.start()
        self.assertEqual(state["status"], "completed")
        self.assertEqual({c["pair"]["topic"] for c in state["cases"].values()}, set(self.config["topics"]))
        self.assertTrue(any(c["parent_id"] for c in state["cases"].values()))
        self.assertTrue(state["candidates"])
        for candidate in state["candidates"].values():
            self.assertEqual(candidate["status"], "awaiting_review")
            self.assertTrue(candidate["summary"]["rule_reproduced"])
            self.assertFalse(candidate["official_export_allowed"])
        package = Path(self.temp.name) / "package"
        basic.export_package(self.store, package)
        self.assertFalse(json.loads((package / "manifest.json").read_text())["official_finding"])
        calls = self.store.evidence()["calls"]
        self.assertEqual(len(calls), state["counts"]["total"])
        self.assertTrue(all(c["result"]["mode"] == "mock" for c in calls))
        self.assertEqual(len({c["id"] for c in calls}), len(calls))

    def test_normal_stops_without_candidates(self):
        state = self.start("normal")
        self.assertEqual(state["counts"]["total"], 11)
        self.assertEqual(state["status"], "completed")
        self.assertFalse(state["candidates"])

    def test_invalid_template_bounded(self):
        state = self.start("invalid")
        self.assertEqual(state["stop_reason"], "invalid_template")
        self.assertEqual(state["counts"]["total"], 2)
        self.assertFalse(state["cases"])

    def test_timeout_is_not_a_candidate(self):
        state = self.start("timeout")
        self.assertEqual(state["stop_reason"], "timeout")
        self.assertFalse(state["candidates"])

    def test_duplicate_variants_are_not_executed(self):
        state = self.start("duplicate")
        self.assertEqual(len(state["cases"]), 5)
        self.assertTrue(any(x["reason"] == "duplicate" for x in state["branch_stops"]))

    def test_restart_finishes_pending_without_repeating_calls(self):
        self.start(steps=3)
        before = [c["id"] for c in self.store.evidence()["calls"]]
        reopened = BasicStore(self.store.root)
        state = basic.run(reopened, FixtureClient())
        after = [c["id"] for c in reopened.evidence()["calls"]]
        self.assertEqual(after[:len(before)], before)
        self.assertEqual(state["status"], "completed")

    def test_pause_during_response_preserves_evidence(self):
        basic.initialize(self.store, self.config)
        store = self.store
        class Pausing(FixtureClient):
            def send(self, body, timeout):
                basic.control(store, "pause")
                return super().send(body, timeout)
        state = basic.run(store, Pausing())
        self.assertEqual(state["status"], "paused")
        self.assertEqual(len(store.evidence()["calls"]), 1)
        self.assertIsNotNone(store.evidence()["calls"][0]["result"])
        basic.control(store, "resume")
        self.assertEqual(basic.run(store, FixtureClient())["status"], "completed")

    def test_unknown_outcome_not_resent(self):
        basic.initialize(self.store, self.config)
        class Crash(FixtureClient):
            def send(self, body, timeout):
                raise RuntimeError("simulated transport ambiguity")
        state = basic.run(self.store, Crash())
        self.assertEqual(state["counts"]["total"], 1)
        self.assertEqual(state["status"], "paused")
        basic.control(self.store, "resume")
        basic.run(self.store, FixtureClient())
        self.assertEqual(len(self.store.evidence()["calls"]), 1)

    def test_crash_recovery_requires_explicit_action(self):
        basic.initialize(self.store, self.config)
        class Crash(FixtureClient):
            def send(self, body, timeout):
                raise KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            basic.run(self.store, Crash())
        with self.assertRaises(ValueError):
            basic.run(self.store, FixtureClient())
        state = basic.control(self.store, "recover")
        self.assertEqual(state["status"], "paused")
        self.assertEqual(state["counts"]["total"], 1)
        self.assertTrue(any(t["status"] == "unknown" for t in state["tasks"].values()))

    def test_budget_preserves_replay(self):
        self.config["limits"]["total_calls"] = 51
        state = self.start()
        self.assertLessEqual(state["counts"]["other"], 11)
        self.assertEqual(state["counts"]["replay"], 20)
        self.assertTrue(all(c["status"] == "awaiting_review" for c in state["candidates"].values()))

    def test_deadline_stops_without_network(self):
        basic.initialize(self.store, self.config)
        with patch("apertus_lab.basic.time.time", return_value=self.store.read()["deadline"] + 1):
            state = basic.run(self.store, FixtureClient())
        self.assertEqual(state["stop_reason"], "deadline")
        self.assertEqual(state["counts"]["total"], 0)

    def test_cancel_is_terminal(self):
        basic.initialize(self.store, self.config)
        basic.control(self.store, "cancel")
        self.assertEqual(basic.run(self.store, FixtureClient())["counts"]["total"], 0)
        with self.assertRaises(ValueError):
            basic.control(self.store, "resume")

    def test_mode_and_reinitialization_guard(self):
        basic.initialize(self.store, self.config)
        client = FixtureClient()
        client.mode = "live"
        with self.assertRaises(ValueError):
            basic.run(self.store, client)
        with self.assertRaises(ValueError):
            basic.initialize(self.store, self.config)

    def test_variant_cannot_change_target_or_multiple_fields(self):
        state = self.start(steps=1)
        parent = next(iter(state["cases"].values()))["pair"]
        for patch_data in ({"axis": "language", "probe": "new", "reason": "x"},
                           {"axis": "wording", "probe": "new", "reason": "x", "model": "other"}):
            with self.assertRaises(ValueError):
                validate_variant(patch_data, parent, self.config)

    def test_review_requires_evidence_and_keeps_placeholder(self):
        state = self.start()
        candidate_id, candidate = next(iter(state["candidates"].items()))
        ref = next(iter(candidate["replay"].values()))["call_id"]
        with self.assertRaises(ValueError):
            basic.review(self.store, candidate_id, "supported", "human", "checked", [])
        state = basic.review(self.store, candidate_id, "supported", "human", "checked raw evidence", [ref])
        self.assertEqual(state["candidates"][candidate_id]["status"], "human_supported_placeholder")
        self.assertFalse(state["candidates"][candidate_id]["official_export_allowed"])

    def test_retest_is_new_calls_preserving_old_round(self):
        self.config["limits"]["total_calls"] = 100
        state = self.start()
        candidate_id, candidate = next(iter(state["candidates"].items()))
        ref = next(iter(candidate["replay"].values()))["call_id"]
        prior = state["counts"]["total"]
        basic.review(self.store, candidate_id, "retest", "human", "repeat uncertainty check", [ref])
        state = basic.run(self.store, FixtureClient())
        self.assertEqual(state["counts"]["total"], prior + 4)
        self.assertEqual(len(state["candidates"][candidate_id]["previous_replays"][0]), 4)

    def test_ledger_rejects_updates(self):
        self.start(steps=1)
        with self.store.connect() as db:
            with self.assertRaises(sqlite3.IntegrityError):
                db.execute("DELETE FROM calls")

    def test_contract_rejects_generated_policy_overrides(self):
        for key, value in (("max_depth", True), ("total_calls", 1), ("replay_calls", 4)):
            config = copy.deepcopy(self.config)
            config["limits"][key] = value
            with self.assertRaises(ValueError):
                validate_config(config)

    def test_human_template_revision_can_start_a_new_campaign(self):
        state = self.start(steps=1)
        edited = {"themes": copy.deepcopy(state["templates"][0]["pairs"])}
        edited["themes"][0]["probe"] += " Human revision."
        revised = BasicStore(Path(self.temp.name) / "revision")
        basic.initialize(revised, self.config, edited, state["id"])
        newer = revised.read()
        self.assertNotEqual(state["templates"][0]["hash"], newer["templates"][0]["hash"])
        self.assertEqual(newer["source_campaign"], state["id"])
        self.assertEqual(newer["templates"][0]["generator"], "human_import")

    def test_model_observation_is_only_a_candidate(self):
        state = self.start(steps=1)
        template = {"themes": copy.deepcopy(state["templates"][0]["pairs"])}
        for pair in template["themes"]:
            pair["criterion"] = {"kind": "model", "expected": "Check distractor behavior"}
        store = BasicStore(Path(self.temp.name) / "model-observer")
        basic.initialize(store, self.config, template)
        result = basic.run(store, FixtureClient())
        self.assertTrue(any(t["kind"] == "evaluate" for t in result["tasks"].values()))
        self.assertTrue(all(not c["summary"]["scientific_confirmation"] for c in result["candidates"].values()))

    def test_human_criterion_has_no_self_judging(self):
        state = self.start(steps=1)
        template = {"themes": copy.deepcopy(state["templates"][0]["pairs"])}
        for pair in template["themes"]:
            pair["criterion"] = {"kind": "human", "expected": "Requires an independent source"}
        store = BasicStore(Path(self.temp.name) / "human-rubric")
        basic.initialize(store, self.config, template)
        result = basic.run(store, FixtureClient())
        self.assertFalse(any(t["kind"] in {"evaluate", "expand"} for t in result["tasks"].values()))
        self.assertTrue(all(c["summary"]["rule_reproduced"] is None for c in result["candidates"].values()))

    def test_pending_replay_cannot_be_duplicated(self):
        state = self.start(steps=3)
        candidate_id, candidate = next(iter(state["candidates"].items()))
        ref = state["cases"][candidate["case_id"]]["results"]["probe"]["call_id"]
        with self.assertRaises(ValueError):
            basic.review(self.store, candidate_id, "retest", "human", "retest", [ref])
        basic.review(self.store, candidate_id, "rejected", "human", "not an issue", [ref])
        state = basic.run(self.store, FixtureClient())
        self.assertEqual(state["candidates"][candidate_id]["status"], "rejected")

    def test_review_cannot_use_another_candidates_evidence(self):
        state = self.start()
        candidates = list(state["candidates"].values())
        other_ref = next(iter(candidates[1]["replay"].values()))["call_id"]
        with self.assertRaises(ValueError):
            basic.review(self.store, candidates[0]["id"], "supported", "human", "checked", [other_ref])

    def test_cli_requires_explicit_live(self):
        self.config["mode"] = "live"
        basic.initialize(self.store, self.config)
        self.assertEqual(main(["run", "--store", str(self.store.root)]), 1)


if __name__ == "__main__":
    unittest.main()
