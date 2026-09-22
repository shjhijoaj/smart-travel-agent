import pytest


@pytest.fixture(autouse=True)
def temporary_history(tmp_path, monkeypatch):
    monkeypatch.setenv("WEATHER_ENABLED", "false")
    monkeypatch.setenv("TRAVEL_DB_PATH", str(tmp_path / "test.db"))
