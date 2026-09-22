"""Open-Meteo adapter: bounded requests and explicit incomplete coverage."""
import asyncio
import os
from datetime import date, datetime, timezone
import httpx


async def lookup(destination, start, end, location_id=None):
    report = dict(source="Open-Meteo", source_url="https://open-meteo.com/",
                  fetched_at=datetime.now(timezone.utc).isoformat(), days=[], status="unavailable")
    try:
        async def fetch():
            async with httpx.AsyncClient(timeout=8, trust_env=os.getenv('WEATHER_TRUST_ENV', 'false').lower() == 'true') as client:
                r = await client.get('https://geocoding-api.open-meteo.com/v1/search',
                                     params=dict(name=destination, count=5, language='zh', format='json'))
                r.raise_for_status()
                places = r.json().get('results', [])
                if location_id is not None:
                    places = [p for p in places if p.get('id') == location_id]
                if not places:
                    report['message'] = '未找到目的地，请使用明确的城市名称。'
                    return report
                if len(places) > 1:
                    report.update(status='ambiguous', message='发现多个同名地点，未自动选择天气位置。',
                                  candidates=[dict(id=p.get('id'), name=p.get('name'), region=p.get('admin1'), country=p.get('country')) for p in places])
                    return report
                place = places[0]
                r = await client.get('https://api.open-meteo.com/v1/forecast', params=dict(
                    latitude=place['latitude'], longitude=place['longitude'], timezone='auto', forecast_days=16,
                    daily='temperature_2m_max,temperature_2m_min,precipitation_probability_max'))
                r.raise_for_status()
                daily = r.json()['daily']
                for i, day in enumerate(daily['time']):
                    if start <= date.fromisoformat(day) <= end:
                        low, high, rain = (daily[key][i] for key in ('temperature_2m_min', 'temperature_2m_max', 'precipitation_probability_max'))
                        report['days'].append(dict(date=day, low_c=low, high_c=high, rain_percent=rain,
                                                   indoor_recommended=isinstance(rain, (float, int)) and rain >= 60))
                count = len(report['days'])
                report.update(location=dict(name=place['name'], region=place.get('admin1'), country=place.get('country')),
                              status='ok' if count == (end-start).days+1 else 'partial' if count else 'out_of_range',
                              message='仅对预报覆盖日期提供天气建议；预报可能变化，请临近出行再次查询。')
                return report
        return await asyncio.wait_for(fetch(), timeout=18)
    except (httpx.HTTPError, asyncio.TimeoutError, ValueError, KeyError, TypeError, IndexError):
        report.update(status='unavailable', days=[], message='天气服务暂不可用，本次不提供已验证天气。')
        return report
