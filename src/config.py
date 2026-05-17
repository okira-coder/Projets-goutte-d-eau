from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Dialecte BDD : "sqlite" (MVP local) ou "mysql" (prod cible)
    db_dialect: str = "sqlite"

    # MySQL (cible production)
    db_host: str = "localhost"
    db_port: int = 3306
    db_user: str = "goutte_app"
    db_password: str = "change_me"
    db_name: str = "goutte_eau"

    # SQLite (MVP local)
    sqlite_path: str = "data/goutte_eau.db"

    api_host: str = "0.0.0.0"
    api_port: int = 8000

    model_path: str = "models/xgboost.pkl"
    log_level: str = "INFO"

    @property
    def db_url(self) -> str:
        if self.db_dialect == "sqlite":
            return f"sqlite:///{self.sqlite_path}"
        return (
            f"mysql+pymysql://{self.db_user}:{self.db_password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}?charset=utf8mb4"
        )


settings = Settings()
