"""Extract the approved, dependency-light BreachWeave assets reproducibly."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "workbench/BreachWeave"
DEST = ROOT / "workbench/apertus-workbench/vendor/breachweave"
REVISION = "4ac5fc4c720ac74cf90968251cfae7cd28d3d62f"
FILES = (
    "LICENSE",
    "packages/core/src/challenge/memory.ts",
    "packages/core/src/solver/extension/challenge-observer/types.ts",
    "packages/core/src/solver/extension/challenge-observer/board-format.ts",
)


def source_blob(path: str) -> bytes:
    return subprocess.check_output([
        "git", "-c", f"safe.directory={SOURCE.as_posix()}", "-C", str(SOURCE),
        "show", f"{REVISION}:{path}",
    ])


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Verify without writing")
    args = parser.parse_args()
    entries = []
    for relative in FILES:
        data = source_blob(relative)
        target = DEST / relative
        if args.check:
            if not target.is_file() or target.read_bytes() != data:
                raise SystemExit(f"Asset mismatch: {relative}")
        elif target.exists() and target.read_bytes() != data:
            raise SystemExit(f"Refusing to overwrite modified asset: {relative}")
        else:
            if not args.check:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(data)
        entries.append({"path": relative, "sha256": hashlib.sha256(data).hexdigest()})
    manifest = {
        "source": "https://github.com/m-sec-org/BreachWeave",
        "revision": REVISION, "license": "Apache-2.0", "modified": False,
        "files": entries,
    }
    path = DEST / "manifest.json"
    encoded = (json.dumps(manifest, indent=2) + "\n").encode()
    if args.check:
        if path.read_bytes() != encoded:
            raise SystemExit("Manifest mismatch")
    else:
        path.write_bytes(encoded)
    print(f"{'Verified' if args.check else 'Extracted'} {len(FILES)} assets at {REVISION}")


if __name__ == "__main__":
    main()
