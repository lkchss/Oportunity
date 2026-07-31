"""Shared pytest fixtures.

Makes `ship/opportunity_finder` importable without an editable install, so the
test suite exercises the package source directly (an `pip install -e ship` is
also supported and covered separately by the packaging verification step).

Also stubs the three heavy optional third-party packages -- see below -- and
disables opportunity_finder.sources' network-calling connectors by default
-- see _disable_structured_sources_by_default below.
"""
from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import platformdirs
import pytest

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


# ------------------------------------------------------- structured sources off by default
#
# opportunity_finder.sources adds network-calling connectors (apprenticeship.
# gov, College Scorecard, grants.gov, a doctrine.toml hub crawl) to
# pipeline.run_cycle's discover stage, on by default in production (its own
# kill switch, env OPP_STRUCTURED_SOURCES, defaults to enabled). Every
# pre-existing run_cycle test predates that module and does not inject a
# fetcher for it, so without this it would make REAL network calls under
# pytest -- confirmed the hard way: wiring it in briefly leaked a real
# grants.gov URL into test_ship_pipeline.py's end-to-end assertions. Off by
# default for the whole suite, same rationale as the SDK stubs above;
# tests/test_ship_sources.py re-enables it for its own file.
@pytest.fixture(autouse=True)
def _disable_structured_sources_by_default(monkeypatch):
    monkeypatch.setenv("OPP_STRUCTURED_SOURCES", "0")


# ------------------------------------------------------- platformdirs isolation by default
#
# opportunity_finder.config.get_or_create_user_key() (added for the per-user-
# identity ship work) WRITES to config.toml on first call -- every other
# config.py function before it only ever READ config.toml. It's called from
# pipeline.run_cycle (every cycle_start event) and web/server.py's
# /api/config, both exercised by most of test_ship_pipeline.py and
# test_ship_web.py, essentially none of which isolate config.config_path /
# platformdirs today, because until now nothing they touched ever wrote to
# disk. Without a default sandbox here, the FIRST such test in a suite run
# would create-or-mutate a real config.toml under this machine's actual
# platformdirs path -- exactly the kind of hidden real-filesystem effect
# this file already goes out of its way to avoid above (see the SDK stubs),
# and several individual test files already hand-roll this same isolation
# for tests that DO know they touch config (test_ship_wizard.py's `sandbox`
# fixture, test_ship_cli_run_profile.py's `sandbox` fixture, ad-hoc
# config.config_path overrides in test_ship_web.py / test_ship_llm.py /
# test_ship_pipeline.py) -- this just makes that the default everywhere else
# too. A test that wants a specific config.toml on disk still monkeypatches
# config.config_path / platformdirs itself, same as today: monkeypatch calls
# layer cleanly (last setattr wins for the duration of a test, unwound in
# reverse order at teardown), so an explicit override in a test's own
# fixture is never fought by this default.
@pytest.fixture(autouse=True)
def _isolate_platformdirs_by_default(monkeypatch, tmp_path):
    monkeypatch.setattr(platformdirs, "user_config_dir",
                        lambda *a, **k: str(tmp_path / "_autouse_config"))
    monkeypatch.setattr(platformdirs, "user_data_dir",
                        lambda *a, **k: str(tmp_path / "_autouse_data"))
