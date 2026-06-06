# 🤖 AI Market News Bot (Telegram)

An AI-powered Telegram bot that delivers real-time market news, summaries, and sentiment analysis for **Crypto**, **US Stocks**, and **Forex** markets.

## ✨ Features

- 📰 **News Aggregation** — Fetches latest market news from multiple sources
- 🧠 **AI Summarization** — Uses LLM to create concise, readable summaries
- 📊 **Sentiment Analysis** — Scores market sentiment (-100 to +100) with visual indicators
- 🪙 **Crypto Prices** — Live prices for BTC, ETH, SOL, XRP, ADA via CoinGecko
- ⏰ **Scheduled Updates** — Automatic morning (07:00) and evening (18:00) market briefings
- 🌐 **Bilingual** — Supports English and Bahasa Indonesia
- 🔔 **Subscribe/Unsubscribe** — Users can opt in/out of auto updates

## 📁 Project Structure

```
MIX/
├── bot.py                  # Main entry point
├── config/
│   ├── __init__.py
│   └── settings.py         # Environment config
├── fetchers/
│   ├── __init__.py
│   ├── crypto.py           # Crypto news + prices (CoinGecko + NewsAPI)
│   ├── stocks.py           # US stock market news (NewsAPI)
│   └── forex.py            # Forex news (NewsAPI)
├── ai/
│   ├── __init__.py
│   └── llm.py              # AI summarization & sentiment (OpenAI-compatible)
├── handlers/
│   ├── __init__.py
│   └── commands.py         # Telegram command handlers
├── scheduler/
│   ├── __init__.py
│   └── jobs.py             # Scheduled job management
├── .env.example            # Environment template
├── .gitignore
├── requirements.txt
└── README.md
```

## 🚀 Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/ochaosamaaz/MIX.git
cd MIX
```

### 2. Create virtual environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and fill in your API keys:

| Variable | Description | Where to get |
|----------|-------------|--------------|
| `TELEGRAM_BOT_TOKEN` | Telegram Bot token | [@BotFather](https://t.me/BotFather) |
| `OPENAI_API_KEY` | LLM API key | [OpenAI](https://platform.openai.com/api-keys) or [Groq](https://console.groq.com/) |
| `NEWSAPI_KEY` | News API key | [NewsAPI.org](https://newsapi.org/register) |

### 5. Run the bot

```bash
python bot.py
```

## 🤖 Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Welcome message & main menu |
| `/news` | Get latest market news (choose: Crypto/Stocks/Forex/All) |
| `/sentiment` | Market sentiment analysis with score |
| `/subscribe` | Subscribe to auto morning & evening updates |
| `/unsubscribe` | Unsubscribe from auto updates |
| `/lang` | Switch language (English / Indonesia) |
| `/help` | Show help message |

## ⚙️ Configuration

### Using a different LLM provider

This bot works with any OpenAI-compatible API. To use **Groq** (free & fast):

```env
OPENAI_API_KEY=your_groq_api_key
OPENAI_BASE_URL=https://api.groq.com/openai/v1
OPENAI_MODEL=llama-3.1-70b-versatile
```

To use **Ollama** (local):

```env
OPENAI_API_KEY=ollama
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_MODEL=llama3.1
```

### Schedule times

Edit in `.env` or `config/settings.py`:
- Morning update: 07:00 WIB (Asia/Jakarta)
- Evening update: 18:00 WIB (Asia/Jakarta)

## 📡 APIs Used

- [NewsAPI](https://newsapi.org/) — News aggregation for all markets
- [CoinGecko](https://www.coingecko.com/en/api) — Crypto price data (free tier)
- [OpenAI](https://platform.openai.com/) — AI summarization & sentiment (or compatible)

## 📝 Notes

- The bot uses in-memory storage for subscribers. For production, consider adding a database (SQLite/PostgreSQL).
- NewsAPI free tier has a limit of 100 requests/day and only supports news from the past 24 hours.
- CoinGecko free tier has rate limits (~10-30 calls/min).

## 📄 License

MIT
