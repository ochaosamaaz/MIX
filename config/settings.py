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

    # Twelve Data API (for real OHLC price data)
    TWELVE_DATA_API_KEY: str = os.getenv("TWELVE_DATA_API_KEY", "")

    # Scheduler
    TIMEZONE: str = os.getenv("TIMEZONE", "Asia/Jakarta")

    # Language
    DEFAULT_LANGUAGE: str = os.getenv("DEFAULT_LANGUAGE", "en")

    # Channel (for auto-posting updates to a Telegram channel)
    # Can be @channel_username or numeric channel ID (e.g., -1001234567890)
    CHANNEL_ID: str = os.getenv("CHANNEL_ID", "")
    CHANNEL_LANGUAGE: str = os.getenv("CHANNEL_LANGUAGE", "en")

    # Force Join — Users must join this channel to use the bot
    # Set to channel username WITHOUT @ (e.g., "CielMarketNews")
    FORCE_JOIN_CHANNEL: str = os.getenv("FORCE_JOIN_CHANNEL", "")

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
