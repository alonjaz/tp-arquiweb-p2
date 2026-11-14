from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    service_name: str = "ping-svc"
    database_url: str
    broker_url: str | None = None       # ping-svc no publica eventos
    log_level: str = "INFO"
    ping_body_limit: int = 100_000
    db_pool_min: int = 2
    db_pool_max: int = 10
    db_connect_timeout: float = 2.0
settings = Settings()

