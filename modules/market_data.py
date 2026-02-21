"""
Market data fetcher.
Uses yfinance (free, no API key) for OHLCV and index data.
"""

import asyncio
import logging
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from config.settings import (
    INDICES,
    LOOKBACK_DAYS,
    YF_SUFFIX,
)

logger = logging.getLogger("MarketData")


class MarketDataFetcher:

    def _ticker(self, symbol: str) -> str:
        """Convert NSE symbol → yfinance ticker."""
        if symbol.startswith("^") or symbol.endswith(".NS"):
            return symbol
        return f"{symbol}{YF_SUFFIX}"

    async def get_ohlcv(self, symbol: str) -> pd.DataFrame:
        """Return OHLCV DataFrame for `symbol` over LOOKBACK_DAYS."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_ohlcv, symbol)

    def _fetch_ohlcv(self, symbol: str) -> pd.DataFrame:
        ticker = self._ticker(symbol)
        end   = datetime.today()
        start = end - timedelta(days=LOOKBACK_DAYS)
        try:
            df = yf.download(
                ticker,
                start=start.strftime("%Y-%m-%d"),
                end=end.strftime("%Y-%m-%d"),
                progress=False,
                auto_adjust=True,
            )
            if df.empty:
                logger.warning("No data for %s", symbol)
            # Flatten MultiIndex columns if present
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            df.index = pd.to_datetime(df.index)
            return df
        except Exception as e:
            logger.error("OHLCV fetch failed for %s: %s", symbol, e)
            return pd.DataFrame()

    async def get_index_summary(self) -> dict:
        """Return {index_name: {price, change_pct, trend}} for all tracked indices."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_indices)

    def _fetch_indices(self) -> dict:
        results = {}
        for name, ticker in INDICES.items():
            try:
                df = yf.download(
                    ticker,
                    period="5d",
                    progress=False,
                    auto_adjust=True,
                )
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                if df.empty or len(df) < 2:
                    results[name] = {"price": None, "change_pct": None}
                    continue
                close_today = float(df["Close"].iloc[-1])
                close_prev  = float(df["Close"].iloc[-2])
                change_pct  = ((close_today - close_prev) / close_prev) * 100
                results[name] = {
                    "price":      round(close_today, 2),
                    "change_pct": round(change_pct, 2),
                    "trend":      "▲" if change_pct >= 0 else "▼",
                }
            except Exception as e:
                logger.error("Index fetch failed for %s: %s", name, e)
                results[name] = {"price": None, "change_pct": None, "trend": "—"}
        return results
