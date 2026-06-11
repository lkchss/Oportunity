"""
Playwright browser test for TweaksPanel.

Verifies:
  1. Profile → results renders with no console errors.
  2. "Adjust weights" button is visible on results screen.
  3. Clicking it opens the TweaksPanel.
  4. Moving a slider causes re-ranking without console errors.
  5. Reset button returns weights to defaults (re-submits).
  6. 0 console errors throughout.

Run with: pytest tests/test_tweaks_playwright.py -v
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


def _fill_and_submit(page):
    """Fill in the intake form and submit to reach results screen."""
    page.goto(BASE_URL, wait_until="networkidle", timeout=15000)

    # LSAT — first number input (min=120, max=180)
    page.locator('input[type="number"][min="120"]').fill("163")

    # GPA — second number input (step=0.01)
    page.locator('input[type="number"][step="0.01"]').fill("3.75")

    # Career goal — first select (Unsure/BigLaw/etc.)
    page.locator('select').first.select_option("BigLaw / In-house")

    # Target state — second select (state dropdown)
    page.locator('select').nth(1).select_option("NY")

    # Submit — the "Find my schools" primary button
    page.get_by_role("button", name="Find my schools").click()

    # Wait for results to appear
    page.wait_for_selector(".school-card, .tier-section", timeout=20000)


# Use a module-scoped fixture so the browser session persists across tests
# (they run in dependency order).
_PAGE = None
_ERRORS = []


@pytest.fixture(scope="module", autouse=True)
def browser_session():
    global _PAGE, _ERRORS
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        ctx = browser.new_context()
        page = ctx.new_page()
        page.on("console", lambda msg: _ERRORS.append(msg) if msg.type == "error" else None)
        page.on("pageerror", lambda err: _ERRORS.append(err))
        _PAGE = page
        _fill_and_submit(page)
        yield
        browser.close()


def test_results_screen_has_school_cards():
    """After profile submit, results screen should show school cards."""
    cards = _PAGE.query_selector_all(".school-card")
    assert len(cards) > 0, "Expected school cards on results screen"


def test_adjust_weights_button_visible():
    """Trigger button should be in the results toolbar."""
    btn = _PAGE.get_by_role("button", name="Adjust weights")
    assert btn.is_visible(), "Adjust weights button should be visible"


def test_open_tweaks_panel():
    """Clicking Adjust weights opens the TweaksPanel."""
    _PAGE.get_by_role("button", name="Adjust weights").click()
    panel = _PAGE.locator(".twp-panel")
    panel.wait_for(state="visible", timeout=3000)
    assert panel.is_visible(), "TweaksPanel did not open"


def test_panel_has_six_sliders():
    """TweaksPanel should expose exactly 6 score-weight sliders."""
    sliders = _PAGE.locator(".twp-panel .twp-slider")
    count = sliders.count()
    assert count == 6, f"Expected 6 weight sliders, got {count}"


def test_move_slider_no_console_errors():
    """Dragging the Financial slider to 2.5 should re-rank without console errors."""
    sliders = _PAGE.locator(".twp-panel .twp-slider")
    fin_slider = sliders.nth(5)  # Financial is last
    fin_slider.fill("2.5")
    fin_slider.dispatch_event("input")
    fin_slider.dispatch_event("change")

    # Wait for debounce + re-render (debounce = 400 ms, add buffer)
    _PAGE.wait_for_timeout(800)

    # Results should still render
    cards = _PAGE.query_selector_all(".school-card")
    assert len(cards) > 0, "School cards disappeared after weight change"

    # No console errors
    console_errs = [e for e in _ERRORS if isinstance(e, ConsoleMessage)]
    assert len(console_errs) == 0, (
        f"Console errors after slider move: {[e.text for e in console_errs[:5]]}"
    )


def test_reset_returns_to_defaults():
    """Reset button re-submits and returns to default weights."""
    reset_btn = _PAGE.locator(".twp-panel .twp-reset")
    assert not reset_btn.is_disabled(), "Reset should be enabled after weight change"
    reset_btn.click()

    # Wait for debounce + re-render
    _PAGE.wait_for_timeout(800)

    # Results still visible
    cards = _PAGE.query_selector_all(".school-card")
    assert len(cards) > 0, "School cards disappeared after reset"

    # Reset button should now be disabled (back to defaults)
    assert reset_btn.is_disabled(), "Reset should be disabled when at defaults"


def test_close_panel():
    """✕ button closes the panel."""
    close_btn = _PAGE.locator(".twp-panel .twp-x")
    close_btn.click()
    _PAGE.wait_for_selector(".twp-panel", state="hidden", timeout=2000)
    assert not _PAGE.locator(".twp-panel").is_visible(), "Panel should be hidden after close"


def test_zero_console_errors_total():
    """Final assertion: no console errors across the whole session."""
    console_errs = [e for e in _ERRORS if isinstance(e, ConsoleMessage)]
    assert len(console_errs) == 0, (
        f"Expected 0 total console errors, got {len(console_errs)}: "
        + str([e.text for e in console_errs[:5]])
    )
