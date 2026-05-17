from src.config import Settings


def test_settings_loaded_from_env_mysql(monkeypatch):
    monkeypatch.setenv("DB_DIALECT", "mysql")
    monkeypatch.setenv("DB_HOST", "testhost")
    monkeypatch.setenv("DB_PORT", "3307")
    monkeypatch.setenv("DB_USER", "u")
    monkeypatch.setenv("DB_PASSWORD", "p")
    monkeypatch.setenv("DB_NAME", "n")
    s = Settings()
    assert s.db_host == "testhost"
    assert s.db_port == 3307
    assert s.db_url.startswith("mysql+pymysql://u:p@testhost:3307/n")


def test_settings_sqlite_url(monkeypatch):
    monkeypatch.setenv("DB_DIALECT", "sqlite")
    monkeypatch.setenv("SQLITE_PATH", "/tmp/test.db")
    s = Settings()
    assert s.db_url == "sqlite:////tmp/test.db"


def test_default_settings():
    s = Settings()
    assert s.api_port == 8000
    assert s.model_path == "models/xgboost.pkl"
