#!/usr/bin/env python3
"""
Test NSE APIs (same flow as /report) and optionally send result to Telegram.
Run: python test_nse_telegram.py
"""
import asyncio
import os
import sys

os.makedirs("logs", exist_ok=True)
os.makedirs("data", exist_ok=True)

from config.settings import CHAT_ID, TRACKED_STOCKS
from modules.market_data import MarketDataFetcher
from modules.technical import TechnicalAnalyzer
from config.settings import TELEGRAM_TOKEN


async def main():
    fetcher = MarketDataFetcher()
    analyzer = TechnicalAnalyzer()

    lines = ["🔬 *NSE API test* (same flow as /report)\n"]

    # 1. Indices
    lines.append("*Indices (NSE)*")
    try:
        indices = await fetcher.get_index_summary()
        for name, data in indices.items():
            p = data.get("price")
            if p is not None:
                ch = data.get("change_pct", 0)
                tr = data.get("trend", "—")
                lines.append(f"  ✅ {name}: {p:,.2f} {tr} {ch:+.2f}%")
            else:
                lines.append(f"  ❌ {name}: no data")
    except Exception as e:
        lines.append(f"  ❌ Error: {e}")

    # 2. One stock OHLCV + signal
    ticker = TRACKED_STOCKS[0] if TRACKED_STOCKS else "RELIANCE"
    lines.append(f"\n*Stock: {ticker} (NSE)*")
    try:
        df = await fetcher.get_ohlcv(ticker)
        if df.empty or len(df) < 30:
            lines.append(f"  ❌ OHLCV: no data or < 30 rows ({len(df)} rows)")
        else:
            lines.append(f"  ✅ OHLCV: {len(df)} rows")
            sig = analyzer.analyse(ticker, df)
            if sig.error:
                lines.append(f"  ⚠️ Signal: {sig.error}")
            else:
                lines.append(f"  ✅ CMP ₹{sig.cmp:,} | RSI {sig.rsi} | {sig.overall_signal}")
    except Exception as e:
        lines.append(f"  ❌ Error: {e}")

    lines.append("\n_Test run. Use /report for full report._")
    msg = "\n".join(lines)

    # Always print to console
    print("--- NSE API test result ---")
    print(msg)
    print("----------------------------")

    # Send to Telegram only if CHAT_ID looks valid (numeric)
    chat_id = (CHAT_ID or "").strip()
    if chat_id.isdigit() or (chat_id.startswith("-") and chat_id[1:].isdigit()):
        try:
            from telegram import Bot
            bot = Bot(TELEGRAM_TOKEN)
            await bot.send_message(
                chat_id=CHAT_ID,
                text=msg,
                parse_mode="Markdown",
            )
            print("✅ Sent to Telegram.")
        except Exception as e:
            print(f"⚠️ Telegram send failed: {e}")
    else:
        print("⚠️ TELEGRAM_CHAT_ID not set or invalid; result not sent. Get ID from @userinfobot.")


if __name__ == "__main__":
    asyncio.run(main())
    sys.exit(0)
