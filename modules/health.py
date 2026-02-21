"""
Simple health monitor — tracks last run status, errors, and uptime.
Persists state to data/health.json.
"""

import json
import logging
import os
from datetime import datetime

HEALTH_FILE = "data/health.json"
logger = logging.getLogger("Health")


class HealthMonitor:

    def __init__(self):
        os.makedirs("data", exist_ok=True)
        self._state = self._load()

    def _load(self) -> dict:
        if os.path.exists(HEALTH_FILE):
            try:
                with open(HEALTH_FILE) as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "total_runs":     0,
            "successes":      0,
            "failures":       0,
            "last_run":       None,
            "last_status":    "Never run",
            "last_error":     None,
            "start_time":     datetime.utcnow().isoformat(),
        }

    def _save(self):
        with open(HEALTH_FILE, "w") as f:
            json.dump(self._state, f, indent=2)

    def record_success(self):
        self._state["total_runs"]  += 1
        self._state["successes"]   += 1
        self._state["last_run"]    = datetime.utcnow().isoformat()
        self._state["last_status"] = "✅ Success"
        self._state["last_error"]  = None
        self._save()

    def record_failure(self, error: str):
        self._state["total_runs"] += 1
        self._state["failures"]   += 1
        self._state["last_run"]   = datetime.utcnow().isoformat()
        self._state["last_status"] = "❌ Failed"
        self._state["last_error"]  = error
        self._save()

    def get_status(self) -> str:
        s = self._state
        uptime_since = s.get("start_time", "—")
        return (
            "🤖 *StockBot Health Status*\n\n"
            f"🟢 Last Status:  `{s['last_status']}`\n"
            f"📅 Last Run:     `{s['last_run'] or 'Never'}`\n"
            f"✅ Successes:    `{s['successes']}`\n"
            f"❌ Failures:     `{s['failures']}`\n"
            f"🔄 Total Runs:   `{s['total_runs']}`\n"
            f"⏱ Running Since: `{uptime_since}`\n"
            + (f"⚠️ Last Error:   `{s['last_error']}`" if s['last_error'] else "")
        )
