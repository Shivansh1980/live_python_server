from pathlib import Path

import pytest

from scripts.renew_pythonanywhere import (
    _find_account_navigation,
    account_from_webapps_url,
    is_reload_label,
    is_renewal_label,
    renew_visible_webapps,
)


def test_account_is_derived_only_from_pythonanywhere_webapps_url() -> None:
    assert (
        account_from_webapps_url(
            "https://www.pythonanywhere.com/user/Ada/webapps/"
        )
        == "Ada"
    )
    assert (
        account_from_webapps_url(
            "https://eu.pythonanywhere.com/user/Grace/webapps/"
        )
        == "Grace"
    )
    assert account_from_webapps_url("https://example.com/user/Ada/webapps/") is None
    assert account_from_webapps_url("https://www.pythonanywhere.com/user/Ada/") is None


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Run until 1 month from today", True),
        ("Extend web app", True),
        ("Renew", True),
        ("Reload ryzenshivansh.pythonanywhere.com", False),
        ("Disable web app", False),
        ("Delete web app", False),
        ("Renew SSL certificate", False),
        ("Extend certificate", False),
    ],
)
def test_renewal_label_allowlist(label: str, expected: bool) -> None:
    assert is_renewal_label(label) is expected


@pytest.mark.parametrize(
    ("label", "expected"),
    [
        ("Reload", True),
        ("Reload web app", True),
        ("Reload example.pythonanywhere.com", True),
        ("\ue031 Reload", True),
        ("Run until 1 month from today", False),
        ("Disable", False),
        ("Delete", False),
        ("Reload and delete web app", False),
    ],
)
def test_reload_label_allowlist(label: str, expected: bool) -> None:
    assert is_reload_label(label) is expected


def test_playwright_clicks_only_renew_and_reload_controls() -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    chrome = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")
    if not chrome.exists():
        pytest.skip("Google Chrome is unavailable for the browser test.")

    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(
            executable_path=str(chrome),
            headless=True,
        )
        page = browser.new_page()
        page.set_content(
            """
            <button id="renew" onclick="this.dataset.clicked='yes'">
              Run until 1 month from today
            </button>
            <button id="reload" onclick="
              this.dataset.clicked='yes';
              document.querySelector('#reload-status').hidden=false;
            ">
              Reload example.pythonanywhere.com
            </button>
            <span id="reload-status" hidden>Reload successful</span>
            <button id="disable" onclick="this.dataset.clicked='yes'">
              Disable web app
            </button>
            <button id="delete" onclick="this.dataset.clicked='yes'">
              Delete web app
            </button>
            """
        )

        result = renew_visible_webapps(page)

        assert result == (1, 1, 1, 1)
        assert page.locator("#renew").get_attribute("data-clicked") == "yes"
        assert page.locator("#reload").get_attribute("data-clicked") == "yes"
        assert page.locator("#disable").get_attribute("data-clicked") is None
        assert page.locator("#delete").get_attribute("data-clicked") is None
        browser.close()


def test_playwright_discovers_signed_in_account_from_navigation() -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    chrome = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")
    if not chrome.exists():
        pytest.skip("Google Chrome is unavailable for the browser test.")

    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(
            executable_path=str(chrome),
            headless=True,
        )
        page = browser.new_page()
        page.set_content(
            """
            <nav>
              <a href="/user/CaptainShivansh/">Dashboard</a>
              <a href="/user/CaptainShivansh/webapps/">Web</a>
            </nav>
            """
        )

        account, dashboard_url = _find_account_navigation(
            page,
            "https://www.pythonanywhere.com",
        )

        assert account == "CaptainShivansh"
        assert dashboard_url == (
            "https://www.pythonanywhere.com/"
            "user/CaptainShivansh/webapps/"
        )
        browser.close()


def test_playwright_dry_run_does_not_click_any_control() -> None:
    playwright = pytest.importorskip("playwright.sync_api")
    chrome = Path("C:/Program Files/Google/Chrome/Application/chrome.exe")
    if not chrome.exists():
        pytest.skip("Google Chrome is unavailable for the browser test.")

    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(
            executable_path=str(chrome),
            headless=True,
        )
        page = browser.new_page()
        page.set_content(
            """
            <button id="renew" onclick="this.dataset.clicked='yes'">
              Extend web app
            </button>
            <button id="reload" onclick="
              this.dataset.clicked='yes';
              document.querySelector('#reload-status').hidden=false;
            ">
              Reload web app
            </button>
            <span id="reload-status" hidden>Reload successful</span>
            """
        )

        result = renew_visible_webapps(page, dry_run=True)

        assert result == (1, 0, 1, 0)
        assert page.locator("#renew").get_attribute("data-clicked") is None
        assert page.locator("#reload").get_attribute("data-clicked") is None
        browser.close()
