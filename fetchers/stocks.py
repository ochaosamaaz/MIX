"""
US Stocks news fetcher.
Uses NewsAPI for stock market news with proper filtering.
"""

import logging
from datetime import datetime, timedelta

import httpx

from config import settings

logger = logging.getLogger(__name__)

NEWSAPI_BASE = "https://newsapi.org/v2"

# Major US indices and popular stocks to track
TRACKED_TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META"]

# Stock-specific query
STOCKS_QUERY = (
    '"stock market" OR "S&P 500" OR "Nasdaq" OR "Wall Street" '
    'OR "Dow Jones" OR "earnings" OR "NYSE" '
    'OR "AAPL" OR "MSFT" OR "NVDA" OR "TSLA" '
    'OR "Russell 2000" OR "market rally" OR "bull market" OR "bear market"'
)


async def fetch_stocks_news(limit: int = 5) -> dict:
    """
    Fetch latest US stock market news.
    Returns dict with 'articles' list.
    """
    articles = []

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
            response = await client.get(
                f"{NEWSAPI_BASE}/everything",
                params={
                    "q": STOCKS_QUERY,
                    "from": yesterday,
                    "sortBy": "relevancy",
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
        logger.error(f"Error fetching stocks news: {e}")

    return {
        "category": "stocks",
        "articles": articles,
        "tracked_tickers": TRACKED_TICKERS,
        "fetched_at": datetime.utcnow().isoformat(),
    }
