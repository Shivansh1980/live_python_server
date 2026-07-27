from fastapi.testclient import TestClient

from app.schemas.payload_config import PayloadConfigInput


def _create_payload_config(
    client: TestClient,
    *,
    user_ip_address: str,
    user_host_name: str,
    should_replace_payload: bool = False,
    is_active: bool = True,
    url: str = "https://example.com/payload",
):
    return client.app.state.payload_config_service.create(
        PayloadConfigInput(
            should_replace_payload=should_replace_payload,
            url=url,
            remote_host="edge.example.com",
            remote_port=443,
            user_ip_address=user_ip_address,
            user_host_name=user_host_name,
            is_active=is_active,
        )
    )


def test_get_returns_newest_active_row_for_ip(client: TestClient) -> None:
    first = _create_payload_config(
        client,
        user_ip_address="203.0.113.10",
        user_host_name="first-host",
        url="https://example.com/first",
    )
    latest = _create_payload_config(
        client,
        user_ip_address="203.0.113.10",
        user_host_name="latest-host",
        url="https://example.com/latest",
    )
    _create_payload_config(
        client,
        user_ip_address="203.0.113.10",
        user_host_name="inactive-host",
        is_active=False,
        url="https://example.com/inactive",
    )

    response = client.get(
        "/api/v1/payloadconfig/",
        params={"user_ip_address": "203.0.113.10"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == latest.id
    assert response.json()["url"] == "https://example.com/latest"
    assert response.json()["id"] != first.id
    assert response.json()["is_active"] is True


def test_post_updates_only_newest_active_row_for_ip(
    client: TestClient,
) -> None:
    first = _create_payload_config(
        client,
        user_ip_address="203.0.113.20",
        user_host_name="shared-host",
    )
    latest = _create_payload_config(
        client,
        user_ip_address="203.0.113.20",
        user_host_name="latest-host",
    )
    other = _create_payload_config(
        client,
        user_ip_address="203.0.113.21",
        user_host_name="other-host",
    )

    response = client.post(
        "/api/v1/payloadconfig/",
        json={
            "user_ip_address": "203.0.113.20",
            "should_replace_payload": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["scope"] == "user_ip_address"
    assert response.json()["updated_rows"] == 1
    assert response.json()["payload_config"]["id"] == latest.id
    assert response.json()["should_replace_payload"] is True
    service = client.app.state.payload_config_service
    assert service.get(first.id).should_replace_payload is False
    assert service.get(latest.id).should_replace_payload is True
    assert service.get(other.id).should_replace_payload is False


def test_post_falls_back_to_hostname_and_defaults_to_false(
    client: TestClient,
) -> None:
    _create_payload_config(
        client,
        user_ip_address="203.0.113.30",
        user_host_name="WorkStation-30",
        should_replace_payload=True,
    )
    latest = _create_payload_config(
        client,
        user_ip_address="203.0.113.31",
        user_host_name="workstation-30",
        should_replace_payload=True,
    )

    response = client.post(
        "/api/v1/payloadconfig/",
        json={"user_host_name": "WORKSTATION-30"},
    )

    assert response.status_code == 200
    assert response.json()["scope"] == "user_host_name"
    assert response.json()["should_replace_payload"] is False
    assert response.json()["payload_config"]["id"] == latest.id


def test_post_prefers_ip_when_both_identifiers_are_supplied(
    client: TestClient,
) -> None:
    by_ip = _create_payload_config(
        client,
        user_ip_address="203.0.113.40",
        user_host_name="ip-target",
    )
    by_hostname = _create_payload_config(
        client,
        user_ip_address="203.0.113.41",
        user_host_name="hostname-target",
    )

    response = client.post(
        "/api/v1/payloadconfig/",
        json={
            "user_ip_address": "203.0.113.40",
            "user_host_name": "hostname-target",
            "should_replace_payload": True,
        },
    )

    assert response.status_code == 200
    assert response.json()["payload_config"]["id"] == by_ip.id
    service = client.app.state.payload_config_service
    assert service.get(by_ip.id).should_replace_payload is True
    assert service.get(by_hostname.id).should_replace_payload is False


def test_post_without_identifiers_updates_every_row(
    client: TestClient,
) -> None:
    active = _create_payload_config(
        client,
        user_ip_address="203.0.113.50",
        user_host_name="active-host",
    )
    inactive = _create_payload_config(
        client,
        user_ip_address="203.0.113.51",
        user_host_name="inactive-host",
        is_active=False,
    )

    enabled = client.post(
        "/api/v1/payloadconfig/",
        json={"should_replace_payload": True},
    )

    assert enabled.status_code == 200
    assert enabled.json() == {
        "should_replace_payload": True,
        "scope": "all",
        "updated_rows": 2,
        "payload_config": None,
    }
    service = client.app.state.payload_config_service
    assert service.get(active.id).should_replace_payload is True
    assert service.get(inactive.id).should_replace_payload is True

    disabled = client.post("/api/v1/payloadconfig/")
    assert disabled.status_code == 200
    assert disabled.json()["should_replace_payload"] is False
    assert disabled.json()["updated_rows"] == 2
    assert service.get(active.id).should_replace_payload is False
    assert service.get(inactive.id).should_replace_payload is False


def test_payload_config_reports_invalid_or_missing_targets(
    client: TestClient,
) -> None:
    invalid_get = client.get(
        "/api/v1/payloadconfig/",
        params={"user_ip_address": "not-an-ip"},
    )
    invalid_post = client.post(
        "/api/v1/payloadconfig/",
        json={"user_ip_address": "not-an-ip"},
    )
    missing_get = client.get(
        "/api/v1/payloadconfig/",
        params={"user_ip_address": "203.0.113.99"},
    )
    missing_post = client.post(
        "/api/v1/payloadconfig/",
        json={"user_host_name": "missing-host"},
    )

    assert invalid_get.status_code == 422
    assert invalid_post.status_code == 422
    assert missing_get.status_code == 404
    assert missing_post.status_code == 404


def test_post_rejects_removed_status_field_without_updating_rows(
    client: TestClient,
) -> None:
    stored = _create_payload_config(
        client,
        user_ip_address="203.0.113.80",
        user_host_name="no-legacy-status",
        should_replace_payload=True,
    )

    response = client.post(
        "/api/v1/payloadconfig/",
        json={"status": False},
    )

    assert response.status_code == 422
    assert (
        client.app.state.payload_config_service.get(
            stored.id
        ).should_replace_payload
        is True
    )
