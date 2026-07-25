import re
from pathlib import Path

from fastapi.testclient import TestClient

from tests.test_contact_api import VALID_CONTACT


def _login(client: TestClient) -> str:
    response = client.post(
        "/admin/login",
        data={
            "username": "test-admin",
            "password": "unit-test-only-password",
        },
        follow_redirects=False,
    )
    assert response.status_code == 303
    dashboard = client.get("/admin")
    assert dashboard.status_code == 200
    match = re.search(
        r'name="csrf_token" value="([^"]+)"',
        dashboard.text,
    )
    assert match is not None
    return match.group(1)


def test_admin_requires_login(client: TestClient) -> None:
    response = client.get("/admin", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/admin/login"


def test_admin_rejects_invalid_credentials(client: TestClient) -> None:
    response = client.post(
        "/admin/login",
        data={"username": "test-admin", "password": "wrong"},
    )

    assert response.status_code == 401
    assert "incorrect" in response.text


def test_admin_login_is_rate_limited(client: TestClient) -> None:
    for _ in range(5):
        response = client.post(
            "/admin/login",
            data={"username": "test-admin", "password": "wrong"},
        )
        assert response.status_code == 401

    blocked = client.post(
        "/admin/login",
        data={"username": "test-admin", "password": "wrong"},
    )

    assert blocked.status_code == 429
    assert "Too many sign-in attempts" in blocked.text


def test_admin_lists_and_manages_contact(client: TestClient) -> None:
    client.post("/api/v1/contact", json=VALID_CONTACT)
    csrf_token = _login(client)

    dashboard = client.get("/admin")
    assert "Jane Smith" in dashboard.text

    detail = client.get("/admin/contacts/1")
    assert detail.status_code == 200
    assert "Example Company" in detail.text
    assert VALID_CONTACT["message"] in detail.text
    assert client.app.state.contact_service.get(1).status.value == "read"

    update = client.post(
        "/admin/contacts/1/status",
        data={"status": "archived", "csrf_token": csrf_token},
        follow_redirects=False,
    )
    assert update.status_code == 303
    assert client.app.state.contact_service.get(1).status.value == "archived"

    deleted = client.post(
        "/admin/contacts/1/delete",
        data={"csrf_token": csrf_token},
        follow_redirects=False,
    )
    assert deleted.status_code == 303
    assert client.app.state.contact_service.counts()["all"] == 0


def test_admin_rejects_invalid_csrf(client: TestClient) -> None:
    client.post("/api/v1/contact", json=VALID_CONTACT)
    _login(client)

    response = client.post(
        "/admin/contacts/1/delete",
        data={"csrf_token": "invalid"},
    )

    assert response.status_code == 403
    assert client.app.state.contact_service.counts()["all"] == 1


def test_admin_uploads_and_deletes_downloadable_file(
    client: TestClient,
    download_directory: Path,
) -> None:
    csrf_token = _login(client)

    uploaded = client.post(
        "/admin/files/upload",
        data={"csrf_token": csrf_token},
        files={"upload": ("proposal.pdf", b"pdf payload", "application/pdf")},
        follow_redirects=False,
    )

    assert uploaded.status_code == 303
    assert (download_directory / "proposal.pdf").read_bytes() == b"pdf payload"
    download = client.get("/api/v1/files/proposal.pdf")
    assert download.status_code == 200
    assert download.content == b"pdf payload"

    duplicate = client.post(
        "/admin/files/upload",
        data={"csrf_token": csrf_token},
        files={"upload": ("proposal.pdf", b"replacement", "application/pdf")},
        follow_redirects=False,
    )
    assert duplicate.status_code == 303
    assert (download_directory / "proposal.pdf").read_bytes() == b"pdf payload"

    deleted = client.post(
        "/admin/files/proposal.pdf/delete",
        data={"csrf_token": csrf_token},
        follow_redirects=False,
    )
    assert deleted.status_code == 303
    assert not (download_directory / "proposal.pdf").exists()


def test_admin_upload_rejects_nested_filename(
    client: TestClient,
    download_directory: Path,
) -> None:
    csrf_token = _login(client)

    response = client.post(
        "/admin/files/upload",
        data={"csrf_token": csrf_token},
        files={"upload": ("../secret.txt", b"secret", "text/plain")},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert not (download_directory / "secret.txt").exists()


def test_admin_upload_rejects_hidden_filename(
    client: TestClient,
    download_directory: Path,
) -> None:
    csrf_token = _login(client)

    response = client.post(
        "/admin/files/upload",
        data={"csrf_token": csrf_token},
        files={"upload": (".env", b"secret", "text/plain")},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert not (download_directory / ".env").exists()


def test_admin_analytics_pages_toggle_and_event_management(
    client: TestClient,
) -> None:
    event = {
        "sessionId": "admin-test-session",
        "eventType": "click",
        "pageUrl": "http://127.0.0.1:3000/#contact",
        "pageTitle": "CurvatureTech",
        "section": "contact",
        "elementTag": "button",
        "elementId": "contact-submit",
        "elementLabel": "Start the conversation",
        "pointerX": 52.5,
        "pointerY": 81.0,
        "metadata": {"variant": "primary"},
    }
    recorded = client.post("/api/v1/analytics/events", json=event)
    assert recorded.status_code == 202
    csrf_token = _login(client)

    listing = client.get("/admin/analytics")
    assert listing.status_code == 200
    assert "Recorded actions" in listing.text
    assert "Start the conversation" in listing.text

    detail = client.get("/admin/analytics/events/1")
    assert detail.status_code == 200
    assert "contact-submit" in detail.text
    assert "primary" in detail.text

    paused = client.post(
        "/admin/analytics/settings",
        data={"csrf_token": csrf_token},
        follow_redirects=False,
    )
    assert paused.status_code == 303
    assert client.app.state.analytics_service.recording_enabled is False

    ignored = client.post("/api/v1/analytics/events", json=event)
    assert ignored.status_code == 202
    assert ignored.json()["recorded"] is False
    assert client.app.state.analytics_service.summary()["total"] == 1

    resumed = client.post(
        "/admin/analytics/settings",
        data={"csrf_token": csrf_token, "enabled": "on"},
        follow_redirects=False,
    )
    assert resumed.status_code == 303
    assert client.app.state.analytics_service.recording_enabled is True

    deleted = client.post(
        "/admin/analytics/events/1/delete",
        data={"csrf_token": csrf_token},
        follow_redirects=False,
    )
    assert deleted.status_code == 303
    assert client.app.state.analytics_service.summary()["total"] == 0
    assert client.get("/admin/analytics/events/1").status_code == 404
