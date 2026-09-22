"""Opt-in real HTTP acceptance: one model call; never print credentials."""
import json
import os
from pathlib import Path
import secrets
import time
from datetime import date, timedelta
import httpx

base=os.getenv('TRAVEL_URL','http://127.0.0.1:8010')
report={'base':base,'checked_at':time.strftime('%Y-%m-%dT%H:%M:%S')}
output=Path('test-results');output.mkdir(exist_ok=True)
creds={'username':'accept_'+secrets.token_hex(5),'password':secrets.token_urlsafe(24)}
today=date.today()
payload=dict(departure='深圳',destination='广州',travel_dates=f'{today+timedelta(days=1)}/{today+timedelta(days=2)}',
             budget='3000',companions='2',preferences='陈家祠、广东省博物馆、沙面；优先引用知识库资料，安排轻松行程',use_memory=True)
with httpx.Client(base_url=base, timeout=200, trust_env=False) as client:
    r=client.post('/api/account/register',json=creds);r.raise_for_status()
    client.put('/api/account/memory',json={'content':'不吃辣，避免长时间步行，优先公交地铁'}).raise_for_status()
    client.post('/api/account/logout').raise_for_status()
    client.post('/api/account/login',json=creds).raise_for_status()
    report['memory_after_login']=client.get('/api/account/memory').json()['content']=='不吃辣，避免长时间步行，优先公交地铁'
    w=client.post('/api/travel/weather',json={**payload,'destination':'杭州','weather_location_id':1808926,'travel_dates':f'{today}/{today}'}).json()
    report['weather_status']=w['status'];report['weather_days']=len(w['days'])
    assert w['status']=='ok', w
    geo=client.post('/api/travel/weather',json=payload).json()
    if geo.get('candidates'):
        matches=[c for c in geo['candidates'] if c.get('region') in ('广东','Guangdong')]
        if len(matches)==1:payload['weather_location_id']=matches[0]['id']
    started=time.monotonic();deltas=0;first=None;completed=None;nodes=[];wire=''
    with client.stream('POST','/api/travel/stream',json=payload) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if not line.startswith('data: '):continue
            event=json.loads(line[6:]);kind=event['event']
            if kind=='status':nodes.append(event['message'])
            if kind=='delta':
                deltas+=1;wire+=event['text']
                if first is None:first=round(time.monotonic()-started,2)
            if kind=='error':raise RuntimeError(event['message'])
            if kind=='complete':completed=event['result']
    assert completed and deltas>1, 'No real stream completion'
    assert '<think>' not in wire.lower()
    record=client.get('/api/history/'+completed['plan_id']);record.raise_for_status()
    report.update(stream_deltas=deltas,first_answer_seconds=first,total_seconds=round(time.monotonic()-started,2),
                  final_chars=len(completed.get('answer','')),sources=len(completed.get('sources',[])),saved=True,status='passed',node_statuses=nodes)
    (output/'live-v1-result.json').write_text(json.dumps(record.json(),ensure_ascii=False),encoding='utf-8')
    client.delete('/api/account/memory').raise_for_status()
    client.delete('/api/history/'+completed['plan_id']).raise_for_status()
    client.post('/api/account/logout').raise_for_status()
(output/'acceptance-v1.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=True,indent=2))
