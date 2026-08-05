"""Renew and optionally reload PythonAnywhere web apps through their dashboard.

The script attaches to a Chrome instance that was started with remote debugging
enabled. It reuses the PythonAnywhere login in that browser and never reads or
stores account credentials.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import asdict, dataclass
from typing import Any
from urllib.parse import urljoin, urlparse

PYTHONANYWHERE_ORIGIN = "https://www.pythonanywhere.com"
ALLOWED_ACCOUNT_HOSTS = {
    "www.pythonanywhere.com",
    "eu.pythonanywhere.com",
}
DEFAULT_CDP_URL = "http://127.0.0.1:9222"
CONTROL_SELECTOR = (
    "button, input[type='submit'], input[type='button'], "
    "a[role='button'], a.btn"
)
RENEW_LABEL = re.compile(
    r"(?:"
    r"\brun\s+until\b"
    r"|\bextend(?:\s+(?:this\s+)?web\s+app"
    r"|\s+for\s+(?:another\s+)?(?:month|week))\b"
    r"|^\W*renew(?:\s+(?:this\s+)?web\s+app)?\W*$"
    r")",
    re.IGNORECASE,
)
RELOAD_LABEL = re.compile(r"\breload(?:\s+web\s+app)?\b", re.IGNORECASE)
DESTRUCTIVE_LABEL = re.compile(r"\b(?:delete|disable|remove)\b", re.IGNORECASE)
WEBAPPS_PATH = re.compile(r"^/user/([^/]+)/webapps/?$")
DASHBOARD_PATH = re.compile(r"^/user/([^/]+)/?$")


class RenewalError(RuntimeError):
    """Raised when a safe renewal cannot be completed."""


@dataclass(frozen=True, slots=True)
class RenewalResult:
    account: str
    dashboard_url: str
    renewal_controls_found: int
    renewed: int
    reload_controls_found: int
    reloaded: int
    dry_run: bool


def account_from_webapps_url(url: str) -> str | None:
    """Return the account name encoded in a PythonAnywhere Web-tab URL."""
    parsed = urlparse(url)
    if parsed.netloc.casefold() not in ALLOWED_ACCOUNT_HOSTS:
        return None
    match = WEBAPPS_PATH.fullmatch(parsed.path)
    return match.group(1) if match else None


def is_renewal_label(label: str) -> bool:
    """Return whether a control label is an allowed renewal action."""
    normalized = label.strip()
    return bool(
        RENEW_LABEL.search(normalized)
        and not DESTRUCTIVE_LABEL.search(normalized)
    )


def is_reload_label(label: str) -> bool:
    """Return whether a control label is an allowed reload action."""
    normalized = label.strip()
    return bool(
        RELOAD_LABEL.search(normalized)
        and not DESTRUCTIVE_LABEL.search(normalized)
    )


def _control_label(control: Any) -> str:
    for attribute in ("value", "aria-label", "title"):
        value = control.get_attribute(attribute)
        if value and value.strip():
            return value.strip()
    return control.inner_text().strip()


def _visible_controls(page: Any, predicate: Any) -> list[tuple[Any, str]]:
    matches: list[tuple[Any, str]] = []
    for control in page.locator(CONTROL_SELECTOR).all():
        if not control.is_visible() or not control.is_enabled():
            continue
        label = _control_label(control)
        if predicate(label):
            matches.append((control, label))
    return matches


def _click_controls(
    page: Any,
    controls: list[tuple[Any, str]],
    *,
    dry_run: bool,
    confirmation_text: str | None = None,
) -> int:
    if dry_run:
        return 0
    clicked = 0
    for control, _label in controls:
        control.click()
        clicked += 1
        page.wait_for_load_state("domcontentloaded")
        if confirmation_text:
            try:
                page.get_by_text(
                    confirmation_text,
                    exact=False,
                ).wait_for(state="visible", timeout=20_000)
            except Exception as exc:
                raise RenewalError(
                    f"The {confirmation_text!r} confirmation did not appear."
                ) from exc
        else:
            page.wait_for_timeout(500)
    return clicked


def renew_visible_webapps(
    page: Any,
    *,
    dry_run: bool = False,
    reload_after: bool = True,
) -> tuple[int, int, int, int]:
    """Renew and reload only explicitly matched controls on the current page."""
    renewals = _visible_controls(page, is_renewal_label)
    renewed = _click_controls(page, renewals, dry_run=dry_run)

    reloads: list[tuple[Any, str]] = []
    reloaded = 0
    if reload_after:
        reloads = _visible_controls(page, is_reload_label)
        reloaded = _click_controls(
            page,
            reloads,
            dry_run=dry_run,
            confirmation_text="Reload successful",
        )
    return len(renewals), renewed, len(reloads), reloaded


def _all_hrefs(page: Any) -> list[str]:
    return page.locator("a[href]").evaluate_all(
        "elements => elements.map(element => element.getAttribute('href'))"
    )


def _find_account_navigation(
    page: Any,
    origin: str,
) -> tuple[str, str]:
    """Discover the current account and its Web-tab URL from visible links."""
    for href in _all_hrefs(page):
        if not href:
            continue
        absolute = urljoin(origin, href)
        account = account_from_webapps_url(absolute)
        if account:
            return account, absolute

    for href in _all_hrefs(page):
        if not href:
            continue
        parsed = urlparse(urljoin(origin, href))
        match = DASHBOARD_PATH.fullmatch(parsed.path)
        if match:
            account = match.group(1)
            return (
                account,
                f"{origin}/user/{account}/webapps/",
            )
    raise RenewalError(
        "No signed-in PythonAnywhere account was found. Sign in in the "
        "connected Chrome window, then run the script again."
    )


def open_webapps_dashboard(
    page: Any,
    *,
    origin: str = PYTHONANYWHERE_ORIGIN,
) -> tuple[str, str]:
    """Open the Web tab for whichever account is signed in to Chrome."""
    normalized_origin = origin.rstrip("/")
    if urlparse(normalized_origin).netloc.casefold() not in ALLOWED_ACCOUNT_HOSTS:
        raise RenewalError("Only official PythonAnywhere account sites are allowed.")
    page.goto(normalized_origin, wait_until="domcontentloaded")
    title = page.title().casefold()
    if "access denied" in title or "/login" in page.url.casefold():
        raise RenewalError(
            "Chrome is not signed in to PythonAnywhere. Sign in and retry."
        )
    account, dashboard_url = _find_account_navigation(page, normalized_origin)
    page.goto(dashboard_url, wait_until="domcontentloaded")
    if "access denied" in page.title().casefold():
        raise RenewalError(
            "The signed-in account cannot access its PythonAnywhere Web tab."
        )
    return account, dashboard_url


def _choose_page(context: Any) -> Any:
    for page in context.pages:
        hostname = urlparse(page.url).hostname or ""
        if hostname.endswith("pythonanywhere.com"):
            return page
    return context.new_page()


def run(
    *,
    cdp_url: str,
    origin: str,
    dry_run: bool,
    reload_after: bool,
) -> RenewalResult:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RenewalError(
            "Playwright is not installed. Run: "
            "python -m pip install -r requirements-automation.txt"
        ) from exc

    with sync_playwright() as playwright:
        try:
            browser = playwright.chromium.connect_over_cdp(cdp_url)
        except Exception as exc:
            raise RenewalError(
                f"Could not connect to Chrome at {cdp_url}. Start Chrome with "
                "remote debugging enabled and retry."
            ) from exc
        if not browser.contexts:
            raise RenewalError("The connected Chrome instance has no context.")

        page = _choose_page(browser.contexts[0])
        account, dashboard_url = open_webapps_dashboard(page, origin=origin)
        found, renewed, reload_found, reloaded = renew_visible_webapps(
            page,
            dry_run=dry_run,
            reload_after=reload_after,
        )
        return RenewalResult(
            account=account,
            dashboard_url=dashboard_url,
            renewal_controls_found=found,
            renewed=renewed,
            reload_controls_found=reload_found,
            reloaded=reloaded,
            dry_run=dry_run,
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Renew PythonAnywhere web apps using the account already signed "
            "in to a remote-debugging Chrome instance."
        )
    )
    parser.add_argument(
        "--cdp-url",
        default=os.getenv("CHROME_CDP_URL", DEFAULT_CDP_URL),
        help="Chrome DevTools URL (default: %(default)s)",
    )
    parser.add_argument(
        "--origin",
        choices=(
            "https://www.pythonanywhere.com",
            "https://eu.pythonanywhere.com",
        ),
        default=os.getenv("PYTHONANYWHERE_ORIGIN", PYTHONANYWHERE_ORIGIN),
        help="PythonAnywhere account site (default: %(default)s)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Discover controls without clicking them.",
    )
    parser.add_argument(
        "--no-reload",
        action="store_true",
        help="Renew the app without restarting its web workers afterward.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        result = run(
            cdp_url=args.cdp_url,
            origin=args.origin,
            dry_run=args.dry_run,
            reload_after=not args.no_reload,
        )
    except RenewalError as exc:
        print(f"Renewal failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(asdict(result), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
