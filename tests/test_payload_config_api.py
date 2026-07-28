import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient

from app.domain.payload_config import NewPayloadConfig
from app.repositories.sqlite_payload_config_repository import (
    SQLitePayloadConfigRepository,
)
from app.schemas.payload_config import PayloadConfigInput


def _create_payload_config(
    client: TestClient,
    *,
    user_ip_address: str,
    user_host_name: str,
    should_replace_payload: bool = False,
    is_active: bool = True,
):
    return client.app.state.payload_config_service.create(
        PayloadConfigInput(
            should_replace_payload=should_replace_payload,
            remote_host="edge.example.com",
            remote_port=443,
            user_ip_address=user_ip_address,
            user_host_name=user_host_name,
            is_active=is_active,
        )
    )


def test_post_creates_record_with_nullable_defaults(
    client: TestClient,
) -> None:
    response = client.post("/api/v1/payloadconfig/", json={})

    assert response.status_code == 201
    assert response.json() == {
        "id": response.json()["id"],
        "should_replace_payload": False,
        "remote_host": None,
        "remote_port": None,
        "user_ip_address": None,
        "user_host_name": None,
        "is_active": True,
        "created_at": response.json()["created_at"],
        "updated_at": response.json()["updated_at"],
    }


def test_post_normalizes_blank_optional_strings_to_null(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/payloadconfig/",
        json={
            "remote_host": " ",
            "user_ip_address": "",
            "user_host_name": "   ",
        },
    )

    assert response.status_code == 201
    assert response.json()["remote_host"] is None
    assert response.json()["user_ip_address"] is None
    assert response.json()["user_host_name"] is None


def test_id_crud_supports_read_partial_update_clear_and_delete(
    client: TestClient,
) -> None:
    created = client.post(
        "/api/v1/payloadconfig/",
        json={
            "remote_host": "edge.example.com",
            "remote_port": 443,
            "user_ip_address": "2001:0db8::1",
            "user_host_name": "workstation-01",
        },
    )
    assert created.status_code == 201
    payload_config_id = created.json()["id"]
    assert created.json()["user_ip_address"] == "2001:db8::1"

    fetched = client.get(f"/api/v1/payloadconfig/{payload_config_id}")
    assert fetched.status_code == 200
    assert fetched.json() == created.json()

    patched = client.patch(
        f"/api/v1/payloadconfig/{payload_config_id}",
        json={"should_replace_payload": True, "remote_port": 8443},
    )
    assert patched.status_code == 200
    assert patched.json()["should_replace_payload"] is True
    assert patched.json()["remote_port"] == 8443
    assert patched.json()["remote_host"] == "edge.example.com"

    cleared = client.patch(
        f"/api/v1/payloadconfig/{payload_config_id}",
        json={
            "remote_host": None,
            "remote_port": None,
            "user_ip_address": "",
            "user_host_name": None,
        },
    )
    assert cleared.status_code == 200
    assert cleared.json()["remote_host"] is None
    assert cleared.json()["remote_port"] is None
    assert cleared.json()["user_ip_address"] is None
    assert cleared.json()["user_host_name"] is None

    deleted = client.delete(f"/api/v1/payloadconfig/{payload_config_id}")
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert (
        client.get(f"/api/v1/payloadconfig/{payload_config_id}").status_code
        == 404
    )


def test_put_replaces_complete_record(client: TestClient) -> None:
    created = client.post(
        "/api/v1/payloadconfig/",
        json={
            "remote_host": "old.example.com",
            "remote_port": 443,
            "user_ip_address": "203.0.113.12",
            "user_host_name": "old-host",
            "should_replace_payload": True,
        },
    )
    payload_config_id = created.json()["id"]

    replaced = client.put(
        f"/api/v1/payloadconfig/{payload_config_id}",
        json={
            "remote_host": "new.example.com",
            "remote_port": 9443,
        },
    )

    assert replaced.status_code == 200
    assert replaced.json()["remote_host"] == "new.example.com"
    assert replaced.json()["remote_port"] == 9443
    assert replaced.json()["should_replace_payload"] is False
    assert replaced.json()["user_ip_address"] is None
    assert replaced.json()["user_host_name"] is None
    assert replaced.json()["is_active"] is True


def test_id_patch_validates_partial_update_payload(
    client: TestClient,
) -> None:
    created = client.post("/api/v1/payloadconfig/", json={})
    payload_config_id = created.json()["id"]

    empty = client.patch(
        f"/api/v1/payloadconfig/{payload_config_id}",
        json={},
    )
    null_boolean = client.patch(
        f"/api/v1/payloadconfig/{payload_config_id}",
        json={"is_active": None},
    )
    invalid_port = client.patch(
        f"/api/v1/payloadconfig/{payload_config_id}",
        json={"remote_port": 70000},
    )
    invalid_ip = client.patch(
        f"/api/v1/payloadconfig/{payload_config_id}",
        json={"user_ip_address": "not-an-ip"},
    )

    assert empty.status_code == 422
    assert null_boolean.status_code == 422
    assert invalid_port.status_code == 422
    assert invalid_ip.status_code == 422


def test_id_crud_returns_not_found_for_unknown_record(
    client: TestClient,
) -> None:
    assert client.get("/api/v1/payloadconfig/999999").status_code == 404
    assert (
        client.patch(
            "/api/v1/payloadconfig/999999",
            json={"is_active": False},
        ).status_code
        == 404
    )
    assert (
        client.put(
            "/api/v1/payloadconfig/999999",
            json={},
        ).status_code
        == 404
    )
    assert client.delete("/api/v1/payloadconfig/999999").status_code == 404


def test_get_returns_newest_active_row_for_ip(client: TestClient) -> None:
    first = _create_payload_config(
        client,
        user_ip_address="203.0.113.10",
        user_host_name="first-host",
    )
    latest = _create_payload_config(
        client,
        user_ip_address="203.0.113.10",
        user_host_name="latest-host",
    )
    _create_payload_config(
        client,
        user_ip_address="203.0.113.10",
        user_host_name="inactive-host",
        is_active=False,
    )

    response = client.get(
        "/api/v1/payloadconfig/",
        params={"user_ip_address": "203.0.113.10"},
    )

    assert response.status_code == 200
    assert response.json()["id"] == latest.id
    assert "url" not in response.json()
    assert response.json()["id"] != first.id
    assert response.json()["is_active"] is True


def test_selector_patch_updates_only_newest_active_row_for_ip(
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

    response = client.patch(
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


def test_selector_patch_falls_back_to_hostname_and_defaults_to_false(
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

    response = client.patch(
        "/api/v1/payloadconfig/",
        json={"user_host_name": "WORKSTATION-30"},
    )

    assert response.status_code == 200
    assert response.json()["scope"] == "user_host_name"
    assert response.json()["should_replace_payload"] is False
    assert response.json()["payload_config"]["id"] == latest.id


def test_selector_patch_prefers_ip_when_both_identifiers_are_supplied(
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

    response = client.patch(
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


def test_selector_patch_without_identifiers_updates_every_row(
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

    enabled = client.patch(
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

    disabled = client.patch("/api/v1/payloadconfig/")
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
    invalid_patch = client.patch(
        "/api/v1/payloadconfig/",
        json={"user_ip_address": "not-an-ip"},
    )
    missing_get = client.get(
        "/api/v1/payloadconfig/",
        params={"user_ip_address": "203.0.113.99"},
    )
    missing_patch = client.patch(
        "/api/v1/payloadconfig/",
        json={"user_host_name": "missing-host"},
    )

    assert invalid_get.status_code == 422
    assert invalid_patch.status_code == 422
    assert missing_get.status_code == 404
    assert missing_patch.status_code == 404


def test_selector_patch_rejects_removed_status_field_without_updating_rows(
    client: TestClient,
) -> None:
    stored = _create_payload_config(
        client,
        user_ip_address="203.0.113.80",
        user_host_name="no-legacy-status",
        should_replace_payload=True,
    )

    response = client.patch(
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


def test_repository_migrates_legacy_url_column_without_data_loss(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "legacy.db"
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE payload_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                should_replace_payload INTEGER NOT NULL,
                url TEXT NOT NULL,
                remote_host TEXT NOT NULL,
                remote_port INTEGER NOT NULL,
                user_ip_address TEXT NOT NULL,
                user_host_name TEXT NOT NULL,
                is_active INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX idx_payload_configs_ip_active_latest
                ON payload_configs(
                    user_ip_address, is_active, created_at DESC, id DESC
                );
            CREATE INDEX idx_payload_configs_updated_at
                ON payload_configs(updated_at DESC);
            INSERT INTO payload_configs (
                should_replace_payload, url, remote_host, remote_port,
                user_ip_address, user_host_name, is_active, created_at,
                updated_at
            ) VALUES (
                1, 'https://obsolete.example/payload', 'edge.example.com',
                8443, '203.0.113.90', 'legacy-host', 1,
                '2026-07-28T10:00:00+00:00',
                '2026-07-28T10:05:00+00:00'
            );
            """
        )

    repository = SQLitePayloadConfigRepository(database_path)
    migrated = repository.get(1)

    assert migrated is not None
    assert migrated.should_replace_payload is True
    assert migrated.remote_host == "edge.example.com"
    assert migrated.remote_port == 8443
    assert migrated.user_ip_address == "203.0.113.90"
    assert migrated.user_host_name == "legacy-host"
    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1]
            for row in connection.execute(
                "PRAGMA table_info(payload_configs)"
            ).fetchall()
        }
        integrity = connection.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]
    assert "url" not in columns
    assert integrity == "ok"


def test_repository_migrates_required_fields_to_nullable_without_data_loss(
    tmp_path: Path,
) -> None:
    database_path = tmp_path / "required-fields.db"
    with sqlite3.connect(database_path) as connection:
        connection.executescript(
            """
            CREATE TABLE payload_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                should_replace_payload INTEGER NOT NULL DEFAULT 0,
                remote_host TEXT NOT NULL,
                remote_port INTEGER NOT NULL,
                user_ip_address TEXT NOT NULL,
                user_host_name TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            INSERT INTO payload_configs (
                remote_host, remote_port, user_ip_address, user_host_name,
                created_at, updated_at
            ) VALUES (
                'edge.example.com', 443, '203.0.113.91', 'existing-host',
                '2026-07-28T10:00:00+00:00',
                '2026-07-28T10:05:00+00:00'
            );
            """
        )

    repository = SQLitePayloadConfigRepository(database_path)
    migrated = repository.get(1)
    created = repository.create(
        NewPayloadConfig(
            should_replace_payload=False,
            remote_host=None,
            remote_port=None,
            user_ip_address=None,
            user_host_name=None,
            is_active=True,
        )
    )

    assert migrated is not None
    assert migrated.remote_host == "edge.example.com"
    assert created.remote_host is None
    assert created.remote_port is None
    with sqlite3.connect(database_path) as connection:
        columns = {
            row[1]: row
            for row in connection.execute(
                "PRAGMA table_info(payload_configs)"
            ).fetchall()
        }
    for name in (
        "remote_host",
        "remote_port",
        "user_ip_address",
        "user_host_name",
    ):
        assert columns[name][3] == 0
