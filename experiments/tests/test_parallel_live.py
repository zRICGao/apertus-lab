"""Offline checks of bounded paired dispatch and evidence behavior."""
from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import threading
import unittest

from apertus_lab.live import confirmation_summary, execute
from apertus_lab.live_contracts import validate_spec
from apertus_lab.live_store import LiveStore
from test_mvp import FakeClient, response


EXAMPLE = Path(__file__).resolve().parents[1] / "examples/live-spec.json"


class PairedParallelTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.store = LiveStore(Path(temp.name) / "evidence")
        self.spec = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        self.spec["id"] = "offline-paired-parallel-test"
        self.spec["dispatch"] = {"mode": "paired_parallel", "max_in_flight": 2}

    def test_control_probe_are_concurrent_and_replay_is_linked(self):
        gate = threading.Barrier(2, timeout=3)

        def handler(body, _timeout):
            gate.wait()
            return response(body)

        client = FakeClient(handler)
        first = execute(self.store, self.spec, client)
        second = execute(self.store, self.spec, client, first)
        exploration, confirmation = self.store.read_run(first), self.store.read_run(second)
        self.assertEqual(len(client.calls), 18)
        self.assertEqual(exploration["status"], "completed")
        self.assertEqual(confirmation["status"], "completed")
        self.assertEqual(confirmation_summary(exploration, confirmation)["status"], "not_supported")
        self.assertEqual({a["request"]["dispatch"]["mode"] for a in exploration["attempts"]}, {"paired_parallel"})
        self.assertEqual([a["request"]["dispatch"]["batch"] for a in exploration["attempts"]], [0, 0, 1, 1, 2, 2])

    def test_error_stops_after_inflight_pair_is_saved(self):
        gate = threading.Barrier(2, timeout=3)

        def handler(body, _timeout):
            gate.wait()
            if "\n\n" in body["messages"][0]["content"]:
                return {"http_status": 429, "transport_error": None}
            return response(body)

        client = FakeClient(handler)
        run_id = execute(self.store, self.spec, client)
        run = self.store.read_run(run_id)
        self.assertEqual(run["status"], "rate_limited")
        self.assertEqual(len(client.calls), 2)
        self.assertEqual(len(run["attempts"]), 2)
        self.assertFalse(run["unknown_attempts"])
        self.assertEqual(len(run["unexecuted_slots"]), 4)

    def test_cancel_finishes_inflight_pair_and_stops(self):
        gate = threading.Barrier(2, timeout=3)
        started = []

        def handler(body, _timeout):
            gate.wait()
            self.store.cancel(started[0])
            return response(body)

        client = FakeClient(handler)
        run_id = execute(self.store, self.spec, client, on_start=started.append)
        run = self.store.read_run(run_id)
        self.assertEqual(run["status"], "cancelled")
        self.assertEqual(len(run["attempts"]), 2)
        self.assertEqual(len(client.calls), 2)
        self.assertFalse(run["unknown_attempts"])

    def test_invalid_dispatch_rejected_before_store_start(self):
        for dispatch in ({"mode": "paired_parallel", "max_in_flight": 3},
                         {"mode": "unbounded", "max_in_flight": 2}):
            spec = copy.deepcopy(self.spec)
            spec["dispatch"] = dispatch
            with self.assertRaises(ValueError):
                validate_spec(spec)
        self.assertEqual(self.store.list_runs(), [])


if __name__ == "__main__":
    unittest.main()
