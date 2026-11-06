"""Drive one Victim browser: sign in, open the supplied URL, wait for it to settle."""

from __future__ import annotations

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import sync_playwright

LOGIN_TIMEOUT_MS = 15_000
NAVIGATION_TIMEOUT_MS = 20_000
SETTLE_MS = 1_500

USERNAME_FIELD = 'input[name="username"]'
PASSWORD_FIELD = 'input[name="password"]'
SUBMIT_BUTTON = 'button[type="submit"]'


class VictimError(RuntimeError):
    """The Victim could not sign in or could not open the target."""


def visit(base_url: str, target_url: str, username: str, password: str) -> None:
    """Sign ``username`` in at ``base_url``, then open ``target_url`` exactly once."""
    base = base_url.rstrip("/")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            _sign_in(page, base, username, password)
            try:
                page.goto(
                    target_url, wait_until="networkidle", timeout=NAVIGATION_TIMEOUT_MS
                )
            except PlaywrightError as error:
                raise VictimError(f"could not open {target_url}: {error}") from error
            page.wait_for_timeout(SETTLE_MS)
        finally:
            browser.close()


def _sign_in(page, base: str, username: str, password: str) -> None:
    sign_in_url = base + "/login"
    try:
        page.goto(sign_in_url, wait_until="domcontentloaded", timeout=LOGIN_TIMEOUT_MS)
        page.fill(USERNAME_FIELD, username)
        page.fill(PASSWORD_FIELD, password)
        with page.expect_navigation(
            wait_until="networkidle", timeout=LOGIN_TIMEOUT_MS
        ):
            page.click(SUBMIT_BUTTON)
    except PlaywrightError as error:
        raise VictimError(f"could not sign in at {sign_in_url}: {error}") from error
    if "/login" in page.url or page.locator(PASSWORD_FIELD).count():
        raise VictimError(
            f"signing in as {username!r} did not succeed (still on {page.url})"
        )
