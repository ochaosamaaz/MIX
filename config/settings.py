import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    """Application settings loaded from environment variables."""

    # Telegram
    TELEGRAM_BOT_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")

    # LLM
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_BASE_URL: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "llama-3.3-70b-versatile")

    # News APIs
    NEWSAPI_KEY: str = os.getenv("NEWSAPI_KEY", "")

    # Scheduler
    TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Jakarta")

    # Language
    DEFAULT_LANGUAGE: str = os.getenv("DEFAULT_LANGUAGE", "en")

    # Schedule times (24h format)
    MORNING_HOUR: int = 7
    MORNING_MINUTE: int = 0
    EVENING_HOUR: int = 18
    EVENING_MINUTE: int = 0

    # Market categories
    MARKETS = ["crypto", "stocks", "forex"]

    def validate(self) -> list[str]:
        """Validate required settings. Returns list of missing keys."""
        missing = []
        if not self.TELEGRAM_BOT_TOKEN:
            missing.append("TELEGRAM_BOT_TOKEN")
        if not self.OPENAI_API_KEY:
            missing.append("OPENAI_API_KEY")
        if not self.NEWSAPI_KEY:
            missing.append("NEWSAPI_KEY")
        return missing
