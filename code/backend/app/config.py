import os

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Supabase PostgreSQL 连接串（必填，见 backend/.env.example）
    # 示例：postgresql+psycopg2://postgres.[ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres
    database_url: str = ""
    database_ssl_mode: str = "require"
    jwt_secret: str = "dev-secret-change-me"
    jwt_expire_minutes: int = 1440
    cors_origins: str = "http://127.0.0.1:5180,http://localhost:5180"

    @property
    def cors_origin_list(self) -> list[str]:
        origins = [o.strip() for o in self.cors_origins.split(",") if o.strip()]
        vercel_url = os.getenv("VERCEL_URL")
        if vercel_url:
            origins.append(f"https://{vercel_url}")
        return list(dict.fromkeys(origins))
    @property
    def db_connect_args(self) -> dict[str, str]:
        if not self.database_ssl_mode:
            return {}
        return {"sslmode": self.database_ssl_mode}


settings = Settings()
