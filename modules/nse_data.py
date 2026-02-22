"""
NSE data via OpenChart — historical OHLCV and index data.
No API key; uses NSE's public chart APIs.
"""

import logging
from datetime import datetime, timedelta
from typing import Any

import pandas as pd

from config.settings import LOOKBACK_DAYS

logger = logging.getLogger("NSEData")

# Actual APIs hit by OpenChart (for logging)
NSE_API_HISTORICAL = "POST https://charting.nseindia.com/v1/charts/symbolHistoricalData"
NSE_API_SESSION = "GET https://www.nseindia.com (session init)"

# OpenChart index symbol (segment IDX) for each display name
# Keys match INDICES keys in settings; values are OpenChart symbol names
NSE_INDEX_SYMBOLS: dict[str, str] = {
    "NIFTY 50": "NIFTY 50",
    "NIFTY BANK": "NIFTY BANK",
    "NIFTY MIDCAP 150": "NIFTY MIDCAP 150",
    "NIFTY SMALLCAP 250": "NIFTY SMALLCAP 250",
}


class NSEDataFetcher:
    def __init__(self):
        try:
            from openchart import NSEData
            self._client = NSEData()
        except ImportError:
            self._client = None
            logger.warning("openchart not installed; NSE data unavailable")

    def _eq_symbol(self, symbol: str) -> str:
        """NSE equity symbol for OpenChart (e.g. RELIANCE -> RELIANCE-EQ)."""
        s = symbol.strip().upper()
        if s.endswith("-EQ"):
            return s
        return f"{s}-EQ"

    def get_stock_data(self, symbol: str) -> pd.DataFrame:
        """Historical OHLCV for the given NSE equity over LOOKBACK_DAYS."""
        if self._client is None:
            logger.warning("NSE API: client not available (openchart not installed)")
            return pd.DataFrame()
        eq = self._eq_symbol(symbol)
        end = datetime.now()
        start = end - timedelta(days=LOOKBACK_DAYS)
        logger.info(
            "NSE API request: %s | symbol=%s segment=EQ from=%s to=%s",
            NSE_API_HISTORICAL, eq, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"),
        )
        try:
            df = self._client.historical(eq, "EQ", start, end, "1d")
            if df is None or df.empty:
                logger.warning("NSE API response: %s | symbol=%s -> no data (empty)", NSE_API_HISTORICAL, eq)
                return pd.DataFrame()
            # OpenChart returns Open, High, Low, Close, Volume (capitalised)
            df.index = pd.to_datetime(df.index)
            df = df.sort_index()
            # Normalise column names to match what technical.py expects
            cols = {c: c.strip() for c in df.columns}
            df = df.rename(columns=cols)
            if "Volume" not in df.columns:
                df["Volume"] = 0
            out = df[["Open", "High", "Low", "Close", "Volume"]].copy()
            logger.info("NSE API response: %s | symbol=%s -> %d rows", NSE_API_HISTORICAL, eq, len(out))
            return out
        except Exception as e:
            logger.error(
                "NSE API response: %s | symbol=%s -> error: %s",
                NSE_API_HISTORICAL, eq, e,
                exc_info=True,
            )
            return pd.DataFrame()

    def get_index_data(self, index_display_name: str, yf_ticker: str) -> dict[str, Any]:
        """
        Return {price, change_pct, trend} for the given index.
        index_display_name: key from INDICES (e.g. 'NIFTY 50').
        yf_ticker: unused; kept for API compatibility.
        """
        if self._client is None:
            logger.warning("NSE API: client not available for index %s", index_display_name)
            return {"price": None, "change_pct": None, "trend": "—"}
        nse_symbol = NSE_INDEX_SYMBOLS.get(index_display_name)
        if not nse_symbol:
            logger.warning("NSE API: no symbol mapping for index %s", index_display_name)
            return {"price": None, "change_pct": None, "trend": "—"}
        end = datetime.now()
        start = end - timedelta(days=15)
        logger.info(
            "NSE API request: %s | symbol=%s segment=IDX from=%s to=%s",
            NSE_API_HISTORICAL, nse_symbol, start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"),
        )
        try:
            df = self._client.historical(nse_symbol, "IDX", start, end, "1d")
            if df is None or len(df) < 2:
                logger.warning(
                    "NSE API response: %s | index=%s -> no data (empty or < 2 rows)",
                    NSE_API_HISTORICAL, index_display_name,
                )
                return {"price": None, "change_pct": None, "trend": "—"}
            df.index = pd.to_datetime(df.index)
            df = df.sort_index()
            close = df["Close"] if "Close" in df.columns else df["close"]
            close_today = float(close.iloc[-1])
            close_prev = float(close.iloc[-2])
            change_pct = ((close_today - close_prev) / close_prev) * 100
            logger.info(
                "NSE API response: %s | index=%s -> %d rows, price=%.2f",
                NSE_API_HISTORICAL, index_display_name, len(df), close_today,
            )
            return {
                "price": round(close_today, 2),
                "change_pct": round(change_pct, 2),
                "trend": "▲" if change_pct >= 0 else "▼",
            }
        except Exception as e:
            logger.error(
                "NSE API response: %s | index=%s -> error: %s",
                NSE_API_HISTORICAL, index_display_name, e,
                exc_info=True,
            )
            return {"price": None, "change_pct": None, "trend": "—"}
