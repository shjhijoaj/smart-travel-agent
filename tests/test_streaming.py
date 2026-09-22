import json
import httpx
import pytest
from fastapi.testclient import TestClient
from api.main import app
from api.streaming import ReasoningFilter


def parse(response):
    return [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]


@pytest.mark.parametrize('size',[1,2,3,7,100])
def test_reasoning_filter_across_fragments(size):
    source='<think>private\nanalysis</think><!--private comment-->## 行程\n到达西湖'
    f=ReasoningFilter()
    result=''.join(f.feed(source[i:i+size]) for i in range(0,len(source),size))+f.feed('',final=True)
    assert result=='## 行程\n到达西湖'


def test_sse_completion_persists_and_reads_memory(monkeypatch):
    original=httpx.AsyncClient
    captured=[]
    def handle(request):
        payload=json.loads(request.content);captured.append(payload)
        events=[{'event':'message','task_id':'task','answer':'<thi'},
                {'event':'message','answer':'nk>private</think>## 每日行程\n'},
                {'event':'message','answer':'西湖散步'},
                {'event':'message_end','message_id':'m','conversation_id':'c',
                 'metadata':{'retriever_resources':[{'document_name':'travel.md','content':'西湖资料'}]}}]
        return httpx.Response(200,text=''.join('data: '+json.dumps(e)+'\n\n' for e in events))
    monkeypatch.setattr('api.streaming.httpx.AsyncClient',lambda **kwargs: original(transport=httpx.MockTransport(handle),**kwargs))
    monkeypatch.setenv('DIFY_API_KEY','test-key');monkeypatch.setenv('DIFY_APP_MODE','advanced-chat')
    client=TestClient(app)
    client.post('/api/account/register',json={'username':'traveler','password':'test-password-123'})
    client.put('/api/account/memory',json={'content':'少走路，喜欢茶文化'})
    payload=dict(departure='上海',destination='杭州',travel_dates='2026-10-03/2026-10-03',budget='2000',companions='2',preferences='参观博物馆')
    response=client.post('/api/travel/stream',json=payload)
    events=parse(response)
    assert 'private' not in response.text
    assert any(e['event']=='delta' for e in events)
    assert events[-1]['event']=='complete'
    assert events[-1]['result']['sources'][0]['document_name']=='travel.md'
    assert captured[0]['response_mode']=='streaming'
    assert '少走路，喜欢茶文化' in captured[0]['inputs']['preferences']
    assert '参观博物馆' in captured[0]['inputs']['preferences']
    assert len(client.get('/api/history').json()['items'])==1
    payload['use_memory']=False
    client.post('/api/travel/stream',json=payload)
    assert '少走路，喜欢茶文化' not in captured[-1]['inputs']['preferences']


def test_premature_end_is_error_and_not_saved(monkeypatch):
    original=httpx.AsyncClient
    calls=[]
    def handle(request):
        calls.append(str(request.url))
        if str(request.url).endswith('/stop'):return httpx.Response(200,json={'result':'success'})
        return httpx.Response(200,text='data: {"event":"message","task_id":"t","answer":"partial"}\n\n')
    monkeypatch.setattr('api.streaming.httpx.AsyncClient',lambda **kwargs: original(transport=httpx.MockTransport(handle),**kwargs))
    monkeypatch.setenv('DIFY_API_KEY','test-key');monkeypatch.setenv('DIFY_APP_MODE','advanced-chat')
    client=TestClient(app)
    events=parse(client.post('/api/travel/stream',json=dict(departure='上海',destination='杭州',travel_dates='2026-10-03/2026-10-03',budget='2000',companions='2',preferences='少走路')))
    assert events[-1]['event']=='error'
    assert client.get('/api/history').json()['items']==[]
    assert any(url.endswith('/t/stop') for url in calls)
