from fastapi.testclient import TestClient

VALID_CONTACT = {
    "name": "Jane Smith",
    "email": "jane@company.com",
    "company": "Example Company",
    "projectType": "Web app or SaaS product",
    "budget": "$8k–$20k",
    "message": "We need a client portal that replaces a manual spreadsheet workflow.",
}


def test_contact_submission_matches_frontend_payload(client: TestClient) -> None:
    response = client.post("/api/v1/contact", json=VALID_CONTACT)

    assert response.status_code == 201
    assert response.json()["id"] == 1
    assert response.json()["status"] == "received"

    stored = client.app.state.contact_service.get(1)
    assert stored.name == "Jane Smith"
    assert stored.project_type == "Web app or SaaS product"
    assert stored.notification_status == '{"notifications": "not_configured"}'


def test_contact_validation_rejects_bad_email_and_short_message(
    client: TestClient,
) -> None:
    payload = {**VALID_CONTACT, "email": "not-an-email", "message": "short"}

    response = client.post("/api/v1/contact", json=payload)

    assert response.status_code == 422


def test_contact_honeypot_accepts_without_storing(client: TestClient) -> None:
    payload = {**VALID_CONTACT, "website": "https://spam.example"}

    response = client.post("/api/v1/contact", json=payload)

    assert response.status_code == 201
    assert response.json()["id"] == 0
    assert client.app.state.contact_service.counts()["all"] == 0


def test_contact_endpoint_is_rate_limited(client: TestClient) -> None:
    for index in range(5):
        response = client.post(
            "/api/v1/contact",
            json={**VALID_CONTACT, "email": f"jane{index}@company.com"},
            headers={"x-forwarded-for": "203.0.113.44"},
        )
        assert response.status_code == 201

    blocked = client.post(
        "/api/v1/contact",
        json=VALID_CONTACT,
        headers={"x-forwarded-for": "203.0.113.44"},
    )
    assert blocked.status_code == 429


def test_contact_cors_preflight_allows_configured_frontend(
    client: TestClient,
) -> None:
    for origin in (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ):
        response = client.options(
            "/api/v1/contact",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin


def test_contact_cors_rejects_unknown_origin(client: TestClient) -> None:
    response = client.options(
        "/api/v1/contact",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "POST",
        },
    )

    assert "access-control-allow-origin" not in response.headers
