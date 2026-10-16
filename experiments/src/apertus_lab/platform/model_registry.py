"""Local, host-only model profiles for the interactive Probe workflow."""
from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from urllib.parse import urlsplit

from .providers import ENDPOINT, MODEL
from .store import uid


class ModelRegistry:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "models.json"

    def _default(self) -> dict:
        return {
            "profiles": [{
                "id": uid("model"), "name": "Apertus 70B", "model": os.environ.get("LLM_NAME") or MODEL,
                "base_url": (os.environ.get("LLM_BASE_URL") or ENDPOINT).rstrip("/"),
                "api_key": os.environ.get("LLM_API_KEY", ""), "created_at": time.time(), "updated_at": time.time(),
            }],
            "target_model_id": None, "assistant_model_id": None,
        }

    def _read(self) -> dict:
        if not self.path.exists():
            value = self._default()
            value["target_model_id"] = value["profiles"][0]["id"]
            value["assistant_model_id"] = value["profiles"][0]["id"]
            self._write(value)
            return value
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise ValueError(f"Model profile file is unreadable: {exc}") from None
        if not isinstance(value, dict) or not isinstance(value.get("profiles"), list):
            raise ValueError("Invalid model profile file")
        return value

    def _write(self, value: dict):
        fd, name = tempfile.mkstemp(prefix="models-", suffix=".json", dir=self.root)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(value, handle, ensure_ascii=False, indent=2)
                handle.write("\n")
            os.replace(name, self.path)
        finally:
            if os.path.exists(name):
                os.unlink(name)

    def _validate(self, data: dict, existing_id: str | None = None, allow_missing_key: bool = False) -> dict:
        if not isinstance(data, dict):
            raise ValueError("Model profile must be an object")
        name, model, base_url = str(data.get("name", "")).strip(), str(data.get("model", "")).strip(), str(data.get("base_url", "")).strip().rstrip("/")
        if not 1 <= len(name) <= 120 or not 1 <= len(model) <= 240:
            raise ValueError("Model name and model id are required")
        parsed = urlsplit(base_url)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError("Model endpoint must be an HTTPS base URL without credentials or query parameters")
        key = str(data.get("api_key", ""))
        if (not key and not allow_missing_key) or any(c in key for c in "\r\n"):
            raise ValueError("An API key is required")
        return {"id": existing_id or uid("model"), "name": name, "model": model, "base_url": base_url,
                "api_key": key, "created_at": float(data.get("created_at", time.time())), "updated_at": time.time()}

    def profiles(self) -> list[dict]:
        return self._read()["profiles"]

    def public(self) -> dict:
        value = self._read()
        return {"profiles": [{k: p[k] for k in ("id", "name", "model", "base_url", "created_at", "updated_at")} |
                             {"credentials_present": bool(p.get("api_key"))} for p in value["profiles"]],
                "target_model_id": value.get("target_model_id"), "assistant_model_id": value.get("assistant_model_id"),
                "path": "WORKBENCH_DATA/models.json"}

    def get(self, profile_id: str) -> dict:
        profile = next((p for p in self.profiles() if p["id"] == profile_id), None)
        if not profile:
            raise ValueError("Unknown model profile")
        return profile

    def add(self, data: dict) -> dict:
        value = self._read()
        profile = self._validate(data)
        value["profiles"].append(profile)
        value["target_model_id"] = value.get("target_model_id") or profile["id"]
        value["assistant_model_id"] = value.get("assistant_model_id") or profile["id"]
        self._write(value)
        return profile

    def update(self, profile_id: str, data: dict) -> dict:
        """Update a profile without exposing or replacing its key accidentally."""
        value = self._read()
        current = next((p for p in value["profiles"] if p["id"] == profile_id), None)
        if not current:
            raise ValueError("Unknown model profile")
        merged = {**current, **{k: v for k, v in data.items() if v is not None}}
        if not str(data.get("api_key", "")).strip():
            merged["api_key"] = current.get("api_key", "")
        profile = self._validate(merged, existing_id=profile_id, allow_missing_key=not current.get("api_key") and not str(data.get("api_key", "")).strip())
        profile["created_at"] = current.get("created_at", profile["created_at"])
        value["profiles"] = [profile if p["id"] == profile_id else p for p in value["profiles"]]
        self._write(value)
        return profile

    def remove(self, profile_id: str):
        value = self._read()
        if len(value["profiles"]) <= 1:
            raise ValueError("At least one model profile must remain")
        if not any(p["id"] == profile_id for p in value["profiles"]):
            raise ValueError("Unknown model profile")
        value["profiles"] = [p for p in value["profiles"] if p["id"] != profile_id]
        for key in ("target_model_id", "assistant_model_id"):
            if value.get(key) == profile_id:
                value[key] = value["profiles"][0]["id"]
        self._write(value)

    def select(self, profile_id: str, role: str):
        if role not in {"target", "assistant"}:
            raise ValueError("Unknown model role")
        self.get(profile_id)
        value = self._read()
        value["target_model_id" if role == "target" else "assistant_model_id"] = profile_id
        self._write(value)
        return self.public()
