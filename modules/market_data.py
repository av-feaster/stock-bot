"""
Market data fetcher — NSE only (OpenChart).
Fetches OHLCV and index data from NSE India; no Yahoo/API key.
"""

import asyncio
import logging

import pandas as pd

from config.settings import INDICES
from modules.nse_data import NSEDataFetcher

logger = logging.getLogger("MarketData")


class MarketDataFetcher:
    def __init__(self):
        self.nse_fetcher = NSEDataFetcher()

    async def get_ohlcv(self, symbol: str) -> pd.DataFrame:
        """Return OHLCV DataFrame for `symbol` over LOOKBACK_DAYS."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.nse_fetcher.get_stock_data, symbol)

    async def get_index_summary(self) -> dict:
        """Return {index_name: {price, change_pct, trend}} for all tracked indices."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_indices)

    def _fetch_indices(self) -> dict:
        results = {}
        for name, yf_ticker in INDICES.items():
            try:
                nse_data = self.nse_fetcher.get_index_data(name, yf_ticker)
                results[name] = nse_data
                if nse_data.get("price") is not None:
                    logger.info("✅ Got index data from NSE for %s", name)
            except Exception as e:
                logger.error("NSE index failed for %s: %s", name, e)
                results[name] = {"price": None, "change_pct": None, "trend": "—"}
        return results
