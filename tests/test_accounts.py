import hashlib
import time
from fastapi.testclient import TestClient
from api.main import app
from api.history import database


CREDS = {'username':'traveler', 'password':'test-password-123'}


def test_auth_persistence_isolation_logout():
    a, b = TestClient(app), TestClient(app)
    assert a.post('/api/account/register', json=CREDS).status_code == 200
    assert a.get('/api/account/me').json()['user']['username'] == 'traveler'
    assert 'httponly' in a.post('/api/account/login', json=CREDS).headers['set-cookie'].lower()
    token = a.cookies.get('travel_auth')
    assert a.put('/api/account/memory',json={'content':'少走路，不吃辣'}).status_code == 200
    assert b.get('/api/account/memory').status_code == 401
    assert b.post('/api/account/login',json={**CREDS,'password':'wrong-password'}).status_code == 401
    assert b.post('/api/account/login',json=CREDS).status_code == 200
    assert b.get('/api/account/memory').json()['content'] == '少走路，不吃辣'
    assert a.post('/api/account/logout').status_code == 200
    a.cookies.set('travel_auth',token)
    assert a.get('/api/account/me').json()['user'] is None
    assert b.get('/api/account/me').json()['user']
    assert b.delete('/api/account/memory').status_code == 200
    assert b.get('/api/account/memory').json()['content'] == ''
    with database() as conn:
        password = conn.execute('SELECT password_hash FROM users').fetchone()[0]
        assert CREDS['password'] not in password
        assert conn.execute('SELECT digest FROM sessions WHERE digest=?',(hashlib.sha256(token.encode()).hexdigest(),)).fetchone() is None


def test_expired_session_and_csrf():
    client = TestClient(app)
    assert client.post('/api/account/register',json=CREDS,headers={'Origin':'https://evil.test'}).status_code == 403
    client.post('/api/account/register',json=CREDS)
    with database() as conn:
        conn.execute('UPDATE sessions SET expires=?',(time.time()-1,))
    assert client.get('/api/account/memory').status_code == 401


def test_login_rate_limit():
    client=TestClient(app)
    for _ in range(5):
        assert client.post('/api/account/login',json=CREDS).status_code==401
    assert client.post('/api/account/login',json=CREDS).status_code==429


def test_account_history_does_not_leak(monkeypatch):
    monkeypatch.delenv('DIFY_API_KEY',raising=False)
    monkeypatch.setenv('LOCAL_FALLBACK','true')
    a,b=TestClient(app),TestClient(app)
    a.post('/api/account/register',json=CREDS)
    b.post('/api/account/register',json={**CREDS,'username':'another'})
    payload=dict(departure='上海',destination='杭州',travel_dates='2026-10-03/2026-10-03',budget='2000',companions='2',preferences='少走路')
    plan=a.post('/api/travel/plan',json=payload).json()
    assert b.get('/api/history/'+plan['plan_id']).status_code==404
    a.post('/api/account/logout')
    assert a.get('/api/history').json()['items']==[]
    a.post('/api/account/login',json=CREDS)
    assert a.get('/api/history/'+plan['plan_id']).status_code==200


def test_password_change_revokes_other_sessions():
    a,b=TestClient(app),TestClient(app)
    a.post('/api/account/register',json=CREDS)
    b.post('/api/account/login',json=CREDS)
    assert a.put('/api/account/password',json={'old_password':'wrong-password','new_password':'new-password-123'}).status_code==401
    assert a.put('/api/account/password',json={'old_password':CREDS['password'],'new_password':'new-password-123'}).status_code==200
    assert b.get('/api/account/me').json()['user'] is None
    assert a.get('/api/account/me').json()['user']
    assert b.post('/api/account/login',json=CREDS).status_code==401
    assert b.post('/api/account/login',json={**CREDS,'password':'new-password-123'}).status_code==200
