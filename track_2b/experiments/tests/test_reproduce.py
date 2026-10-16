import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from apertus_lab.contracts import digest
from apertus_lab.reproduce import main, resolve_spec
from test_mvp import FakeClient


class ReproduceTests(unittest.TestCase):
    def setUp(self):
        self.template_path = Path(__file__).resolve().parents[1] / "examples/live-spec.json"
        self.template = json.loads(self.template_path.read_text(encoding="utf-8"))

    def test_auto_ids_preserve_template_and_other_configuration(self):
        original = digest(self.template)
        first = resolve_spec(self.template, "auto")
        second = resolve_spec(self.template, "auto")
        self.assertNotEqual(first["id"], second["id"])
        self.assertEqual({**first, "id": self.template["id"]}, self.template)
        self.assertEqual(original, digest(self.template))
        long_template = {**self.template, "id": "a" * 80}
        self.assertEqual(len(resolve_spec(long_template, "auto")["id"]), 80)
        self.assertEqual(resolve_spec(self.template, None), self.template)
        with self.assertRaises(ValueError):
            resolve_spec(self.template, "../../bad")

    def test_two_auto_launches_and_duplicate_manual_id_in_one_store(self):
        with tempfile.TemporaryDirectory() as temp:
            store = Path(temp)
            client = FakeClient()
            def launch(experiment_id):
                argv = ["reproduce", "--spec", str(self.template_path), "--store", temp,
                        "--experiment-id", experiment_id]
                with patch("sys.argv", argv), patch("apertus_lab.reproduce.CSCSClient", return_value=client), contextlib.redirect_stdout(io.StringIO()):
                    return main()
            self.assertEqual(launch("auto"), 0)
            self.assertEqual(launch("auto"), 0)
            summaries = [json.loads(p.read_text(encoding="utf-8")) for p in store.glob("summary-*.json")]
            self.assertEqual(len({s["experiment_id"] for s in summaries}), 2)
            self.assertEqual(len(client.calls), 36)
            launches = list(store.glob("launch-*.json"))
            self.assertEqual(len(launches), 4)
            for path in launches:
                record = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(record["template_sha256"], digest(self.template))
                self.assertEqual(record["spec_sha256"], digest(record["spec"]))
                self.assertEqual(record["experiment_id"], record["spec"]["id"])
            self.assertEqual(launch("manual-reproduction-01"), 0)
            before = len(client.calls)
            with self.assertRaisesRegex(ValueError, "phase already exists"):
                launch("manual-reproduction-01")
            self.assertEqual(len(client.calls), before)
