"""
Technical analysis engine.
Computes RSI, MACD, EMAs, volume signals, and pattern labels.
Uses pandas/numpy only (no pandas-ta/numba) for broad Python compatibility.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd

from config.settings import (
    EMA_SHORT,
    EMA_LONG,
    MACD_FAST,
    MACD_SLOW,
    MACD_SIGNAL,
    RSI_BULLISH_ZONE,
    RSI_OVERBOUGHT,
    RSI_OVERSOLD,
    VOLUME_SPIKE_MULTIPLIER,
)

logger = logging.getLogger("Technical")


def _ema(series: pd.Series, length: int) -> pd.Series:
    """Exponential moving average."""
    return series.ewm(span=length, adjust=False).mean()


def _rsi(series: pd.Series, length: int = 14) -> pd.Series:
    """RSI (Wilder smoothing)."""
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = (-delta).clip(lower=0)
    avg_gain = gain.ewm(alpha=1 / length, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / length, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - (100 / (1 + rs))


def _macd(close: pd.Series, fast: int, slow: int, signal: int) -> tuple[pd.Series, pd.Series, pd.Series]:
    """MACD line, signal line, histogram. Returns (macd_line, signal_line, histogram)."""
    ema_fast = _ema(close, fast)
    ema_slow = _ema(close, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema(macd_line, signal)
    hist = macd_line - signal_line
    return macd_line, signal_line, hist


@dataclass
class StockSignal:
    ticker:           str
    cmp:              Optional[float] = None     # current price
    change_pct:       Optional[float] = None
    rsi:              Optional[float] = None
    macd_bullish:     bool            = False
    above_ema20:      bool            = False
    above_ema50:      bool            = False
    volume_spike:     bool            = False
    volume_ratio:     Optional[float] = None
    pattern:          str             = "No pattern"
    overall_signal:   str             = "NEUTRAL"  # STRONG BUY / BUY / WATCH / NEUTRAL / CAUTION
    entry_zone:       str             = "—"
    stop_loss:        str             = "—"
    st_target:        str             = "—"
    mt_target:        str             = "—"
    rr_ratio:         str             = "—"
    signal_emoji:     str             = "⚪"
    notes:            list            = field(default_factory=list)
    error:            Optional[str]   = None


# ── Hardcoded trade levels (updated weekly by analyst) ────────────────────────
TRADE_LEVELS: dict = {
    "NATCOPHARM": {
        "entry":    "₹845–880",
        "sl":       "₹720",
        "st_target":"₹940–960",
        "mt_target":"₹1,060–1,150",
        "rr":       "1:2.5",
        "pattern":  "Double Bottom",
    },
    "WELSPUNLIV": {
        "entry":    "₹132–140",
        "sl":       "₹118",
        "st_target":"₹155–160",
        "mt_target":"₹175–185",
        "rr":       "1:2.5",
        "pattern":  "Double Bottom + Gap Breakout",
    },
    "MCX": {
        "entry":    "₹8,400–8,700",
        "sl":       "₹7,900",
        "st_target":"₹9,200–9,500",
        "mt_target":"₹10,200–10,800",
        "rr":       "1:2.5",
        "pattern":  "Double Bottom + Marubozu",
    },
    "AUBANK": {
        "entry":    "₹990–1,020",
        "sl":       "₹960",
        "st_target":"₹1,060–1,090",
        "mt_target":"₹1,180–1,250",
        "rr":       "1:2.5",
        "pattern":  "Symmetrical Triangle Breakout",
    },
    "GRAPHITE": {
        "entry":    "₹430–480",
        "sl":       "₹390",
        "st_target":"₹550–590",
        "mt_target":"₹670–720",
        "rr":       "1:2.8",
        "pattern":  "Rounded Bottom",
    },
}


class TechnicalAnalyzer:

    def analyse(self, ticker: str, df: pd.DataFrame) -> StockSignal:
        sig = StockSignal(ticker=ticker)

        # Pull saved trade levels
        lvl = TRADE_LEVELS.get(ticker, {})
        sig.entry_zone = lvl.get("entry", "—")
        sig.stop_loss  = lvl.get("sl",    "—")
        sig.st_target  = lvl.get("st_target", "—")
        sig.mt_target  = lvl.get("mt_target", "—")
        sig.rr_ratio   = lvl.get("rr",    "—")
        sig.pattern    = lvl.get("pattern","—")

        if df.empty or len(df) < 1:
            sig.error = "Insufficient data"
            sig.overall_signal = "NO DATA"
            sig.signal_emoji   = "❓"
            return sig

        try:
            # Handle both single-row and multi-row DataFrames
            if len(df) == 1:
                close = df["Close"]
                volume = df["Volume"]
            else:
                close = df["Close"]
                volume = df["Volume"]

            # ── Price action ──────────────────────────────────────────────────
            sig.cmp = round(float(close.iloc[-1]), 2)
            
            # Only calculate change percentage if we have at least 2 data points
            if len(close) >= 2:
                sig.change_pct = round(
                    float((close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100), 2
                )

            # ── Technical indicators (only if we have enough data) ─────────────
            if len(close) >= 30:  # Only calculate indicators with sufficient data
                # ── RSI ───────────────────────────────────────────────────────
                rsi_series = _rsi(close, length=14)
                if rsi_series is not None and not rsi_series.empty:
                    last_rsi = rsi_series.iloc[-1]
                    if np.isfinite(last_rsi):
                        sig.rsi = round(float(last_rsi), 1)

                # ── MACD ──────────────────────────────────────────────────────
                macd_line, signal_line, _ = _macd(
                    close, fast=MACD_FAST, slow=MACD_SLOW, signal=MACD_SIGNAL
                )
                if macd_line is not None and len(macd_line) > 0:
                    m = float(macd_line.iloc[-1])
                    s = float(signal_line.iloc[-1])
                    if np.isfinite(m) and np.isfinite(s):
                        sig.macd_bullish = bool(m > s)

                # ── EMAs ──────────────────────────────────────────────────────
                ema20 = _ema(close, EMA_SHORT)
                ema50 = _ema(close, EMA_LONG)
                if ema20 is not None and len(ema20) > 0:
                    sig.above_ema20 = bool(close.iloc[-1] > ema20.iloc[-1])
                if ema50 is not None and len(ema50) > 0:
                    sig.above_ema50 = bool(close.iloc[-1] > ema50.iloc[-1])

                # ── Volume spike ──────────────────────────────────────────────
                if len(volume) >= 20:
                    avg_vol = float(volume.iloc[-20:].mean())
                    cur_vol = float(volume.iloc[-1])
                    sig.volume_ratio = round(cur_vol / avg_vol, 2) if avg_vol else None
                    sig.volume_spike = bool(
                        sig.volume_ratio and sig.volume_ratio >= VOLUME_SPIKE_MULTIPLIER
                    )
            else:
                # Not enough data for technical analysis - set basic signal based on price movement
                sig.notes.append("Limited data: Only current price available")

            # ── Composite signal ──────────────────────────────────────────────
            if len(close) >= 30:
                # Full technical analysis available
                bullish_count = sum([
                    sig.macd_bullish,
                    sig.above_ema20,
                    sig.above_ema50,
                    sig.volume_spike,
                    sig.rsi is not None and RSI_BULLISH_ZONE <= sig.rsi < RSI_OVERBOUGHT,
                ])

                if bullish_count >= 4:
                    sig.overall_signal = "STRONG BUY"
                    sig.signal_emoji   = "🟢"
                elif bullish_count == 3:
                    sig.overall_signal = "BUY"
                    sig.signal_emoji   = "🟢"
                elif bullish_count == 2:
                    sig.overall_signal = "WATCH"
                    sig.signal_emoji   = "🟡"
                elif bullish_count == 1:
                    sig.overall_signal = "NEUTRAL"
                    sig.signal_emoji   = "⚪"
                else:
                    sig.overall_signal = "CAUTION"
                    sig.signal_emoji   = "🔴"
            else:
                # Limited data - base signal on price movement only
                if sig.change_pct is not None:
                    if sig.change_pct > 2:
                        sig.overall_signal = "WATCH"
                        sig.signal_emoji   = "🟡"
                    elif sig.change_pct > 0:
                        sig.overall_signal = "NEUTRAL"
                        sig.signal_emoji   = "⚪"
                    elif sig.change_pct > -2:
                        sig.overall_signal = "NEUTRAL"
                        sig.signal_emoji   = "⚪"
                    else:
                        sig.overall_signal = "CAUTION"
                        sig.signal_emoji   = "🔴"
                else:
                    sig.overall_signal = "NEUTRAL"
                    sig.signal_emoji   = "⚪"

            # ── Notes ─────────────────────────────────────────────────────────
            if sig.rsi and sig.rsi < RSI_OVERSOLD:
                sig.notes.append("RSI oversold — potential bounce zone")
            if sig.rsi and sig.rsi > RSI_OVERBOUGHT:
                sig.notes.append("RSI overbought — partial profit booking advisable")
            if sig.volume_spike:
                sig.notes.append(f"Volume spike {sig.volume_ratio}× avg — institutional activity")
            if not sig.above_ema50 and sig.above_ema20:
                sig.notes.append("50 EMA reclaim attempt — key resistance")

        except Exception as e:
            logger.exception("Analysis error for %s: %s", ticker, e)
            sig.error = str(e)

        return sig
