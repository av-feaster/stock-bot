"""
Message formatter.
Builds Telegram Markdown messages from signal objects.
Automatically chunks output to stay under Telegram's 4096-char limit.
"""

from datetime import datetime
from typing import Optional

from modules.technical import StockSignal

MAX_MSG_LEN = 4000   # safe margin under 4096


class MessageFormatter:

    # ── Public API ────────────────────────────────────────────────────────────

    def build_report(
        self,
        indices: dict,
        signals: list[StockSignal],
        news: dict[str, list[dict]],
    ) -> list[str]:
        """Returns list of Telegram-ready message strings."""
        parts = []
        parts.append(self._header())
        parts.append(self._index_block(indices))
        for sig in signals:
            parts.append(self._signal_block(sig))
            parts.append(self._news_block(sig.ticker, news.get(sig.ticker, [])))
        parts.append(self._footer())

        return self._chunk(parts)

    def format_single_signal(self, sig: StockSignal) -> str:
        return self._signal_block(sig)

    # ── Private builders ──────────────────────────────────────────────────────

    def _header(self) -> str:
        now = datetime.now().strftime("%d %b %Y • %I:%M %p IST")
        return (
            "━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "📊 *DAILY STOCK ALERT REPORT*\n"
            f"🗓 _{now}_\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

    def _index_block(self, indices: dict) -> str:
        lines = ["", "📈 *INDEX SUMMARY*", ""]
        for name, data in indices.items():
            if data.get("price") is None:
                lines.append(f"• {name}: _data unavailable_")
                continue
            price      = f"{data['price']:,.2f}"
            change_pct = data["change_pct"]
            trend      = data["trend"]
            emoji      = "🟢" if change_pct >= 0 else "🔴"
            lines.append(
                f"{emoji} *{name}*: `{price}` {trend} `{change_pct:+.2f}%`"
            )
        lines.append("")
        return "\n".join(lines)

    def _signal_block(self, sig: StockSignal) -> str:
        if sig.error:
            return (
                f"\n⚠️ *{sig.ticker}* — data error\n"
                f"`{sig.error}`\n"
            )

        chg_str = f"{sig.change_pct:+.2f}%" if sig.change_pct is not None else "—"
        rsi_str = str(sig.rsi) if sig.rsi else "—"
        vol_str = f"{sig.volume_ratio:.2f}×" if sig.volume_ratio else "—"

        # Indicator pill row
        def pill(flag: bool, label: str) -> str:
            return f"✅ {label}" if flag else f"❌ {label}"

        indicators = "  ".join([
            pill(sig.macd_bullish, "MACD"),
            pill(sig.above_ema20,  "EMA20"),
            pill(sig.above_ema50,  "EMA50"),
            pill(sig.volume_spike, "Vol↑"),
        ])

        # Notes
        notes_str = ""
        if sig.notes:
            notes_str = "\n💬 " + "\n💬 ".join(sig.notes)

        block = (
            f"\n{'─'*26}\n"
            f"{sig.signal_emoji} *{sig.ticker}* — {sig.overall_signal}\n"
            f"💰 CMP: `₹{sig.cmp:,}` ({chg_str})\n"
            f"📐 Pattern: _{sig.pattern}_\n"
            f"\n"
            f"*Indicators*\n"
            f"{indicators}\n"
            f"📉 RSI: `{rsi_str}` | 📦 Volume: `{vol_str}`\n"
            f"\n"
            f"*Trade Levels*\n"
            f"🎯 Entry:    `{sig.entry_zone}`\n"
            f"🛑 Stop Loss: `{sig.stop_loss}`\n"
            f"📌 ST Target: `{sig.st_target}`\n"
            f"🏁 MT Target: `{sig.mt_target}`\n"
            f"⚖️ R:R Ratio: `{sig.rr_ratio}`"
        )

        if notes_str:
            block += f"\n{notes_str}"

        return block

    def _news_block(self, ticker: str, items: list[dict]) -> str:
        if not items:
            return f"\n📰 *{ticker} News*: _No recent headlines_\n"
        lines = [f"\n📰 *{ticker} News*"]
        for item in items:
            title = item["title"][:80] + ("…" if len(item["title"]) > 80 else "")
            url   = item.get("url", "#")
            lines.append(f"• [{title}]({url})")
        return "\n".join(lines) + "\n"

    def _footer(self) -> str:
        return (
            "\n━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
            "⚠️ _For educational purposes only._\n"
            "_Not SEBI-registered advice._\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━"
        )

    # ── Chunker ───────────────────────────────────────────────────────────────

    def _chunk(self, parts: list[str]) -> list[str]:
        """Combine parts into messages ≤ MAX_MSG_LEN chars."""
        messages = []
        current  = ""
        for part in parts:
            if len(current) + len(part) + 1 > MAX_MSG_LEN:
                if current:
                    messages.append(current.strip())
                current = part
            else:
                current += ("\n" if current else "") + part
        if current.strip():
            messages.append(current.strip())
        return messages if messages else ["No data to display."]
