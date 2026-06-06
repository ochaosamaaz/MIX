"""
AI/LLM module for news summarization and sentiment analysis.
Uses OpenAI-compatible API (works with OpenAI, Groq, Ollama, etc.)
"""

import logging
import json

from openai import AsyncOpenAI

from config import settings

logger = logging.getLogger(__name__)

# Initialize the client
client = AsyncOpenAI(
    api_key=settings.OPENAI_API_KEY,
    base_url=settings.OPENAI_BASE_URL,
)


async def summarize_news(articles: list[dict], category: str, language: str = "en") -> str:
    """
    Summarize a list of news articles into a concise market update.

    Args:
        articles: List of article dicts with 'title' and 'description'
        category: Market category (crypto, stocks, forex)
        language: 'en' for English, 'id' for Indonesian

    Returns:
        Formatted summary string
    """
    if not articles:
        if language == "id":
            return f"📭 Tidak ada berita {category} terbaru saat ini."
        return f"📭 No recent {category} news available at the moment."

    # Build article context
    news_context = "\n".join(
        f"- {a['title']}: {a.get('description', 'No description')}"
        for a in articles
    )

    lang_instruction = (
        "Respond in Bahasa Indonesia." if language == "id"
        else "Respond in English."
    )

    category_labels = {
        "crypto": "Cryptocurrency",
        "stocks": "US Stock Market",
        "forex": "Forex/Currency Market",
    }

    prompt = f"""You are a professional financial news analyst. Summarize the following {category_labels.get(category, category)} news into a brief, informative market update.

{lang_instruction}

Rules:
- Keep it concise (3-5 bullet points max)
- Highlight the most important market-moving events
- Use relevant emojis for readability
- End with a brief 1-sentence market outlook
- Format for Telegram (use markdown-compatible formatting)

News articles:
{news_context}
"""

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a concise financial news summarizer for a Telegram bot."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.4,
            max_tokens=500,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Error summarizing news: {e}")
        if language == "id":
            return "⚠️ Gagal membuat ringkasan. Silakan coba lagi nanti."
        return "⚠️ Failed to generate summary. Please try again later."


async def analyze_sentiment(articles: list[dict], category: str, language: str = "en") -> dict:
    """
    Analyze overall market sentiment from news articles.

    Args:
        articles: List of article dicts with 'title' and 'description'
        category: Market category (crypto, stocks, forex)
        language: 'en' for English, 'id' for Indonesian

    Returns:
        Dict with 'score' (-100 to 100), 'label', and 'analysis'
    """
    if not articles:
        return {
            "score": 0,
            "label": "Neutral" if language == "en" else "Netral",
            "analysis": (
                "Not enough data to analyze sentiment."
                if language == "en"
                else "Data tidak cukup untuk analisis sentimen."
            ),
        }

    news_context = "\n".join(
        f"- {a['title']}: {a.get('description', '')}"
        for a in articles
    )

    lang_instruction = (
        "Respond in Bahasa Indonesia." if language == "id"
        else "Respond in English."
    )

    prompt = f"""Analyze the overall market sentiment from these {category} news headlines and descriptions.

{lang_instruction}

Provide your response as JSON with these fields:
- "score": integer from -100 (extremely bearish) to 100 (extremely bullish)
- "label": one of "Very Bullish", "Bullish", "Neutral", "Bearish", "Very Bearish" (translate if Indonesian)
- "analysis": 2-3 sentence explanation of the sentiment with key drivers

News:
{news_context}

Respond ONLY with valid JSON, no markdown fences.
"""

    try:
        response = await client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": "You are a financial sentiment analyzer. Always respond with valid JSON only."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,
            max_tokens=300,
        )

        content = response.choices[0].message.content.strip()

        # Clean up possible markdown fences
        if content.startswith("```"):
            content = content.split("\n", 1)[1]
        if content.endswith("```"):
            content = content.rsplit("```", 1)[0]
        content = content.strip()

        result = json.loads(content)

        # Validate score range
        result["score"] = max(-100, min(100, int(result.get("score", 0))))

        return result

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse sentiment JSON: {e}")
        return {
            "score": 0,
            "label": "Unknown",
            "analysis": "Failed to analyze sentiment due to parsing error.",
        }
    except Exception as e:
        logger.error(f"Error analyzing sentiment: {e}")
        return {
            "score": 0,
            "label": "Error",
            "analysis": f"Sentiment analysis failed: {str(e)[:100]}",
        }


def get_sentiment_emoji(score: int) -> str:
    """Get emoji representation of sentiment score."""
    if score >= 60:
        return "🟢🚀"
    elif score >= 20:
        return "🟢"
    elif score >= -20:
        return "🟡"
    elif score >= -60:
        return "🔴"
    else:
        return "🔴💀"


def format_sentiment_message(sentiment: dict, category: str) -> str:
    """Format sentiment analysis into a Telegram message."""
    emoji = get_sentiment_emoji(sentiment["score"])
    category_labels = {
        "crypto": "🪙 Crypto",
        "stocks": "📈 US Stocks",
        "forex": "💱 Forex",
    }
    cat_label = category_labels.get(category, category.title())

    bar = create_sentiment_bar(sentiment["score"])

    return (
        f"{'─' * 20}\n"
        f"{cat_label} Sentiment {emoji}\n"
        f"{'─' * 20}\n"
        f"Score: {sentiment['score']}/100\n"
        f"{bar}\n"
        f"Label: {sentiment['label']}\n\n"
        f"📊 {sentiment['analysis']}\n"
    )


def create_sentiment_bar(score: int) -> str:
    """Create a visual sentiment bar."""
    # Normalize score from -100..100 to 0..10
    normalized = int((score + 100) / 20)
    normalized = max(0, min(10, normalized))
    filled = "█" * normalized
    empty = "░" * (10 - normalized)
    return f"[{filled}{empty}] {'Bearish' if score < 0 else 'Bullish'}"
