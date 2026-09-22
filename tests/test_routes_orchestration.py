import asyncio
import httpx
from fastapi.testclient import TestClient
from api.main import app
from api.orchestration import review
from api.routes import RouteRequest, calculate_route


def test_review_triggers_rain_and_long_route():
    result = review({}, {"days": [{"date": "2026-10-03", "rain_percent": 80}]}, {"duration_min": 240}, "")
    assert result['status'] == 'needs_replan'
    assert {a['type'] for a in result['actions']} == {'weather', 'route'}


def test_local_adjust_keeps_schedule_and_adds_reason():
    client = TestClient(app)
    response = client.post('/api/travel/local-adjust', json={"days": [{"title": "第1天", "activities": [{"time": "09:00-10:00", "place": "西湖", "fields": {}}]}], "actions": [{"type": "weather", "priority": "high", "message": "雨天改室内"}]})
    assert response.status_code == 200
    assert response.json()['days'][0]['activities'][0]['fields']['智能调整建议'] == '雨天改室内'


def test_route_selected_coordinates(monkeypatch):
    original = httpx.AsyncClient
    def handler(request):
        return httpx.Response(200, json={"code": "Ok", "routes": [{"distance": 12345, "duration": 3600}]})
    monkeypatch.setattr('api.routes.httpx.AsyncClient', lambda **kw: original(transport=httpx.MockTransport(handler), **kw))
    result = asyncio.run(calculate_route(RouteRequest(destination='杭州', stops=[{"name":"A","latitude":30,"longitude":120},{"name":"B","latitude":30.1,"longitude":120.1}])))
    assert result['status'] == 'ok'
    assert result['distance_km'] == 12.3
    assert result['duration_min'] == 60
