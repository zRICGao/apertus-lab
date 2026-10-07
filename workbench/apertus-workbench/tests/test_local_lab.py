import hashlib
import http.client
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import threading
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "experiments/src"), str(ROOT / "experiments/tests"), str(ROOT / "workbench/apertus-workbench")]
from local_lab import ReadOnlyStore, Workspace, server
from apertus_lab.live import execute
from apertus_lab.live_store import LiveStore
from test_mvp import FakeClient, response


class WorkspaceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        spec = json.loads((ROOT / "experiments/examples/live-spec.json").read_text(encoding="utf-8"))
        self.store = LiveStore(self.root / "ledger")
        client = FakeClient(lambda body, timeout: response(body, "BLUE"))
        self.first = execute(self.store, spec, client)
        self.second = execute(self.store, spec, client, self.first)
        config = self.root / "workspace.json"
        config.write_text(json.dumps({"schema_version": "1.0", "stores": {"fixture": "ledger", "empty": "absent"},
                                     "wiki_workspace": "wiki", "runtime_state": "runtime", "wiki_application": "wiki-app"}))
        self.ws = Workspace(self.root, config)

    def test_read_only_integrity_and_missing_store(self):
        before = self.store.path.read_bytes()
        snapshot = self.ws.snapshot()
        self.assertEqual([r["conclusion"] for r in snapshot["runs"]], ["not_supported"] * 2)
        self.assertEqual(sum(r["reserved_calls"] for r in snapshot["runs"]), 18)
        with self.assertRaises(sqlite3.OperationalError):
            ReadOnlyStore(self.store.root).cancel(self.first)
        with self.assertRaises(FileNotFoundError):
            self.ws.store("empty")
        self.assertFalse((self.root / "absent").exists())
        self.assertEqual(before, self.store.path.read_bytes())

    def test_corruption_is_visible(self):
        with self.store.connect() as db:
            db.execute("DROP TRIGGER no_UPDATE_results")
            db.execute("UPDATE results SET payload_hash='corrupted'")
        data = self.ws.snapshot()
        self.assertEqual(data["stores"][0]["status"], "unreadable_or_corrupt")
        self.assertEqual(data["runs"], [])

    def test_http_is_read_only_and_rejects_cross_origin_and_paths(self):
        service = server(self.ws, 0)
        thread = threading.Thread(target=service.serve_forever, daemon=True)
        thread.start()
        try:
            def get(path, method="GET", headers=None):
                conn = http.client.HTTPConnection("127.0.0.1", service.server_port, timeout=5)
                conn.request(method, path, headers=headers or {})
                result = conn.getresponse()
                data = result.read()
                conn.close()
                return result.status, data
            self.assertEqual(get("/api/snapshot")[0], 200)
            code, body = get(f"/api/run?store=fixture&id={self.first}")
            self.assertEqual(code, 200)
            self.assertEqual(len(json.loads(body)["attempts"]), 6)
            self.assertEqual(get("/api/snapshot", headers={"Host": "evil.example"})[0], 403)
            self.assertEqual(get("/api/snapshot", headers={"Origin": "https://evil.example"})[0], 403)
            self.assertEqual(get("/api/run", "POST")[0], 501)
            self.assertEqual(get("/../../management/lab-workspace.json")[0], 404)
            self.assertEqual(get("/api/run?store=unknown&id=no")[0], 400)
        finally:
            service.shutdown()
            service.server_close()
            thread.join()

    def test_knowledge_summary_preserves_negative_result_and_edits(self):
        from apertus_lab.knowledge import compile_candidate, check_sources
        runs = self.ws.runs("fixture")
        for run in runs:
            compile_candidate(self.ws.store("fixture"), run["run_id"], self.ws.wiki)
        self.ws.compile_pair(runs[1], runs)
        self.ws.compile_pair(runs[1], runs)
        pages = list((self.ws.wiki / "wiki").glob("run-pair-*.md"))
        self.assertEqual(len(pages), 1)
        self.assertIn('conclusion: "not_supported"', pages[0].read_text(encoding="utf-8"))
        self.assertTrue(all(r["freshness"] == "current" for r in check_sources(self.ws.wiki)))
        pages[0].write_text("edited by human", encoding="utf-8")
        with self.assertRaises(ValueError):
            self.ws.compile_pair(runs[1], runs)
        self.assertEqual(pages[0].read_text(), "edited by human")


if __name__ == "__main__":
    unittest.main()
