"""Preload the installed wheel before pytest discovers source-tree tests."""
from pathlib import Path
import sys

import batchalign

source_root = Path(__file__).resolve().parents[2] / "python"
if Path(batchalign.__file__).resolve().is_relative_to(source_root):
    raise RuntimeError("Wheel tests imported the source checkout")
import batchalign._core  # noqa: E402,F401 — require the installed native extension
import pytest  # noqa: E402

raise SystemExit(pytest.main(sys.argv[1:]))
