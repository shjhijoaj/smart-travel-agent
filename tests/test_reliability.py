import httpx
import pytest
from fastapi.testclient import TestClient
from api.main import app


@pytest.fixture
def payload():
    return dict(departure="上海", destination="杭州", travel_dates="2026-10-03/2026-10-05",
                budget="5000", companions="2", preferences="少走路", language="中文")


@pytest.fixture(autouse=True)
def isolate(monkeypatch):
    monkeypatch.setenv("DIFY_API_KEY", "test-key")
    monkeypatch.setenv("DIFY_BASE_URL", "http://dify.test")
    monkeypatch.setenv("DIFY_APP_MODE", "advanced-chat")
    monkeypatch.setenv("DIFY_TIMEOUT", "120")


@pytest.mark.parametrize("field,value", [
    ("budget", "NaN"), ("budget", "inf"), ("budget", "-1"),
    ("destination", "   "), ("companions", "0"), ("companions", "1.5"),
    ("travel_dates", "2026-02-30/2026-03-01"), ("travel_dates", "明天"),
    ("travel_dates", "2026-01-01/2026-03-01"),
])
def test_invalid_input_never_calls_dify(monkeypatch, payload, field, value):
    def unexpected(**kwargs):
        pytest.fail("invalid input reached upstream")
    monkeypatch.setattr("api.main.httpx.AsyncClient", unexpected)
    payload[field] = value
    assert TestClient(app).post("/api/travel/plan", json=payload).status_code == 422


@pytest.mark.parametrize("mode,body,status", [
    ("advanced-chat", {"answer": " "}, 200),
    ("advanced-chat", [], 200),
    ("advanced-chat", {"error": "private diagnostic"}, 401),
    ("workflow", {"data": {"status": "failed", "outputs": {"plan": "partial"}}}, 200),
    ("workflow", {"data": {"status": "succeeded", "outputs": {}}}, 200),
])
def test_upstream_failures(monkeypatch, payload, mode, body, status):
    original = httpx.AsyncClient
    transport = httpx.MockTransport(lambda request: httpx.Response(status, json=body))
    monkeypatch.setenv("DIFY_APP_MODE", mode)
    monkeypatch.setattr("api.main.httpx.AsyncClient", lambda **kwargs: original(transport=transport, **kwargs))
    response = TestClient(app).post("/api/travel/plan", json=payload)
    assert response.status_code == 502
    assert "private diagnostic" not in response.text


@pytest.mark.parametrize("failure,expected", [("timeout", 504), ("network", 502), ("json", 502)])
def test_transport_errors(monkeypatch, payload, failure, expected):
    original = httpx.AsyncClient
    def handler(request):
        if failure == "timeout":
            raise httpx.ReadTimeout("private", request=request)
        if failure == "network":
            raise httpx.ConnectError("private", request=request)
        return httpx.Response(200, text="not json")
    monkeypatch.setattr("api.main.httpx.AsyncClient", lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    response = TestClient(app).post("/api/travel/plan", json=payload)
    assert response.status_code == expected
    assert "private" not in response.text


def test_single_day_demo(monkeypatch, payload):
    monkeypatch.delenv("DIFY_API_KEY")
    monkeypatch.setenv("LOCAL_FALLBACK", "true")
    payload["travel_dates"] = "2026-10-03/2026-10-03"
    response = TestClient(app).post("/api/travel/plan", json=payload)
    assert response.status_code == 200
    assert "第1天" in response.json()["plan"]
    assert "第2天" not in response.json()["plan"]
