"""Workspace entry point for BASIC exploration."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "experiments" / "src"))
from apertus_lab.basic_cli import main

if __name__ == "__main__":
    raise SystemExit(main())
