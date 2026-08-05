from fastapi.testclient import TestClient

VALID_EVENT = {
    "sessionId": "session-12345678",
    "eventType": "section_view",
    "pageUrl": "http://localhost:3000/services?campaign=private#details",
    "pageTitle": "Services",
    "section": "ai-integration",
    "elementTag": "section",
    "elementId": "ai-integration",
    "elementLabel": "AI integration",
    "durationMs": 12800,
    "scrollDepth": 72.5,
    "pointerX": 44.2,
    "pointerY": 61.8,
    "viewportWidth": 1440,
    "viewportHeight": 900,
    "metadata": {"source": "navigation", "visible": True},
}


def test_analytics_event_records_detailed_anonymous_data(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/analytics/events",
        json=VALID_EVENT,
        headers={"user-agent": "BuildMind-Labs-Test-Browser/1.0"},
    )

    assert response.status_code == 202
    assert response.json() == {
        "recorded": True,
        "event_id": 1,
        "reason": "recorded",
    }
    stored = client.app.state.analytics_service.get(1)
    assert stored.page_url == "http://localhost:3000/services"
    assert stored.section == "ai-integration"
    assert stored.duration_ms == 12800
    assert stored.scroll_depth == 72.5
    assert stored.user_agent == "BuildMind-Labs-Test-Browser/1.0"
    assert stored.metadata_json == '{"source":"navigation","visible":true}'


def test_analytics_rejects_sensitive_metadata(client: TestClient) -> None:
    response = client.post(
        "/api/v1/analytics/events",
        json={
            **VALID_EVENT,
            "metadata": {"password": "must-not-be-collected"},
        },
    )

    assert response.status_code == 422
    assert client.app.state.analytics_service.summary()["total"] == 0


def test_analytics_rejects_identifying_session_ids(
    client: TestClient,
) -> None:
    response = client.post(
        "/api/v1/analytics/events",
        json={**VALID_EVENT, "sessionId": "person@example.com"},
    )

    assert response.status_code == 422
    assert client.app.state.analytics_service.summary()["total"] == 0


def test_analytics_toggle_prevents_database_writes(
    client: TestClient,
) -> None:
    client.app.state.analytics_service.set_recording_enabled(False)

    response = client.post("/api/v1/analytics/events", json=VALID_EVENT)

    assert response.status_code == 202
    assert response.json() == {
        "recorded": False,
        "event_id": None,
        "reason": "recording_disabled",
    }
    assert client.app.state.analytics_service.summary()["total"] == 0


def test_analytics_cors_allows_both_local_origins(
    client: TestClient,
) -> None:
    for origin in (
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ):
        response = client.options(
            "/api/v1/analytics/events",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin
