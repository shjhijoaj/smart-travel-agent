"""Explicitly restarts only this project's Compose service and checks persistence."""
import json
import secrets
import subprocess
import time
import httpx

credentials={'username':'persist_'+secrets.token_hex(5),'password':secrets.token_urlsafe(24)}
with httpx.Client(base_url='http://127.0.0.1:8000',trust_env=False,timeout=10) as client:
    client.post('/api/account/register',json=credentials).raise_for_status()
    client.put('/api/account/memory',json={'content':'容器重启持久化验收'}).raise_for_status()
    subprocess.run(['docker','compose','restart','travel-agent-api'],check=True)
    for attempt in range(20):
        try:
            client.get('/api/health').raise_for_status()
            break
        except httpx.HTTPError:
            time.sleep(.5)
    client.post('/api/account/login',json=credentials).raise_for_status()
    assert client.get('/api/account/memory').json()['content']=='容器重启持久化验收'
    client.delete('/api/account/memory').raise_for_status()
    client.post('/api/account/logout').raise_for_status()
    print(json.dumps({'container_restart':'passed','account_persisted':True,'memory_persisted':True}))
