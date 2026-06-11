"""
Playwright browser test for Saved Scenarios feature.

Verifies:
  1. Fill form → save as "Scenario A".
  2. Change LSAT → save as "Scenario B".
  3. Load "Scenario A" → form shows A's original LSAT.
  4. Delete "Scenario B" → it is gone from the list.
  5. Reload page → "Scenario A" persists in localStorage.
  6. 0 console errors throughout.

Run with: pytest tests/test_scenarios_playwright.py -v
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


LSAT_A = "163"
LSAT_B = "170"

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

        # Start on intake screen with a clean slate
        page.goto(BASE_URL, wait_until="networkidle", timeout=15000)
        # Clear any stale scenario data from prior runs
        page.evaluate("() => localStorage.removeItem('oplaw-v2-scenarios')")
        page.reload(wait_until="networkidle")

        yield
        browser.close()


def _fill_lsat(lsat: str):
    """Set the LSAT field to the given value."""
    _PAGE.locator('input[type="number"][min="120"]').fill(lsat)


def _fill_gpa():
    """Set a valid GPA."""
    _PAGE.locator('input[type="number"][step="0.01"]').fill("3.75")


def _save_scenario(name: str):
    """Click '+ Save scenario', type name, click Save."""
    _PAGE.get_by_role("button", name="+ Save scenario").click()
    _PAGE.locator(".sc-name-input").fill(name)
    _PAGE.get_by_role("button", name="Save").click()


def _open_scenario_list():
    """Click the Scenarios toggle to open the list."""
    toggle = _PAGE.locator(".sc-toggle")
    if toggle.is_visible():
        # Only click if the list isn't already open
        if not _PAGE.locator(".sc-list").is_visible():
            toggle.click()


def test_intake_screen_loads():
    """Intake form is visible."""
    assert _PAGE.locator('input[type="number"][min="120"]').is_visible()


def test_save_scenario_a():
    """Fill form with LSAT_A and save as 'Scenario A'."""
    _fill_lsat(LSAT_A)
    _fill_gpa()
    _save_scenario("Scenario A")
    # After saving, the list should open and show Scenario A
    _open_scenario_list()
    _PAGE.wait_for_selector(".sc-list", timeout=3000)
    items = _PAGE.locator(".sc-load-btn")
    names = [items.nth(i).inner_text() for i in range(items.count())]
    assert "Scenario A" in names, f"Scenario A not found in list: {names}"


def test_save_scenario_b():
    """Change LSAT to LSAT_B and save as 'Scenario B'."""
    _fill_lsat(LSAT_B)
    _save_scenario("Scenario B")
    _open_scenario_list()
    _PAGE.wait_for_selector(".sc-list", timeout=3000)
    items = _PAGE.locator(".sc-load-btn")
    names = [items.nth(i).inner_text() for i in range(items.count())]
    assert "Scenario B" in names, f"Scenario B not found in list: {names}"
    assert "Scenario A" in names, f"Scenario A disappeared: {names}"


def test_load_scenario_a_restores_lsat():
    """Loading Scenario A fills the form with LSAT_A (not LSAT_B)."""
    _open_scenario_list()
    _PAGE.wait_for_selector(".sc-list", timeout=3000)

    # Find and click the "Scenario A" load button
    items = _PAGE.locator(".sc-load-btn")
    for i in range(items.count()):
        if items.nth(i).inner_text() == "Scenario A":
            items.nth(i).click()
            break

    # The LSAT field should now show LSAT_A
    lsat_val = _PAGE.locator('input[type="number"][min="120"]').input_value()
    assert lsat_val == LSAT_A, f"Expected LSAT {LSAT_A} after loading Scenario A, got {lsat_val}"


def test_delete_scenario_b():
    """Delete 'Scenario B'; assert it is gone from the list."""
    _open_scenario_list()
    _PAGE.wait_for_selector(".sc-list", timeout=3000)

    # Find the delete button for Scenario B
    items = _PAGE.locator(".sc-item")
    for i in range(items.count()):
        item = items.nth(i)
        load_btn = item.locator(".sc-load-btn")
        if load_btn.inner_text() == "Scenario B":
            item.locator(".sc-del").click()
            break

    # Give React a tick to re-render
    _PAGE.wait_for_timeout(200)

    # Scenario B should be gone
    # Check via localStorage to be definitive
    scenarios_raw = _PAGE.evaluate("() => localStorage.getItem('oplaw-v2-scenarios')")
    import json
    scenarios = json.loads(scenarios_raw) if scenarios_raw else {}
    assert "Scenario B" not in scenarios, f"Scenario B still in localStorage: {scenarios}"
    assert "Scenario A" in scenarios, f"Scenario A was also removed: {scenarios}"


def test_persistence_after_reload():
    """Reload the page; Scenario A should still be in the list."""
    _PAGE.reload(wait_until="networkidle")

    # The scenarios toggle should appear (count > 0)
    _open_scenario_list()
    _PAGE.wait_for_selector(".sc-list", timeout=3000)
    items = _PAGE.locator(".sc-load-btn")
    names = [items.nth(i).inner_text() for i in range(items.count())]
    assert "Scenario A" in names, f"Scenario A not found after reload: {names}"
    assert "Scenario B" not in names, f"Scenario B should have been deleted: {names}"


def test_zero_console_errors():
    """No console errors across the whole session."""
    console_errs = [e for e in _ERRORS if isinstance(e, ConsoleMessage)]
    assert len(console_errs) == 0, (
        f"Expected 0 console errors, got {len(console_errs)}: "
        + str([e.text for e in console_errs[:5]])
    )
