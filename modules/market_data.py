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
        """Direct NSE API as primary source"""
        
        # Try NSE API first (primary)
        logger.info("Fetching data from NSE API for %s", symbol)
        try:
            nse_df = self.nse_fetcher.get_stock_data(symbol)
            if not nse_df.empty:
                logger.info("✅ Got data from NSE API for %s", symbol)
                return nse_df
        except Exception as e:
            logger.error("NSE API failed for %s: %s", symbol, e)
        
        # Fallback to yfinance (secondary)
        logger.warning("Falling back to yfinance for %s", symbol)
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
                timeout=10,
            )
            if not df.empty:
                # Flatten MultiIndex columns if present
                if isinstance(df.columns, pd.MultiIndex):
                    df.columns = df.columns.get_level_values(0)
                df.index = pd.to_datetime(df.index)
                logger.info("✅ Got data from yfinance for %s", symbol)
                return df
        except Exception as e:
            logger.error("yfinance fallback failed for %s: %s", symbol, e)
        
        return pd.DataFrame()

    async def get_index_summary(self) -> dict:
        """Return {index_name: {price, change_pct, trend}} for all tracked indices."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_indices)

    def _fetch_indices(self) -> dict:
        """Direct NSE API as primary source"""
        results = {}
        for name, ticker in INDICES.items():
            # Try NSE API first (primary)
            logger.info("Fetching index data from NSE API for %s", name)
            try:
                nse_data = self.nse_fetcher.get_index_data(ticker)
                if nse_data.get('price') is not None:
                    results[name] = nse_data
                    logger.info("✅ Got index data from NSE API for %s", name)
                    continue
            except Exception as e:
                logger.error("NSE index API failed for %s: %s", name, e)
            
            # Fallback to yfinance (secondary)
            logger.warning("Falling back to yfinance for %s", name)
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
                if not df.empty and len(df) >= 2:
                    close_today = float(df["Close"].iloc[-1])
                    close_prev  = float(df["Close"].iloc[-2])
                    change_pct  = ((close_today - close_prev) / close_prev) * 100
                    results[name] = {
                        "price":      round(close_today, 2),
                        "change_pct": round(change_pct, 2),
                        "trend":      "▲" if change_pct >= 0 else "▼",
                    }
                    logger.info("✅ Got index data from yfinance for %s", name)
                else:
                    results[name] = {"price": None, "change_pct": None, "trend": "—"}
            except Exception as e:
                logger.error("yfinance index fallback failed for %s: %s", name, e)
                results[name] = {"price": None, "change_pct": None, "trend": "—"}
        return results
