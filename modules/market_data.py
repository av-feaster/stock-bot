"""
Market data fetcher.
Uses yfinance (free, no API key) for OHLCV and index data.
Falls back to NSE API when yfinance fails.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta

import pandas as pd
import yfinance as yf

from config.settings import (
    INDICES,
    LOOKBACK_DAYS,
    YF_SUFFIX,
)
from modules.nse_data import NSEDataFetcher

logger = logging.getLogger("MarketData")


class MarketDataFetcher:
    def __init__(self):
        self.nse_fetcher = NSEDataFetcher()

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
        
        # Try yfinance first
        for attempt in range(2):  # Reduced attempts
            try:
                df = yf.download(
                    ticker,
                    start=start.strftime("%Y-%m-%d"),
                    end=end.strftime("%Y-%m-%d"),
                    progress=False,
                    auto_adjust=True,
                    timeout=10,
                )
                if df.empty:
                    logger.warning("No data for %s from yfinance (attempt %d)", symbol, attempt + 1)
                    if attempt < 1:
                        time.sleep(2)
                        continue
                # Flatten MultiIndex columns if present
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                df.index = pd.to_datetime(df.index)
                return df
            except Exception as e:
                logger.error("yfinance failed for %s (attempt %d): %s", symbol, attempt + 1, e)
                if attempt < 1:
                    time.sleep(2)
                    continue
        
        # Fallback to NSE API
        logger.info("Falling back to NSE API for %s", symbol)
        try:
            nse_df = self.nse_fetcher.get_stock_data(symbol)
            if not nse_df.empty:
                return nse_df
        except Exception as e:
            logger.error("NSE fallback failed for %s: %s", symbol, e)
        
        return pd.DataFrame()

    async def get_index_summary(self) -> dict:
        """Return {index_name: {price, change_pct, trend}} for all tracked indices."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_indices)

    def _fetch_indices(self) -> dict:
        results = {}
        for name, ticker in INDICES.items():
            # Try yfinance first
            try:
                df = yf.download(
                    ticker,
                    period="5d",
                    progress=False,
                    auto_adjust=True,
                    timeout=10,
                )
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                if df.empty or len(df) < 2:
                    logger.warning("No yfinance data for %s, trying NSE", name)
                    results[name] = self.nse_fetcher.get_index_data(ticker)
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
                logger.error("yfinance index failed for %s: %s, trying NSE", name, e)
                # Fallback to NSE
                results[name] = self.nse_fetcher.get_index_data(ticker)
        return results
