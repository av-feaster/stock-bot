"""
Technical analysis engine.
Computes RSI, MACD, EMAs, volume signals, and pattern labels.
"""

import logging
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
import pandas as pd
import pandas_ta as ta  # pip install pandas-ta

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

        if df.empty or len(df) < 30:
            sig.error = "Insufficient data"
            sig.overall_signal = "NO DATA"
            sig.signal_emoji   = "❓"
            return sig

        try:
            close  = df["Close"].squeeze()
            volume = df["Volume"].squeeze()

            # ── Price action ──────────────────────────────────────────────────
            sig.cmp        = round(float(close.iloc[-1]), 2)
            sig.change_pct = round(
                float((close.iloc[-1] - close.iloc[-2]) / close.iloc[-2] * 100), 2
            )

            # ── RSI ───────────────────────────────────────────────────────────
            rsi_series = ta.rsi(close, length=14)
            if rsi_series is not None and not rsi_series.empty:
                sig.rsi = round(float(rsi_series.iloc[-1]), 1)

            # ── MACD ──────────────────────────────────────────────────────────
            macd_df = ta.macd(
                close,
                fast=MACD_FAST, slow=MACD_SLOW, signal=MACD_SIGNAL
            )
            if macd_df is not None and not macd_df.empty:
                macd_line   = macd_df.iloc[-1, 0]  # MACD
                signal_line = macd_df.iloc[-1, 2]  # Signal
                sig.macd_bullish = bool(macd_line > signal_line)

            # ── EMAs ──────────────────────────────────────────────────────────
            ema20 = ta.ema(close, length=EMA_SHORT)
            ema50 = ta.ema(close, length=EMA_LONG)
            if ema20 is not None:
                sig.above_ema20 = bool(close.iloc[-1] > ema20.iloc[-1])
            if ema50 is not None:
                sig.above_ema50 = bool(close.iloc[-1] > ema50.iloc[-1])

            # ── Volume spike ──────────────────────────────────────────────────
            avg_vol = float(volume.iloc[-20:].mean())
            cur_vol = float(volume.iloc[-1])
            sig.volume_ratio = round(cur_vol / avg_vol, 2) if avg_vol else None
            sig.volume_spike = bool(
                sig.volume_ratio and sig.volume_ratio >= VOLUME_SPIKE_MULTIPLIER
            )

            # ── Composite signal ──────────────────────────────────────────────
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
