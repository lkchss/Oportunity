"""Shared pytest fixtures.

Makes `ship/opportunity_finder` importable without an editable install, so the
test suite exercises the package source directly (an `pip install -e ship` is
also supported and covered separately by the packaging verification step).
"""
from __future__ import annotations

import sys
from pathlib import Path

_SHIP_SRC = Path(__file__).resolve().parent.parent / "ship"
if str(_SHIP_SRC) not in sys.path:
    sys.path.insert(0, str(_SHIP_SRC))
