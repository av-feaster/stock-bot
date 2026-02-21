# 📊 Indian Stock Market — Telegram Alert Bot

A fully self-hosted Telegram bot that sends **daily technical reversal signals**, **Nifty/SmallCap index summaries**, and **news headlines** for tracked NSE stocks — every morning at 9:00 AM IST.

---

## 🏗️ Project Structure

```
stock_bot/
├── bot.py                  # Main entry point & command handlers
├── run_report_once.py      # One-off report (cron / GitHub Actions)
├── config/
│   └── settings.py         # All config (stocks, thresholds, schedule)
├── modules/
│   ├── market_data.py      # OHLCV + index data (yfinance)
│   ├── technical.py        # RSI, MACD, EMA, volume, pattern analysis
│   ├── news.py             # RSS news headlines (Google News)
│   ├── formatter.py        # Telegram Markdown message builder
│   └── health.py           # Bot health tracking
├── data/                   # Runtime state (health.json)
├── logs/                   # bot.log
├── .env.example            # Environment variable template
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── railway.json            # Railway deploy config (Dockerfile + restart policy)
├── fly.toml                # Fly.io worker config (no HTTP)
├── .github/workflows/
│   └── daily-report.yml    # GitHub Actions: daily report at 9 AM IST
└── stockbot.service        # Systemd service file
```

---

## ⚡ Quick Start (5 minutes)

### Step 1 — Create your Telegram Bot

1. Open Telegram → search `@BotFather`
2. Send `/newbot` → follow prompts → copy the **bot token**
3. Open `@userinfobot` → send `/start` → copy your **numeric chat ID**

### Step 2 — Clone & configure

```bash
git clone <your-repo-url>
cd stock_bot

# Install dependencies (use a virtualenv)
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure secrets
cp .env.example .env
nano .env   # paste your token and chat ID
```

**.env file:**
```
TELEGRAM_BOT_TOKEN=7123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TELEGRAM_CHAT_ID=987654321
```

### Step 3 — Run

```bash
python bot.py
```

Open Telegram → find your bot → send `/start`

---

## 📱 Bot Commands

| Command | Description |
|---|---|
| `/start` or `/help` | Show all commands |
| `/report` | Trigger an instant full report right now |
| `/signal TICKER` | Get signal for a single stock (e.g. `/signal MCX`) |
| `/watchlist` | Show all tracked stocks |
| `/status` | Bot health — uptime, last run, errors |

---

## 🕘 Daily Report — Sample Output

```
━━━━━━━━━━━━━━━━━━━━━━━━━━
📊 DAILY STOCK ALERT REPORT
🗓 21 Feb 2026 • 09:00 AM IST
━━━━━━━━━━━━━━━━━━━━━━━━━━

📈 INDEX SUMMARY

🟢 NIFTY 50:          23,450.20  ▲ +0.42%
🟢 NIFTY MIDCAP 150:  12,840.50  ▲ +0.61%
🟢 NIFTY SMALLCAP 250: 8,910.30  ▲ +0.73%
🔴 NIFTY BANK:        49,210.00  ▼ -0.18%

──────────────────────────
🟢 NATCOPHARM — STRONG BUY
💰 CMP: ₹871 (+1.2%)
📐 Pattern: Double Bottom

Indicators
✅ MACD  ✅ EMA20  ❌ EMA50  ✅ Vol↑
📉 RSI: 53.4 | 📦 Volume: 1.72×

Trade Levels
🎯 Entry:     ₹845–880
🛑 Stop Loss:  ₹720
📌 ST Target:  ₹940–960
🏁 MT Target:  ₹1,060–1,150
⚖️ R:R Ratio:  1:2.5
💬 Volume spike 1.72× avg — institutional activity

📰 NATCOPHARM News
• Natco Pharma Q3 profit rises 14%, eyes US launches
• Natco gets USFDA nod for generic Revlimid
```

---

## ⚙️ Customisation

### Add / remove stocks

Edit `config/settings.py`:

```python
TRACKED_STOCKS = [
    "NATCOPHARM",
    "WELSPUNLIV",
    "MCX",
    "AUBANK",
    "GRAPHITE",
    "INFY",        # ← add any NSE ticker
]
```

Also add trade levels in `modules/technical.py` → `TRADE_LEVELS` dict.

### Change report time

```python
DAILY_REPORT_TIME_IST = (8, 30)   # 8:30 AM IST
```

### Add multiple chat IDs (group / channel)

In `bot.py` → `build_and_send_report()`, loop over a list of chat IDs:

```python
for chat_id in [CHAT_ID, "-100123456789"]:    # group ID starts with -100
    await bot.send_message(chat_id=chat_id, ...)
```

---

## 🚀 Production Deployment

### Option A — Systemd (VPS/bare metal)

```bash
# Edit stockbot.service with your paths, then:
sudo cp stockbot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable stockbot
sudo systemctl start stockbot

# View logs
sudo journalctl -u stockbot -f
```

### Option B — Docker (recommended)

```bash
docker compose up -d

# View logs
docker compose logs -f
```

### Option C — Railway

1. Push your repo to GitHub (ensure `.env` is not committed).
2. Go to [railway.app](https://railway.app) → **Start a New Project** → **Deploy from GitHub repo** → select this repo.
3. Railway will detect the **Dockerfile** and build from it. No extra config needed if `railway.json` is in the repo.
4. In the service → **Variables**, add:
   - `TELEGRAM_BOT_TOKEN` = your bot token from @BotFather  
   - `TELEGRAM_CHAT_ID` = your numeric chat ID from @userinfobot  
5. Deploy. The bot runs as a long-lived worker (no port needed). Check **Deployments** → **View Logs** for output.

**Note:** Railway gives ~$5/month free credit. The bot is a worker process and will restart automatically on failure (`restartPolicyType: ALWAYS` in `railway.json`).

### Deploy for free

| Option | What you get | Trade-off |
|--------|----------------|-----------|
| **GitHub Actions** | Daily report at 9 AM IST, no server | No Telegram commands (/start, /report, etc.); report-only. |
| **Oracle Cloud** | Always-free VPS, full bot 24/7 | One-time signup; deploy with Docker or systemd. |
| **Fly.io** | Free allowance, full bot 24/7 | ~3 small VMs free; set secrets and deploy. |
| **Railway** | ~$5/mo credit | Free for a while; then paid. |

**Option 1 — GitHub Actions (zero infra)**  
- Push the repo to GitHub.  
- **Settings → Secrets and variables → Actions** → add `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`.  
- The workflow in `.github/workflows/daily-report.yml` runs at **9:00 AM IST** and sends one report.  
- You can also run it manually: **Actions** → **Daily stock report** → **Run workflow**.  
- No server, no cost. You only get the scheduled report (no /report or /signal from Telegram unless you run the full bot elsewhere).

**Option 2 — Oracle Cloud (always-free VPS)**  
- Create an always-free VM (e.g. Ubuntu) at [Oracle Cloud](https://www.oracle.com/cloud/free/).  
- SSH in, clone the repo, set `.env`, then run with **Docker** (`docker compose up -d`) or **systemd** (see Option A above).  
- Full bot 24/7 with all commands.

**Option 3 — Fly.io (free tier)**  
- Install [flyctl](https://fly.io/docs/hands-on/install-flyctl/) and run `fly launch` in the repo (use existing `fly.toml`).  
- Set secrets: `fly secrets set TELEGRAM_BOT_TOKEN=xxx TELEGRAM_CHAT_ID=xxx`  
- `fly deploy` — bot runs as a worker (no HTTP). Full bot 24/7 within free allowance.

### Recommended free/cheap hosting

| Platform | Free Tier | Notes |
|---|---|---|
| **GitHub Actions** | Free (scheduled job) | Report-only; no 24/7 bot. |
| **Oracle Cloud** | Always free 4 OCPUs / 24GB | Best free VPS for full bot. |
| **Fly.io** | 3 shared VMs free | Full bot; use `fly.toml` in repo. |
| **Railway.app** | $5/mo free credit | Easy Docker deploy. |
| **Render.com** | Free (sleeps) | Use with keep-alive or cron + `run_report_once.py`. |
| **Hetzner CX11** | ~€3.29/mo | Best paid value. |

---

## 🔒 Security Notes

- Never commit `.env` to Git — it's in `.gitignore`
- Rotate your bot token via `@BotFather` if compromised
- For group chats, verify the bot only responds to your user ID

---

## 📦 Dependencies

| Package | Purpose |
|---|---|
| `python-telegram-bot` | Telegram Bot API + job queue |
| `yfinance` | Free NSE/BSE OHLCV & index data |
| `pandas-ta` | RSI, MACD, EMA calculations |
| `feedparser` | RSS news parsing |
| `python-dotenv` | Environment variable management |

---

## 🛠️ Troubleshooting

**Bot not sending messages?**
→ Check `logs/bot.log` for errors
→ Verify `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`

**No market data?**
→ NSE data via yfinance sometimes has delays. Try `/report` after 9:15 AM IST (market open).

**News not loading?**
→ Google News RSS can throttle requests. This is non-critical; bot will show "No recent headlines."

---

## ⚠️ Disclaimer

This bot is for **educational and informational purposes only**. It does not constitute SEBI-registered investment advice. Always consult a qualified financial advisor before trading.
