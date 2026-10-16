"""Repository-local entry point; works without PYTHONPATH setup."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "workbench" / "apertus-workbench"))
from local_lab import main

if __name__ == "__main__":
    raise SystemExit(main(ROOT))
