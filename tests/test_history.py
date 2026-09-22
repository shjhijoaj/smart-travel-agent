from fastapi.testclient import TestClient
from api.main import app
from api import history
import httpx


def setup_demo(monkeypatch):
    monkeypatch.delenv("DIFY_API_KEY", raising=False)
    monkeypatch.setenv("LOCAL_FALLBACK", "true")
    return dict(departure="上海", destination="杭州", budget="5000", companions="2",
                preferences="少走路", travel_dates="2026-10-03/2026-10-05")


def test_history_persists_and_is_isolated(monkeypatch):
    payload = setup_demo(monkeypatch)
    first, other = TestClient(app), TestClient(app)
    generated = first.post('/api/travel/plan', json=payload).json()
    plan_id = generated['plan_id']
    assert first.get('/api/history').json()['items'][0]['id'] == plan_id
    assert other.get('/api/history').json()['items'] == []
    assert other.get('/api/history/' + plan_id).status_code == 404
    assert other.delete('/api/history/' + plan_id).status_code == 404
    assert other.post('/api/history/' + plan_id + '/replan', json=payload).status_code == 404
    restored = TestClient(app)
    restored.cookies.update(first.cookies)
    assert restored.get('/api/history/' + plan_id).json()['request']['destination'] == '杭州'
    payload['budget'] = '2000'
    revised = restored.post('/api/history/' + plan_id + '/replan', json=payload)
    assert revised.status_code == 200
    new_id = revised.json()['plan_id']
    assert new_id != plan_id
    assert restored.get('/api/history/' + new_id).json()['parent_id'] == plan_id
    assert restored.get('/api/history/' + plan_id).json()['request']['budget'] == '5000'
    assert restored.delete('/api/history/' + plan_id).status_code == 200
    assert restored.get('/api/history/' + plan_id).status_code == 404
    assert restored.get('/api/history/' + new_id).status_code == 200


def test_save_failure_preserves_generated_plan(monkeypatch):
    payload = setup_demo(monkeypatch)
    def fail(*args, **kwargs):
        raise OSError('disk full')
    monkeypatch.setattr(history, 'save', fail)
    response = TestClient(app).post('/api/travel/plan', json=payload)
    assert response.status_code == 200
    assert response.json()['plan']
    assert 'save_warning' in response.json()


def test_invalid_request_not_saved(monkeypatch):
    payload = setup_demo(monkeypatch)
    client = TestClient(app)
    payload['budget'] = '-1'
    assert client.post('/api/travel/plan', json=payload).status_code == 422
    assert client.get('/api/history').json()['items'] == []


def test_real_adapter_replan_context_and_clean_history(monkeypatch):
    payload = setup_demo(monkeypatch)
    monkeypatch.setenv('DIFY_API_KEY', 'test-key')
    monkeypatch.setenv('DIFY_APP_MODE', 'advanced-chat')
    monkeypatch.setenv('DIFY_BASE_URL', 'http://dify.test')
    import json
    captured = []
    original = httpx.AsyncClient
    def handle(request):
        captured.append(json.loads(request.content))
        return httpx.Response(200, json={'answer': '<think>internal reasoning</think>## 每日行程\n西湖散步\n| 合计 | 2000 |'})
    monkeypatch.setattr('api.main.httpx.AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(handle), **kwargs))
    client = TestClient(app)
    result = client.post('/api/travel/plan', json=payload).json()
    assert 'internal reasoning' not in result['answer']
    record = client.get('/api/history/' + result['plan_id']).json()
    assert record['request']['preferences'] == payload['preferences']
    assert '展示格式要求' in captured[0]['inputs']['preferences']
    payload['budget'] = '2500'
    updated = client.post('/api/history/' + result['plan_id'] + '/replan', json=payload)
    assert updated.status_code == 200
    assert '原方案参考' in captured[1]['inputs']['preferences']
    assert '西湖散步' in captured[1]['inputs']['preferences']
    assert 'internal reasoning' not in captured[1]['inputs']['preferences']
    assert captured[1]['inputs']['budget'] == '2500'
