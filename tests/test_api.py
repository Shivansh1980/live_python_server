from pathlib import Path

from fastapi.testclient import TestClient


def test_root_describes_service(client: TestClient) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json()["files"] == "/api/v1/files"


def test_health_check(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_file_list_reflects_new_files_without_code_changes(
    client: TestClient,
    download_directory: Path,
) -> None:
    first_response = client.get("/api/v1/files")
    assert first_response.json() == {"count": 0, "files": []}

    new_file = download_directory / "new report.txt"
    new_file.write_text("dynamic content", encoding="utf-8")

    second_response = client.get("/api/v1/files")
    body = second_response.json()
    assert second_response.status_code == 200
    assert body["count"] == 1
    assert body["files"][0]["name"] == "new report.txt"
    assert body["files"][0]["size_bytes"] == len(b"dynamic content")
    assert body["files"][0]["download_url"].endswith(
        "/api/v1/files/new%20report.txt"
    )


def test_download_returns_exact_file(
    client: TestClient,
    download_directory: Path,
) -> None:
    payload = b"\x00download payload\xff"
    (download_directory / "sample.bin").write_bytes(payload)

    response = client.get("/api/v1/files/sample.bin")

    assert response.status_code == 200
    assert response.content == payload
    assert "sample.bin" in response.headers["content-disposition"]


def test_missing_file_returns_404(client: TestClient) -> None:
    response = client.get("/api/v1/files/missing.pdf")

    assert response.status_code == 404


def test_server_source_files_are_not_exposed(client: TestClient) -> None:
    response = client.get("/api/v1/files/requirements.txt")

    assert response.status_code == 404


def test_nested_files_are_not_listed_or_downloadable(
    client: TestClient,
    download_directory: Path,
) -> None:
    nested_directory = download_directory / "private"
    nested_directory.mkdir()
    (nested_directory / "secret.txt").write_text("secret", encoding="utf-8")

    list_response = client.get("/api/v1/files")
    download_response = client.get("/api/v1/files/private%2Fsecret.txt")

    assert list_response.json() == {"count": 0, "files": []}
    assert download_response.status_code in {400, 404}


def test_windows_style_traversal_is_rejected(client: TestClient) -> None:
    response = client.get("/api/v1/files/..%5Crequirements.txt")

    assert response.status_code == 400
