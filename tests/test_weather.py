import asyncio
from datetime import date
import httpx
from api.weather import lookup


def test_forecast_and_partial_coverage(monkeypatch):
    original = httpx.AsyncClient
    def handler(request):
        if 'geocoding' in request.url.host:
            return httpx.Response(200, json={'results':[{'name':'杭州','latitude':30,'longitude':120}]})
        return httpx.Response(200,json={'daily':{'time':['2026-09-22'],'temperature_2m_min':[20],
                              'temperature_2m_max':[25],'precipitation_probability_max':[80]}})
    monkeypatch.setattr('api.weather.httpx.AsyncClient',lambda **kwargs: original(transport=httpx.MockTransport(handler),**kwargs))
    result=asyncio.run(lookup('杭州',date(2026,9,22),date(2026,9,24)))
    assert result['status']=='partial'
    assert result['days'][0]['indoor_recommended']
    assert len(result['days'])==1


def test_ambiguous_city_not_guessed(monkeypatch):
    original=httpx.AsyncClient
    monkeypatch.setattr('api.weather.httpx.AsyncClient',lambda **kwargs: original(transport=httpx.MockTransport(
        lambda r: httpx.Response(200,json={'results':[{'name':'Paris'},{'name':'Paris'}]})),**kwargs))
    assert asyncio.run(lookup('Paris',date.today(),date.today()))['status']=='ambiguous'


def test_unavailable_is_not_fabricated(monkeypatch):
    original=httpx.AsyncClient
    monkeypatch.setattr('api.weather.httpx.AsyncClient',lambda **kwargs: original(transport=httpx.MockTransport(
        lambda r: httpx.Response(503)),**kwargs))
    result=asyncio.run(lookup('杭州',date.today(),date.today()))
    assert result['status']=='unavailable'
    assert result['days']==[]


def test_selected_city_is_used_and_stale_selection_rejected(monkeypatch):
    original = httpx.AsyncClient
    forecasts = []
    def handler(request):
        if 'geocoding' in request.url.host:
            return httpx.Response(200, json={'results': [
                {'id': 1, 'name': '杭州', 'latitude': 30, 'longitude': 120},
                {'id': 2, 'name': '杭州', 'latitude': 31, 'longitude': 121}]})
        forecasts.append(request.url.params['latitude'])
        return httpx.Response(200, json={'daily': {'time': ['2026-09-22'],
            'temperature_2m_min': [20], 'temperature_2m_max': [25], 'precipitation_probability_max': [10]}})
    monkeypatch.setattr('api.weather.httpx.AsyncClient', lambda **kw: original(transport=httpx.MockTransport(handler), **kw))
    assert asyncio.run(lookup('杭州', date(2026,9,22), date(2026,9,22), 2))['status'] == 'ok'
    assert forecasts == ['31']
    assert asyncio.run(lookup('杭州', date(2026,9,22), date(2026,9,22), 3))['status'] == 'unavailable'
    assert forecasts == ['31']
