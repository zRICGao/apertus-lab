"""Cross-platform test entry with an explicitly writable temporary directory."""
from pathlib import Path
import os
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
temporary = ROOT / "experiments/results/test-temp"
temporary.mkdir(parents=True, exist_ok=True)
os.environ["TEMP"] = os.environ["TMP"] = str(temporary)
tempfile.tempdir = str(temporary)
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
suite = unittest.defaultTestLoader.discover(str(ROOT / "src/tests"), pattern="test_platform.py")
raise SystemExit(not unittest.TextTestRunner(verbosity=2).run(suite).wasSuccessful())
