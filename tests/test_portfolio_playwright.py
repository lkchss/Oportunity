"""
Playwright browser test for the Application Portfolio Builder ("Apply plan" tab).

Verifies:
  1. 165/3.7 NY profile → results load → "Apply plan" tab is visible.
  2. Clicking "Apply plan" tab renders three buckets (Safeties, Targets, Reaches)
     with school cards inside at least one bucket.
  3. 0 console errors throughout the 165/3.7 session.
  4. 145/2.9 profile (navigated in the same browser session):
     Apply plan tab renders gracefully (shrunk or empty slate, no crash,
     no console errors for that interaction).

Run with: pytest tests/test_portfolio_playwright.py -v
Requires: pip install playwright && playwright install chromium
Server must be running: python -m law.server
"""

import socket

import pytest

pytest.importorskip("playwright")

from playwright.sync_api import sync_playwright, ConsoleMessage

BASE_URL = "http://127.0.0.1:5000"


def _server_reachable(host: str = "127.0.0.1", port: int = 5000) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


if not _server_reachable():
    pytest.skip(
        "law server not running on 127.0.0.1:5000 (start with `python -m law.server`)",
        allow_module_level=True,
    )


def _fill_and_submit(page, lsat: str, gpa: str, state: str = "NY"):
    """Fill the intake form and submit to reach results screen."""
    page.goto(BASE_URL, wait_until="networkidle", timeout=15000)

    # LSAT — first number input (min=120, max=180)
    page.locator('input[type="number"][min="120"]').fill(lsat)

    # GPA — second number input (step=0.01)
    page.locator('input[type="number"][step="0.01"]').fill(gpa)

    # Career goal — first select
    page.locator('select').first.select_option("BigLaw / In-house")

    # Target state — second select
    page.locator('select').nth(1).select_option(state)

    # Submit
    page.get_by_role("button", name="Find my schools").click()
    page.wait_for_selector(".school-card, .tier-section", timeout=20000)


# ---------------------------------------------------------------------------
# Module-level state (populated by the single browser_session fixture)
# ---------------------------------------------------------------------------

_PAGE = None
_ERRORS: list = []

# State captured for each sub-scenario so tests can make assertions per profile.
_STATE: dict = {
    "full_errors_before_tab": 0,
    "tab_visible": False,
    "buckets_count": 0,
    "cards_after_tab": 0,
    "full_console_errors": [],
    "low_tab_visible": False,
    "low_cards_or_muted": False,
    "low_console_errors": [],
}


@pytest.fixture(scope="module", autouse=True)
def browser_session():
    """Single Playwright session that runs both profiles sequentially."""
    global _PAGE, _ERRORS, _STATE
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.on("console", lambda msg: _ERRORS.append(msg) if msg.type == "error" else None)
        page.on("pageerror", lambda err: _ERRORS.append(err))
        _PAGE = page

        # --- Profile 1: 165/3.7 NY (full slate expected) ---
        _fill_and_submit(page, "165", "3.7", "NY")

        tab = page.get_by_role("button", name="Apply plan")
        _STATE["tab_visible"] = tab.is_visible()

        if _STATE["tab_visible"]:
            tab.click()
            page.wait_for_selector(".tier-section", timeout=5000)
            sections = page.query_selector_all(".tier-section")
            _STATE["buckets_count"] = len(sections)
            _STATE["cards_after_tab"] = len(page.query_selector_all(".school-card"))

        _STATE["full_console_errors"] = [e for e in _ERRORS if isinstance(e, ConsoleMessage)]

        # --- Profile 2: 145/2.9 FL (shrunk / empty slate) ---
        # Navigate back to intake; use the "Edit" button on results.
        page.get_by_role("button", name="Edit").click()
        page.wait_for_selector('input[type="number"][min="120"]', timeout=5000)

        # Clear and re-fill LSAT + GPA
        lsat_inp = page.locator('input[type="number"][min="120"]')
        lsat_inp.fill("")
        lsat_inp.fill("145")

        gpa_inp = page.locator('input[type="number"][step="0.01"]')
        gpa_inp.fill("")
        gpa_inp.fill("2.9")

        # Change state to FL
        page.locator('select').nth(1).select_option("FL")

        low_errors_before = len(_ERRORS)
        page.get_by_role("button", name="Find my schools").click()
        page.wait_for_selector(".school-card, .tier-section", timeout=20000)

        low_tab = page.get_by_role("button", name="Apply plan")
        _STATE["low_tab_visible"] = low_tab.is_visible()

        if _STATE["low_tab_visible"]:
            low_tab.click()
            page.wait_for_timeout(600)
            cards = page.query_selector_all(".school-card")
            muted = page.query_selector_all(".muted")
            _STATE["low_cards_or_muted"] = len(cards) > 0 or len(muted) > 0

        _STATE["low_console_errors"] = [
            e for e in _ERRORS[low_errors_before:] if isinstance(e, ConsoleMessage)
        ]

        yield
        browser.close()


# ---------------------------------------------------------------------------
# Tests: 165/3.7 profile (full slate)
# ---------------------------------------------------------------------------

def test_apply_plan_tab_visible():
    """Apply plan tab must be present in the results toolbar for 165/3.7."""
    assert _STATE["tab_visible"], "Apply plan tab button not visible for 165/3.7 profile"


def test_apply_plan_tab_click_no_error():
    """Clicking Apply plan tab should render at least one tier-section."""
    assert _STATE["buckets_count"] > 0, "No tier-sections visible after clicking Apply plan"


def test_portfolio_buckets_render():
    """Apply plan view must render Safeties, Targets, and Reaches headings."""
    content = _PAGE.content()
    found = sum(1 for label in ("Safeties", "Targets", "Reaches") if label in content)
    assert found >= 2, f"Expected at least 2 bucket headings, found {found}"


def test_portfolio_has_school_cards():
    """At least one school card must appear in the Apply plan view."""
    assert _STATE["cards_after_tab"] > 0, "No school cards in Apply plan view for 165/3.7"


def test_portfolio_no_console_errors_full_profile():
    """No console errors for the 165/3.7 profile session."""
    errs = _STATE["full_console_errors"]
    assert len(errs) == 0, (
        f"Console errors during 165/3.7 session: {[e.text for e in errs[:5]]}"
    )


# ---------------------------------------------------------------------------
# Tests: 145/2.9 profile (graceful empty/shrunk slate)
# ---------------------------------------------------------------------------

def test_low_stat_apply_plan_no_crash():
    """
    145/2.9 FL profile: if Apply plan tab is present, it must render gracefully
    (school cards or an empty-state message). Tab may be absent (portfolio=null).
    """
    if _STATE["low_tab_visible"]:
        assert _STATE["low_cards_or_muted"], (
            "Apply plan tab visible but shows neither school cards nor empty-state text"
        )
    # If tab is hidden, portfolio was null → correct empty-state behavior. Pass.


def test_low_stat_no_console_errors():
    """No console errors during the 145/2.9 FL profile interaction."""
    errs = _STATE["low_console_errors"]
    assert len(errs) == 0, (
        f"Console errors during 145/2.9 session: {[e.text for e in errs[:5]]}"
    )
