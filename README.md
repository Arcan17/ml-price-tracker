# ML Price Tracker 🤖

![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)
![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?style=flat&logo=telegram&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED?style=flat&logo=docker&logoColor=white)
![CI](https://img.shields.io/github/actions/workflow/status/Arcan17/ml-price-tracker/ci.yml?label=CI&logo=github)
![License](https://img.shields.io/badge/license-MIT-green?style=flat)
![Status](https://img.shields.io/badge/status-active-brightgreen)

> **Never miss a price drop on MercadoLibre again.**

A Telegram bot that monitors product prices on **MercadoLibre Chile** and sends you an instant notification the moment the price drops to your target. Built with Python, async/await, and the official MercadoLibre public API — **no API key required** to start tracking.

**The problem it solves:** Manually checking product prices every day is tedious and easy to forget. ML Price Tracker does it automatically every 30 minutes and messages you only when it matters.

---

## How It Works

```
User                    Bot                   MercadoLibre API
 |                       |                          |
 |-- /buscar iphone 15 ->|                          |
 |                       |-- GET /sites/MLC/search->|
 |                       |<-- 5 results ------------|
 |<-- numbered list -----|                          |
 |                       |                          |
 |-- /seguir MLC123 850000 ->                       |
 |                       |-- GET /items/MLC123 ---->|
 |                       |<-- price: $900.000 ------|
 |<-- "Te aviso cuando baje de $850.000" ---------- |
 |                       |                          |
 |          [ every 30 min ]                        |
 |                       |-- GET /items/MLC123 ---->|
 |                       |<-- price: $820.000 ------|
 |<-- "🔔 ¡Bajó el precio! $820.000" ------------- |
```

---

## Bot Commands

```
/start          — Welcome message and quick intro
/buscar {query} — Search products on MercadoLibre Chile
/seguir {id or url} {price} — Create a price alert
/mis_alertas    — List your active alerts
/borrar {id}    — Delete an alert
/ayuda          — Show all commands with examples
```

### Demo

```
You: /buscar iphone 15

Bot: 🔍 Resultados para "iphone 15":

     1. iPhone 15 128GB Negro
        💰 $749.990
        🆔 MLC1234567890
        🔗 Ver en MercadoLibre

     2. iPhone 15 Pro 256GB Titanio
        💰 $1.099.990
        🆔 MLC9876543210
        🔗 Ver en MercadoLibre
     ...

You: /seguir MLC1234567890 700000

Bot: ✅ ¡Alerta creada!
     📦 iPhone 15 128GB Negro
     💰 Precio actual: $749.990
     🎯 Te aviso cuando baje de: $700.000
     Reviso los precios cada 30 minutos 🔄

[ 3 days later ]

Bot: 🔔 ¡Bajó el precio!
     📦 iPhone 15 128GB Negro
     💰 Precio actual: $689.990
     ✅ Tu objetivo era: $700.000
     🛒 Ver en MercadoLibre
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Bot framework | python-telegram-bot v20 (async) |
| HTTP client | httpx (async) |
| Database | SQLite via SQLAlchemy 2.0 |
| Scheduler | PTB built-in JobQueue (APScheduler) |
| Health check | FastAPI |
| Testing | pytest + respx (HTTP mocks) |
| Containerization | Docker + Docker Compose |
| CI/CD | GitHub Actions |

---

## Getting Started

### Option 1: Docker (recommended)

**Prerequisites:** Docker, Docker Compose, and a Telegram bot token.

```bash
git clone https://github.com/Arcan17/ml-price-tracker.git
cd ml-price-tracker

# Create your .env file
cp .env.example .env
# Edit .env and set TELEGRAM_BOT_TOKEN=your_token_here

docker-compose up --build
```

The bot starts immediately and the health check is at `http://localhost:8080/health`.

### Option 2: Local Development

**Prerequisites:** Python 3.11+

```bash
git clone https://github.com/Arcan17/ml-price-tracker.git
cd ml-price-tracker

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and set TELEGRAM_BOT_TOKEN=your_token_here

# Start the bot
python main.py
```

### Getting a Telegram Bot Token

1. Open Telegram and search for **@BotFather**
2. Send `/newbot` and follow the instructions
3. Copy the token and paste it in your `.env` file

---

## Running Tests

Tests use **respx** to mock all MercadoLibre API calls — no real HTTP requests, no token needed.

```bash
pytest tests/ -v
```

Expected output:

```
tests/test_mercadolibre.py::test_search_products_returns_results PASSED
tests/test_mercadolibre.py::test_get_item_returns_item PASSED
tests/test_mercadolibre.py::test_get_item_returns_none_on_404 PASSED
...
tests/test_alerts.py::test_alert_triggered_when_price_drops PASSED
tests/test_alerts.py::test_alert_not_triggered_when_price_above PASSED
tests/test_alerts.py::test_alert_deactivated_when_product_removed PASSED
...
17 passed in X.XXs
```

---

## Project Structure

```
ml-price-tracker/
├── bot/
│   ├── handlers.py        # Telegram command handlers
│   └── messages.py        # All bot text (Chilean Spanish)
├── services/
│   ├── mercadolibre.py    # MercadoLibre API client
│   └── alerts.py          # Price checking & notification logic
├── models/
│   └── database.py        # SQLAlchemy models (User, Alert)
├── api/
│   └── main.py            # FastAPI health check endpoint
├── tests/
│   ├── conftest.py        # Shared test fixtures
│   ├── test_mercadolibre.py
│   └── test_alerts.py
├── main.py                # Entry point
├── Dockerfile
└── docker-compose.yml
```

---

## Data Model

```
User
├── id
├── telegram_id  (unique)
├── username
└── created_at

Alert
├── id
├── user_id      → User.id
├── item_id      (e.g. MLC1234567890)
├── item_name
├── item_url
├── target_price
├── current_price
├── is_active
├── created_at
└── triggered_at
```

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| `TELEGRAM_BOT_TOKEN` | Your bot token from @BotFather | — |
| `DATABASE_URL` | SQLAlchemy connection string | `sqlite:///./data/bot.db` |

---

## Roadmap

- [ ] Support MercadoLibre Argentina and Mexico (MLA, MLM)
- [ ] `/historial {id}` command to show price history chart
- [ ] Web dashboard to manage alerts from browser
- [ ] Deploy public instance (Railway + persistent DB)
- [ ] Price drop percentage alerts (e.g. "alert me when it drops 15%")
- [ ] Multi-language support (English)

---

## License

MIT
