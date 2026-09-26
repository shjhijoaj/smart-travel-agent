import sqlite3
from fastapi.testclient import TestClient
from api.main import app
from api import telemetry, limits

PAYLOAD={"departure":"上海","destination":"杭州","travel_dates":"2026-10-03/2026-10-05","budget":"3000","companions":"2","preferences":"少走路","language":"中文"}


def create(client):
    r=client.post('/api/travel/plan',json=PAYLOAD)
    assert r.status_code==200,r.text
    return r.json()


def test_manual_plan_is_structured_editable_and_export_consistent(monkeypatch):
    monkeypatch.delenv('DIFY_API_KEY',raising=False)
    with TestClient(app) as c:
        result=create(c)
        assert len(result['validation']['days'])==3
        days=result['validation']['days']
        days[0]['activities'][0]['place']='用户确认的西湖散步'
        response=c.patch('/api/history/'+result['plan_id']+'/structured',json={'days':days})
        assert response.status_code==200,response.text
        saved=c.get('/api/history/'+result['plan_id']).json()['result']
        assert '用户确认的西湖散步' in saved['edited_plan']
        assert '用户确认的西湖散步' not in saved['plan']
        assert saved['validation']['structured_override'] is True


def test_oversized_edit_rejected_without_corrupting_original(monkeypatch):
    monkeypatch.delenv('DIFY_API_KEY',raising=False)
    with TestClient(app) as c:
        result=create(c); days=result['validation']['days']; days[0]['activities'][0]['place']='x'*161
        assert c.patch('/api/history/'+result['plan_id']+'/structured',json={'days':days}).status_code==422
        assert 'edited_plan' not in c.get('/api/history/'+result['plan_id']).json()['result']


def test_history_search_pagination_and_owner_isolation(monkeypatch):
    monkeypatch.delenv('DIFY_API_KEY',raising=False)
    with TestClient(app) as a, TestClient(app) as b:
        create(a);create(a)
        page=a.get('/api/history?q=杭州&limit=1').json()
        assert len(page['items'])==1 and page['has_more']
        assert len(a.get('/api/history?q=杭州&limit=1&offset=1').json()['items'])==1
        assert not a.get('/api/history?q=北京').json()['items']
        assert not b.get('/api/history?q=杭州').json()['items']
        assert b.patch('/api/history/'+page['items'][0]['id']+'/structured',json={'days':[{'title':'测试','activities':[]}]}).status_code==404


def test_metrics_failure_does_not_lose_successful_plan(monkeypatch):
    monkeypatch.delenv('DIFY_API_KEY',raising=False)
    def broken(*args,**kwargs): raise sqlite3.OperationalError('test failure')
    monkeypatch.setattr(telemetry,'record',broken)
    monkeypatch.setenv('DIFY_COST_PER_1K','invalid')
    with TestClient(app) as c:
        r=create(c)
        assert c.get('/api/history/'+r['plan_id']).status_code==200


def test_disabled_provider_not_ready(monkeypatch):
    monkeypatch.delenv('DIFY_API_KEY',raising=False);monkeypatch.setenv('LOCAL_FALLBACK','false')
    with TestClient(app) as c: assert c.get('/api/ready').status_code==503


def test_generation_limit_keeps_history_available(monkeypatch):
    monkeypatch.delenv('DIFY_API_KEY',raising=False);monkeypatch.setenv('GENERATION_LIMIT_PER_HOUR','1')
    with TestClient(app) as c:
        create(c)
        assert c.post('/api/travel/stream',json=PAYLOAD).status_code==429
        assert c.get('/api/history').status_code==200


def test_unreasonable_group_size_is_rejected():
    with TestClient(app) as c: assert c.post('/api/travel/plan',json={**PAYLOAD,'companions':'999'}).status_code==422
