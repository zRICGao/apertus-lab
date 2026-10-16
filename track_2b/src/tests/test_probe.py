import json
from pathlib import Path
import tempfile
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from fastapi.testclient import TestClient

from apertus_lab.platform.api import create_app
from apertus_lab.platform.model_registry import ModelRegistry
from apertus_lab.platform.probe import ProbeRuntime
from apertus_lab.platform.providers import ConfiguredProvider
from apertus_lab.platform.store import Store


class ProbeTests(unittest.TestCase):
    def test_model_registry_redacts_key_and_persists_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            registry = ModelRegistry(root)
            first = registry._read()["profiles"][0]
            first["api_key"] = "probe-secret"
            registry._write({"profiles": [first], "target_model_id": first["id"], "assistant_model_id": first["id"]})
            public = registry.public()
            self.assertNotIn("probe-secret", json.dumps(public))
            self.assertTrue(public["profiles"][0]["credentials_present"])
            self.assertIn("probe-secret", (root / "models.json").read_text(encoding="utf-8"))

    def test_probe_translation_test_confirmation_and_save(self):
        with tempfile.TemporaryDirectory() as directory:
            root, store = Path(directory), Store(Path(directory))
            registry = ModelRegistry(root)
            profile = registry._read()["profiles"][0]
            profile["api_key"] = "fixture-key"
            registry._write({"profiles": [profile], "target_model_id": profile["id"], "assistant_model_id": profile["id"]})
            job = store.probe_create("bias_fairness", "same evidence", ["zh", "en", "de"], profile["id"], profile["id"])

            def fake_send(self, request, payload, timeout):
                return {"valid": True, "reason": "ok", "text": payload["phase"] + "-" + payload["language"], "model": self.model, "mode": "live"}

            with patch.object(ConfiguredProvider, "send", fake_send):
                runtime = ProbeRuntime(store)
                with ThreadPoolExecutor(max_workers=10) as pool:
                    futures = {}
                    for _ in range(30):
                        runtime.tick(pool, futures)
                        time.sleep(.01)
                self.assertEqual(store.probe_get(job)["status"], "waiting_confirmation")
                with self.assertRaises(ValueError):
                    store.probe_start_test(job, False)
                store.probe_start_test(job, True)
                with ThreadPoolExecutor(max_workers=10) as pool:
                    futures = {}
                    for _ in range(30):
                        runtime.tick(pool, futures)
                        time.sleep(.01)
                state = store.probe_get(job)
                self.assertEqual(state["status"], "completed")
                self.assertEqual(len(state["calls"]), 6)
                record = store.probe_save(job, {"job": job, "calls": state["calls"]})
                self.assertTrue(record.startswith("probe-record-"))
                with self.assertRaises(ValueError):
                    store.probe_discard(job)

    def test_probe_api_requires_confirmation_and_never_returns_key(self):
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(Path.cwd(), Path(directory)))
            models = client.get("/api/v1/models").json()
            self.assertNotIn("api_key", json.dumps(models))
            profile = models["profiles"][0]
            response = client.post("/api/v1/probe/suggestions", json={"domain_id": "bias_fairness", "context": "x", "assistant_model_id": profile["id"]})
            self.assertEqual(response.status_code, 422)
            response = client.post("/api/v1/probe/jobs", json={"domain_id": "bias_fairness", "prompt": "x", "languages": ["zh"], "target_model_id": profile["id"], "assistant_model_id": profile["id"]})
            self.assertEqual(response.status_code, 201)
            state = client.get("/api/v1/probe/jobs/" + response.json()["id"]).json()
            self.assertEqual(state["status"], "queued")

    def test_model_update_redacts_key_and_allows_first_run_without_credentials(self):
        with tempfile.TemporaryDirectory() as directory:
            client = TestClient(create_app(Path.cwd(), Path(directory)))
            profile = client.get("/api/v1/models").json()["profiles"][0]
            renamed = client.patch(f"/api/v1/models/{profile['id']}", json={"name": "Local Apertus"})
            self.assertEqual(renamed.status_code, 200)
            self.assertEqual(renamed.json()["profiles"][0]["name"], "Local Apertus")
            configured = client.patch(f"/api/v1/models/{profile['id']}", json={"api_key": "fixture-key"})
            self.assertEqual(configured.status_code, 200)
            self.assertTrue(configured.json()["profiles"][0]["credentials_present"])
            self.assertNotIn("fixture-key", configured.text)


if __name__ == "__main__":
    unittest.main()
