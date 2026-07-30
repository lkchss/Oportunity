"""Shared pytest fixtures.

Makes `ship/opportunity_finder` importable without an editable install, so the
test suite exercises the package source directly (an `pip install -e ship` is
also supported and covered separately by the packaging verification step).

Also stubs the three heavy optional third-party packages -- see below.
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

_SHIP_SRC = Path(__file__).resolve().parent.parent / "ship"
if str(_SHIP_SRC) not in sys.path:
    sys.path.insert(0, str(_SHIP_SRC))


# ------------------------------------------------------- heavy third-party stubs
#
# `anthropic`, `openai` and `trafilatura` are optional runtime dependencies that
# production code imports lazily, inside the function that needs them. Every
# test already fakes them at the call site (fake clients, injected openers), so
# no test asserts anything about real SDK or real extractor behaviour -- but
# executing their top-level imports still cost ~10s of a ~54s suite, because
# whichever test first reached the code path paid the whole import:
#
#     openai       ~4.3s  test_ship_wizard  TestValidatorTimeouts
#     trafilatura  ~2.8s  test_ship_fetch   TestSchemeRefusal (first _extract_text)
#     anthropic    ~2.7s  test_ship_pipeline TestRunCycleEndToEnd (via profile.py)
#
# That looked like three mysteriously slow tests; it was one import each, and
# nothing else. This repo reruns `pytest tests/ -q` after every .py edit, so
# that cost was being paid constantly for imports the suite never uses.
#
# Installing a stub in sys.modules before anything imports the real package
# removes it. Each stub goes in ONLY when the real package is actually
# installed, so `pytest.importorskip(...)` and the `except ImportError`
# fallbacks in wizard.py / llm.py / fetch.py behave exactly as they do in a
# real environment. The stubs expose only the names production code binds, and
# the SDK entry points raise when used for real rather than silently no-op'ing
# -- a future test that genuinely needs the SDK fails loudly instead of quietly
# passing against a mock.


def _unusable(package: str, attr: str) -> type:
    """A stand-in class that refuses to be constructed."""

    class _Unusable:
        def __init__(self, *args: object, **kwargs: object) -> None:
            raise RuntimeError(
                f"tests/conftest.py stubs the `{package}` SDK to keep the suite "
                f"fast, and {package}.{attr} was constructed for real. Fake it at "
                f"the call site, or drop the stub if this test needs the real SDK."
            )

    _Unusable.__name__ = _Unusable.__qualname__ = attr
    return _Unusable


def _stub_module(name: str, **attrs: object) -> None:
    if name in sys.modules:  # something already paid for the real import
        return
    try:
        if importlib.util.find_spec(name) is None:
            return  # genuinely not installed -- let the real ImportError happen
    except (ImportError, ValueError):  # pragma: no cover - defensive
        return
    module = types.ModuleType(name)
    for attr, value in attrs.items():
        setattr(module, attr, value)
    sys.modules[name] = module


def _declines_extraction(*args: object, **kwargs: object) -> None:
    """trafilatura.extract returns None when it judges a page to be
    boilerplate-only -- a normal, documented result that fetch._extract_text
    already handles by falling back to its stdlib tag stripper. That fallback
    is the path the fetch tests assert against either way, and it is what
    TestStdlibFallbackExtraction goes out of its way to force. The
    prefer-trafilatura branch is covered directly by
    TestExtractorPreference::test_trafilatura_result_wins_over_tag_stripper.
    """
    return None


_stub_module("anthropic", Anthropic=_unusable("anthropic", "Anthropic"))
_stub_module("openai", OpenAI=_unusable("openai", "OpenAI"))
_stub_module("trafilatura", extract=_declines_extraction)
