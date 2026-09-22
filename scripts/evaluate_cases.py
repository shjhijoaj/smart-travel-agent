"""Deterministic product evaluation: no model key and no external calls required."""
import json
import os
import time
from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
os.environ.pop('DIFY_API_KEY', None)
os.environ['DIFY_API_KEY'] = ''
os.environ['DIFY_BASE_URL'] = 'http://127.0.0.1:1'
os.environ['LOCAL_FALLBACK'] = 'true'
os.environ['WEATHER_ENABLED'] = 'false'
os.environ['TRAVEL_DB_PATH'] = str(Path('test-results') / 'evaluation.db')
from api.main import app


CASES = [
    {"name": "budget_warning", "payload": {"departure": "上海", "destination": "杭州", "travel_dates": "2026-10-03/2026-10-05", "budget": "1000", "companions": "2", "preferences": "少走路"}, "expects": ["local-fallback", "warnings"]},
    {"name": "single_day", "payload": {"departure": "北京", "destination": "广州", "travel_dates": "2026-10-03/2026-10-03", "budget": "5000", "companions": "1", "preferences": "博物馆"}, "expects": ["local-fallback", "行程概览"]},
]


def main():
    report = {"started_at": time.strftime('%Y-%m-%dT%H:%M:%S'), "cases": []}
    with TestClient(app) as client:
        for case in CASES:
            started = time.perf_counter()
            response = client.post('/api/travel/plan', json=case['payload'])
            body = response.json()
            text = json.dumps(body, ensure_ascii=False)
            passed = response.status_code == 200 and all((item in text if item != 'warnings' else bool(body.get('warnings'))) for item in case['expects'])
            report['cases'].append({"name": case['name'], "passed": passed, "status": response.status_code, "duration_ms": round((time.perf_counter()-started)*1000, 2), "validation": body.get('validation', {})})
    report['passed'] = all(item['passed'] for item in report['cases'])
    Path('test-results').mkdir(exist_ok=True)
    Path('test-results/evaluation.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if report['passed'] else 1)


if __name__ == '__main__':
    main()
