#!/usr/bin/env python3
"""
Indian Stock Market Daily Alert Bot — Telegram
Sends daily reversal signals, Nifty/SmallCap summary & news headlines.
"""

import asyncio
import logging
import os
from datetime import time as dtime

# Ensure runtime dirs exist before logging to file
os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)

from telegram import Bot
from telegram.ext import Application, CommandHandler, ContextTypes, JobQueue

from config.settings import (
    TELEGRAM_TOKEN,
    CHAT_ID,
    DAILY_REPORT_TIME_IST,
    TRACKED_STOCKS,
)
from modules.market_data import MarketDataFetcher
from modules.technical import TechnicalAnalyzer
from modules.news import NewsFetcher
from modules.formatter import MessageFormatter
from modules.health import HealthMonitor

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("logs/bot.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("StockBot")


# ──────────────────────────────────────────────
# Core report builder
# ──────────────────────────────────────────────

async def build_and_send_report(bot: Bot):
    """Fetch all data, analyse, format, send."""
    logger.info("📊 Starting daily report build...")

    fetcher  = MarketDataFetcher()
    analyzer = TechnicalAnalyzer()
    news_fetcher = NewsFetcher()
    formatter    = MessageFormatter()
    health       = HealthMonitor()

    try:
        # 1. Index summary
        indices = await fetcher.get_index_summary()

        # 2. Stock signals
        stock_signals = []
        for ticker in TRACKED_STOCKS:
            data   = await fetcher.get_ohlcv(ticker)
            signal = analyzer.analyse(ticker, data)
            stock_signals.append(signal)

        # 3. News headlines
        headlines = await news_fetcher.get_headlines(TRACKED_STOCKS)

        # 4. Format messages (split to avoid 4096-char Telegram limit)
        messages = formatter.build_report(indices, stock_signals, headlines)

        # 5. Send each part
        for msg in messages:
            await bot.send_message(
                chat_id=CHAT_ID,
                text=msg,
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )
            await asyncio.sleep(0.5)   # stay well within rate limits

        health.record_success()
        logger.info("✅ Daily report sent successfully.")

    except Exception as exc:
        logger.exception("❌ Report build failed: %s", exc)
        health.record_failure(str(exc))
        await bot.send_message(
            chat_id=CHAT_ID,
            text=f"⚠️ *StockBot Error*\n`{exc}`\nCheck server logs.",
            parse_mode="Markdown",
        )


# ──────────────────────────────────────────────
# Scheduled job (runs daily at configured IST time)
# ──────────────────────────────────────────────

async def scheduled_report(context: ContextTypes.DEFAULT_TYPE):
    await build_and_send_report(context.bot)


# ──────────────────────────────────────────────
# Command handlers
# ──────────────────────────────────────────────

async def cmd_start(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *StockBot is live!*\n\n"
        "Commands:\n"
        "/report — Instant full report\n"
        "/signal TICKER — Signal for one stock\n"
        "/watchlist — Show tracked stocks\n"
        "/status — Bot health status\n"
        "/help — This message",
        parse_mode="Markdown",
    )


async def cmd_report(update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Fetching data, please wait...")
    await build_and_send_report(context.bot)


async def cmd_signal(update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /signal NATCOPHARM")
        return
    ticker = args[0].upper()
    fetcher  = MarketDataFetcher()
    analyzer = TechnicalAnalyzer()
    formatter = MessageFormatter()
    data   = await fetcher.get_ohlcv(ticker)
    signal = analyzer.analyse(ticker, data)
    msg    = formatter.format_single_signal(signal)
    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_watchlist(update, context: ContextTypes.DEFAULT_TYPE):
    stocks = "\n".join(f"• `{s}`" for s in TRACKED_STOCKS)
    await update.message.reply_text(
        f"📋 *Tracked Stocks*\n\n{stocks}", parse_mode="Markdown"
    )


async def cmd_status(update, context: ContextTypes.DEFAULT_TYPE):
    health = HealthMonitor()
    status = health.get_status()
    await update.message.reply_text(status, parse_mode="Markdown")


# ──────────────────────────────────────────────
# App entry point
# ──────────────────────────────────────────────

def main():
    # Python 3.14+ may not set an event loop on the main thread
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())

    logger.info("🚀 StockBot starting...")

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Register command handlers
    app.add_handler(CommandHandler("start",     cmd_start))
    app.add_handler(CommandHandler("help",      cmd_start))
    app.add_handler(CommandHandler("report",    cmd_report))
    app.add_handler(CommandHandler("signal",    cmd_signal))
    app.add_handler(CommandHandler("watchlist", cmd_watchlist))
    app.add_handler(CommandHandler("status",    cmd_status))

    # Schedule daily report (IST = UTC+5:30)
    h, m = DAILY_REPORT_TIME_IST
    utc_h = (h - 5) % 24
    utc_m = (m - 30) % 60
    if m < 30:
        utc_h = (utc_h - 1) % 24

    job_queue: JobQueue = app.job_queue
    job_queue.run_daily(
        scheduled_report,
        time=dtime(hour=utc_h, minute=utc_m, second=0),
        name="daily_stock_report",
    )
    logger.info(
        f"⏰ Daily report scheduled at {h:02d}:{m:02d} IST "
        f"({utc_h:02d}:{utc_m:02d} UTC)"
    )

    logger.info("✅ Bot is polling. Press Ctrl+C to stop.")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
