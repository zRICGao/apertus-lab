"""Adapter to the existing LLM Wiki workspace; never a replacement application."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from datetime import datetime, timezone

from apertus_lab.contracts import canonical


class Knowledge:
    def __init__(self, workspace: Path):
        self.workspace = workspace.resolve()
        self.sources = self.workspace / "sources" / "research-imports"

    def safe(self, path: Path) -> Path:
        if not path.resolve().is_relative_to(self.workspace) or any(p.is_symlink() for p in [path, *path.parents] if p.is_relative_to(self.workspace)):
            raise ValueError("Wiki path escapes workspace or uses a symbolic link")
        return path

    def wiki_paths(self):
        for p in sorted((self.workspace / "wiki").rglob("*.md")):
            try:
                self.safe(p)
                if p.stat().st_size <= 1_000_000:
                    name = p.relative_to(self.workspace).as_posix()
                    yield "wiki-" + hashlib.sha256(name.encode()).hexdigest()[:24], p
            except (OSError, ValueError):
                continue

    def ingest(self, title: str, text: str, license_name: str, source_url: str = "") -> dict:
        if not title.strip() or not license_name.strip() or len(text.encode()) > 1_000_000 or not text.strip():
            raise ValueError("Require title, source rights/license, and at most 1 MB of text")
        raw = text.encode("utf-8")
        sha = hashlib.sha256(raw).hexdigest()
        source_id = "source-" + sha[:24]
        self.safe(self.sources).mkdir(parents=True, exist_ok=True)
        path = self.sources / (source_id + ".md")
        metadata = {"id": source_id, "title": title[:200], "license": license_name[:200], "source_url": source_url[:2000],
                    "sha256": sha, "review_status": "candidate", "scope": "user-imported; applicability unreviewed"}
        self.safe(path)
        self.safe(path.with_suffix(".json"))
        if not path.exists():
            path.write_bytes(raw)
            path.with_suffix(".json").write_bytes(canonical(metadata))
        return self.read(source_id)

    def read(self, source_id: str) -> dict:
        if re.fullmatch(r"wiki-[a-f0-9]{24}", source_id):
            p = next((p for key, p in self.wiki_paths() if key == source_id), None)
            if p is None:
                raise ValueError("Unknown Wiki page")
            raw = p.read_bytes()
            text = raw.decode("utf-8")
            metadata = {}
            if text.startswith("---"):
                for line in text.split("---", 2)[1].strip().splitlines():
                    if ":" in line:
                        key, value = line.split(":", 1)
                        try:
                            metadata[key] = json.loads(value)
                        except ValueError:
                            metadata[key] = value.strip()
            refs = metadata.get("evidence_refs", [])
            valid = isinstance(refs, list) and bool(refs)
            for ref in refs if isinstance(refs, list) else []:
                try:
                    relative = Path(ref["path"])
                    if relative.is_absolute() or ".." in relative.parts:
                        raise ValueError()
                    source = self.safe(self.workspace / relative)
                    valid = valid and source.is_file() and hashlib.sha256(source.read_bytes()).hexdigest() == ref["sha256"]
                except (KeyError, ValueError, OSError, TypeError):
                    valid = False
            return {"id": source_id, "title": metadata.get("title", p.stem), "text": text,
                    "sha256": hashlib.sha256(raw).hexdigest(), "review_status": metadata.get("review_status", "candidate"),
                    "scope": metadata.get("scope", "unreviewed background; not a finding"),
                    "freshness": "current" if valid else "stale" if refs else "unverified",
                    "license": "source-specific; inspect linked provenance", "source_url": "", "origin": "existing_full_llmwiki"}
        if not re.fullmatch(r"source-[a-f0-9]{24}", source_id):
            raise ValueError("Invalid source identifier")
        p = self.safe(self.sources / (source_id + ".md"))
        if not p.is_file() or p.is_symlink() or p.with_suffix(".json").is_symlink():
            raise ValueError("Unknown source or unsupported link")
        metadata = json.loads(p.with_suffix(".json").read_text(encoding="utf-8"))
        raw = p.read_bytes()
        return {**metadata, "text": raw.decode("utf-8"), "freshness": "current" if hashlib.sha256(raw).hexdigest() == metadata["sha256"] else "stale"}

    def list(self, query: str = "") -> list[dict]:
        result = []
        keys = [p.stem for p in sorted(self.sources.glob("source-*.json"))] if self.sources.exists() else []
        keys += [key for key, _ in self.wiki_paths()]
        for key in keys:
            try:
                item = self.read(key)
            except (ValueError, OSError, UnicodeError):
                continue
            if query.casefold() in (item["title"] + " " + item["text"]).casefold():
                result.append({**item, "text": item["text"][:12000]})
            if len(result) == 50:
                break
        return result

    def sync(self, state: dict) -> str:
        """New immutable candidate page; edited pages never overwritten."""
        raw = canonical(state)
        state_hash = hashlib.sha256(raw).hexdigest()
        source_name = f'research-{state["id"]}-{state_hash[:12]}.json'
        source = self.safe(self.workspace / "sources" / source_name)
        source.parent.mkdir(parents=True, exist_ok=True)
        if source.exists() and source.read_bytes() != raw:
            raise ValueError("Existing Wiki evidence snapshot changed")
        if not source.exists():
            source.write_bytes(raw)
        metadata = {"title": "Research " + state["id"], "description": "Evidence-backed research summary; not a confirmed finding",
                    "date": datetime.fromtimestamp(state["created"], timezone.utc).date().isoformat(), "tags": ["apertus", "research"],
                    "review_status": "candidate", "mode": state["spec"]["mode"], "campaign_id": state["id"],
                    "scope": {"languages": state["spec"]["languages"], "model_revision": "unknown"},
                    "evidence_refs": [{"path": "sources/"+source_name, "sha256": state_hash}]}
        body = "---\n" + "\n".join(f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in metadata.items()) + "\n---\n\n"
        body += "# Research summary\n\n" + json.dumps(state["summary"], ensure_ascii=False, indent=2)
        body += "\n\n## Source calls\n" + "\n".join(f'- {c["id"]}: request {c["hash"]}; response {c["response_hash"]}' for c in state["calls"])
        digest = hashlib.sha256(body.encode()).hexdigest()
        path = self.safe(self.workspace / "wiki" / f'research-{state["id"]}-{digest[:12]}.md')
        path.parent.mkdir(parents=True, exist_ok=True)
        if path.exists() and path.read_text(encoding="utf-8") != body:
            raise ValueError("Existing Wiki page was edited; refusing overwrite")
        if not path.exists():
            path.write_text(body, encoding="utf-8")
        return path.name
