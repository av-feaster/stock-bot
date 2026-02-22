"""
Central configuration — edit this file to customise the bot.
All secrets are loaded from environment variables (never hard-code tokens).
"""

import os
from dotenv import load_dotenv

load_dotenv()   # reads .env file in project root

# ── Telegram ─────────────────────────────────────────────────────────────────
TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID: str        = os.getenv("TELEGRAM_CHAT_ID", "")

if not TELEGRAM_TOKEN:
    raise EnvironmentError("TELEGRAM_BOT_TOKEN is not set in .env")
if not CHAT_ID:
    raise EnvironmentError("TELEGRAM_CHAT_ID is not set in .env")

# When True, only run the daily scheduled report (no /start, /report, etc.).
# Use on Railway/Fly so one instance doesn't conflict with a local bot.
SCHEDULER_ONLY: bool = os.getenv("BOT_SCHEDULER_ONLY", "").lower() in ("1", "true", "yes")

# ── Schedule ──────────────────────────────────────────────────────────────────
# Tuple (hour, minute) in IST — bot will convert to UTC automatically
DAILY_REPORT_TIME_IST: tuple[int, int] = (9, 0)   # 09:00 AM IST

# ── Tracked stocks (NSE tickers) ─────────────────────────────────────────────
TRACKED_STOCKS: list[str] = [
    "RELIANCE",
    "TCS", 
    "HDFCBANK",
    "INFY",
    "ICICIBANK",
]

# ── Technical thresholds ─────────────────────────────────────────────────────
VOLUME_SPIKE_MULTIPLIER: float = 1.5   # ≥1.5× avg volume = spike
RSI_OVERSOLD: float            = 40
RSI_BULLISH_ZONE: float        = 50
RSI_OVERBOUGHT: float          = 70
EMA_SHORT: int                 = 20
EMA_LONG: int                  = 50
MACD_FAST: int                 = 12
MACD_SLOW: int                 = 26
MACD_SIGNAL: int               = 9
LOOKBACK_DAYS: int             = 120   # OHLCV history to fetch

# ── Data source ───────────────────────────────────────────────────────────────
# NSE indices (display name -> legacy id; data fetched via OpenChart)
INDICES: dict[str, str] = {
    "NIFTY 50":         "^NSEI",
    "NIFTY MIDCAP 150": "NIFTY_MID_SELECT.NS",
    "NIFTY SMALLCAP 250": "^CNXSC",
    "NIFTY BANK":       "^NSEBANK",
}

# ── News ──────────────────────────────────────────────────────────────────────
NEWS_MAX_PER_STOCK: int = 2    # headlines per stock
NEWS_SOURCES: list[str] = [
    "moneycontrol.com",
    "economictimes.indiatimes.com",
    "livemint.com",
]

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_FILE: str = "logs/bot.log"
# Set to 1/true to log every NSE HTTP request (URL + status) in bot.log / console
LOG_HTTP: bool = os.getenv("LOG_HTTP", "").lower() in ("1", "true", "yes")
