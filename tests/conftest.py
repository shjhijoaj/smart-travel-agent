import pytest


@pytest.fixture(autouse=True)
def temporary_history(tmp_path, monkeypatch):
    from api import limits
    limits.reset()
    monkeypatch.delenv('DIFY_API_KEY', raising=False)
    monkeypatch.setenv('LOCAL_FALLBACK','true')
    monkeypatch.setenv("WEATHER_ENABLED", "false")
    monkeypatch.setenv("TRAVEL_DB_PATH", str(tmp_path / "test.db"))
