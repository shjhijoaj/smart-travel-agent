from fastapi.testclient import TestClient

from api.main import app


class FakeDifyResponse:
    def raise_for_status(self):
        return None

    def json(self):
        return {
            "workflow_run_id": "run-test-001",
            "data": {"status": "succeeded", "outputs": {"result": "模拟行程"}},
        }


class FakeDifyClient:
    def __init__(self, **kwargs):
        self.timeout = kwargs["timeout"]
        self.request = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, traceback):
        return False

    async def post(self, url, headers, json):
        self.request = {"url": url, "headers": headers, "json": json}
        return FakeDifyResponse()

client = TestClient(app)


def test_health():
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_empty_destination_is_rejected():
    response = client.post(
        "/api/travel/plan",
        json={
            "departure": "上海",
            "destination": "",
            "travel_dates": "2026-10-03/2026-10-05",
            "budget": "3000",
            "companions": "2",
            "preferences": "历史景点、咖啡、美食、少走路",
            "language": "中文",
        },
    )

    assert response.status_code == 422


def test_invalid_budget_is_rejected():
    response = client.post("/api/travel/plan", json={
        "departure": "上海", "destination": "杭州",
        "travel_dates": "2026-10-03/2026-10-05", "budget": "0",
        "companions": "2", "preferences": "少走路", "language": "中文",
    })
    assert response.status_code == 422


def test_reversed_dates_are_rejected():
    response = client.post("/api/travel/plan", json={
        "departure": "上海", "destination": "杭州",
        "travel_dates": "2026-10-05/2026-10-03", "budget": "3000",
        "companions": "2", "preferences": "少走路", "language": "中文",
    })
    assert response.status_code == 422


def test_missing_api_key_returns_clear_error(monkeypatch):
    monkeypatch.delenv("DIFY_API_KEY", raising=False)
    monkeypatch.setenv("LOCAL_FALLBACK", "false")

    response = client.post(
        "/api/travel/plan",
        json={
            "departure": "上海",
            "destination": "杭州",
            "travel_dates": "2026-10-03/2026-10-05",
            "budget": "3000",
            "companions": "2",
            "preferences": "历史景点、咖啡、美食、少走路",
            "language": "中文",
        },
    )

    assert response.status_code == 503
    assert "DIFY_API_KEY" in response.json()["detail"]


def test_local_fallback_returns_structured_plan(monkeypatch):
    monkeypatch.delenv("DIFY_API_KEY", raising=False)
    monkeypatch.setenv("LOCAL_FALLBACK", "true")
    response = client.post(
        "/api/travel/plan",
        json={
            "departure": "上海", "destination": "杭州",
            "travel_dates": "2026-10-03/2026-10-05", "budget": "1000",
            "companions": "2", "preferences": "历史景点、咖啡、美食、少走路", "language": "中文",
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["source"] == "local-fallback"
    assert "行程概览" in body["plan"]
    assert body["warnings"]


def test_dify_success_response_is_forwarded(monkeypatch):
    fake_client = FakeDifyClient(timeout=30)
    monkeypatch.setattr("api.main.httpx.AsyncClient", lambda **kwargs: fake_client)
    monkeypatch.setenv("DIFY_API_KEY", "test-key")
    monkeypatch.setenv("DIFY_BASE_URL", "http://dify.test")
    monkeypatch.setenv("DIFY_APP_MODE", "workflow")

    response = client.post("/api/travel/plan", json={
        "departure": "上海", "destination": "杭州",
        "travel_dates": "2026-10-03/2026-10-05", "budget": "3000",
        "companions": "2", "preferences": "少走路", "language": "中文",
    })

    assert response.status_code == 200
    assert {key: response.json()[key] for key in ('success', 'source', 'workflow_id', 'outputs')} == {
        "success": True,
        "source": "dify",
        "workflow_id": "run-test-001",
        "outputs": {"result": "模拟行程"},
    }
    assert fake_client.request["url"] == "http://dify.test/v1/workflows/run"
    assert fake_client.request["json"]["inputs"]["destination"] == "杭州"


def test_advanced_chat_response_is_forwarded(monkeypatch):
    class ChatResponse(FakeDifyResponse):
        def json(self):
            return {"message_id": "msg-test-001", "conversation_id": "conv-test-001", "answer": "模拟回答"}

    class ChatClient(FakeDifyClient):
        async def post(self, url, headers, json):
            self.request = {"url": url, "headers": headers, "json": json}
            return ChatResponse()

    fake_client = ChatClient(timeout=30)
    monkeypatch.setattr("api.main.httpx.AsyncClient", lambda **kwargs: fake_client)
    monkeypatch.setenv("DIFY_API_KEY", "test-key")
    monkeypatch.setenv("DIFY_BASE_URL", "http://dify.test")
    monkeypatch.setenv("DIFY_APP_MODE", "advanced-chat")

    response = client.post("/api/travel/plan", json={
        "departure": "上海", "destination": "杭州",
        "travel_dates": "2026-10-03/2026-10-05", "budget": "3000",
        "companions": "2", "preferences": "少走路", "language": "中文",
    })

    assert response.status_code == 200
    assert response.json()["answer"] == "模拟回答"
    assert fake_client.request["url"] == "http://dify.test/v1/chat-messages"
    assert "杭州" in fake_client.request["json"]["query"]
