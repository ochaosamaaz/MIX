"""
Crypto news fetcher.
Uses CoinGecko API for price data and NewsAPI for crypto news.
"""

import logging
from datetime import datetime, timedelta

import httpx

from config import settings

logger = logging.getLogger(__name__)

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
NEWSAPI_BASE = "https://newsapi.org/v2"

# Top coins to track
TOP_COINS = ["bitcoin", "ethereum", "solana", "xrp", "cardano"]


async def fetch_crypto_prices() -> list[dict]:
    """Fetch current prices for top cryptocurrencies."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{COINGECKO_BASE}/simple/price",
                params={
                    "ids": ",".join(TOP_COINS),
                    "vs_currencies": "usd",
                    "include_24hr_change": "true",
                    "include_market_cap": "true",
                },
            )
            response.raise_for_status()
            data = response.json()

            prices = []
            for coin in TOP_COINS:
                if coin in data:
                    prices.append({
                        "name": coin.capitalize(),
                        "symbol": coin[:3].upper() if coin != "bitcoin" else "BTC",
                        "price_usd": data[coin].get("usd", 0),
                        "change_24h": data[coin].get("usd_24h_change", 0),
                        "market_cap": data[coin].get("usd_market_cap", 0),
                    })
            return prices
    except Exception as e:
        logger.error(f"Error fetching crypto prices: {e}")
        return []


async def fetch_crypto_news(limit: int = 5) -> dict:
    """
    Fetch latest crypto news articles.
    Returns dict with 'articles' list and 'prices' list.
    """
    articles = []
    prices = await fetch_crypto_prices()

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            # Fetch news from NewsAPI
            yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
            response = await client.get(
                f"{NEWSAPI_BASE}/everything",
                params={
                    "q": "cryptocurrency OR bitcoin OR ethereum OR crypto market",
                    "from": yesterday,
                    "sortBy": "publishedAt",
                    "language": "en",
                    "pageSize": limit,
                    "apiKey": settings.NEWSAPI_KEY,
                },
            )
            response.raise_for_status()
            data = response.json()

            for article in data.get("articles", [])[:limit]:
                articles.append({
                    "title": article.get("title", ""),
                    "description": article.get("description", ""),
                    "source": article.get("source", {}).get("name", "Unknown"),
                    "url": article.get("url", ""),
                    "published_at": article.get("publishedAt", ""),
                })

    except Exception as e:
        logger.error(f"Error fetching crypto news: {e}")

    return {
        "category": "crypto",
        "articles": articles,
        "prices": prices,
        "fetched_at": datetime.utcnow().isoformat(),
    }
