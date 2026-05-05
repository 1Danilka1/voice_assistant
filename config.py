import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    BOT_TOKEN: str = os.environ["BOT_TOKEN"]
    OPENAI_API_KEY: str = os.environ["OPENAI_API_KEY"]
    ANTHROPIC_API_KEY: str = os.environ["ANTHROPIC_API_KEY"]
    ICLOUD_USERNAME: str = os.getenv("ICLOUD_USERNAME", "")
    ICLOUD_PASSWORD: str = os.getenv("ICLOUD_PASSWORD", "")
    TG_API_ID: int = int(os.getenv("TG_API_ID", "0"))
    TG_API_HASH: str = os.getenv("TG_API_HASH", "")
    TIMEZONE: str = os.getenv("TIMEZONE", "Europe/Moscow")
    DB_PATH: str = os.getenv("DB_PATH", "assistant.db")


settings = Settings()
