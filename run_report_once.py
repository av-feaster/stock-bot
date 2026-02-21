#!/usr/bin/env python3
"""
Run the daily report once and exit. Use for cron, GitHub Actions, or scheduled jobs
so you don't need a 24/7 server. No Telegram commands (/start, /report, etc.) — only
sends the one scheduled report.
"""
import asyncio
import os
import sys

# Ensure runtime dirs exist before bot module touches logs/
os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)

from telegram import Bot
from config.settings import TELEGRAM_TOKEN
from bot import build_and_send_report


async def main():
    bot = Bot(TELEGRAM_TOKEN)
    await build_and_send_report(bot)


if __name__ == "__main__":
    sys.exit(asyncio.run(main()) or 0)
