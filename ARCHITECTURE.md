# Architecture — ML Price Tracker

## Overview

ML Price Tracker is a production-ready Telegram bot that monitors product prices on MercadoLibre Chile and notifies users when prices drop to their target threshold. The bot uses a **producer-consumer** architecture with async event loops for concurrent API calls and database operations.

```
┌─────────────────┐
│  Telegram User  │
└────────┬────────┘
         │
    [Telegram API]
         │
    ┌────▼────────────────────────────────────────┐
    │     Telegram Bot Application                │
    │  (CommandHandler + JobQueue + CallbackQry)  │
    └──┬────────────────────────────┬────────────┘
       │                            │
  ┌────▼──────────────┐      ┌─────▼──────────────┐
  │ bot/handlers.py   │      │ bot/messages.py    │
  │ (Commands)        │      │ (Text templates)   │
  └────┬──────────────┘      └────────────────────┘
       │
    ┌──┴──────────────────────────────┐
    │                                 │
┌───▼──────────────────┐   ┌──────────▼──────────┐
│ services/            │   │ models/database.py  │
│ mercadolibre.py      │   │ (SQLAlchemy ORM)    │
│ (MercadoLibre API)   │   └─────────────────────┘
│ & alerts.py          │           │
│ (Price checking)     │      ┌────▼────────────┐
└───┬──────────────────┘      │ data/bot.db      │
    │                         │ (SQLite)         │
    │  HTTP calls             └──────────────────┘
    │
    └──────────────────────────────────┐
                                       │
                         ┌─────────────▼────────────┐
                         │  MercadoLibre Public API │
                         │  (No auth required)      │
                         └──────────────────────────┘
```

## Key Components

### 1. **Telegram Bot Application** (`bot/handlers.py`)

The main bot logic using `python-telegram-bot` v20 with async/await support.

**Handlers:**
- `start_command` — Welcome message and quick intro
- `search_command` — Query MercadoLibre for products (invokes `_do_search`)
- `follow_alert_callback` — Create a price alert from search results
- `list_alerts_command` — Show user's active alerts
- `delete_alert_command` — Delete an existing alert
- `help_command` — Show all available commands

**Job Scheduling:**
- `check_all_alerts` runs every 30 minutes via `JobQueue`
- Uses APScheduler under the hood (via python-telegram-bot)
- Updates prices and triggers notifications when target is reached

### 2. **MercadoLibre API Client** (`services/mercadolibre.py`)

Handles all HTTP communication with the public MercadoLibre API (no credentials needed).

**Key functions:**
- `search_products(query: str, limit: int)` — Search for products
  - Returns list of dicts with title, price, ID, URL
  - No pagination needed (defaults to 5 results per request)

- `get_item(item_id: str)` — Fetch single product details
  - Returns current price and availability
  - Returns `None` if product deleted/unavailable (404)

**HTTP Client:**
- Uses `httpx` for async HTTP calls
- No rate limiting detected (public API)
- Handles JSON parsing and basic error handling

### 3. **Alert Service** (`services/alerts.py`)

Core business logic for price monitoring.

**Key functions:**
- `check_all_alerts()` — Triggered every 30 minutes
  - Fetches all active alerts from database
  - Calls MercadoLibre API for each alert's product
  - Compares `current_price` vs `target_price`
  - If `current_price ≤ target_price`: marks as triggered and sends notification
  - Updates database

- `create_alert(user, item_id, target_price)` — Creates new alert
  - Fetches current product info from MercadoLibre
  - Stores in database with `is_active=True`

- `delete_alert(alert_id)` — Soft delete
  - Sets `is_active=False`

### 4. **Data Models** (`models/database.py`)

SQLAlchemy ORM models for user and alert persistence.

**Schema:**
```
User
├── id (Primary Key)
├── telegram_id (Unique) → Links to Telegram user
├── username → Telegram username (nullable)
└── created_at → UTC timestamp

Alert
├── id (Primary Key)
├── user_id (Foreign Key) → User.id
├── item_id → MercadoLibre item code (e.g., MLC1234567890)
├── item_name → Product name (cached from API)
├── item_url → Permalink to product
├── target_price → User's target price (cents)
├── current_price → Last known price (updated every 30 min)
├── is_active → Soft delete flag
├── created_at → UTC timestamp
└── triggered_at → When price target was reached (nullable)
```

**Database:**
- **Type:** SQLite (file-based)
- **Location:** `data/bot.db`
- **Thread safety:** Handled by SQLAlchemy connection pooling
- **Migrations:** None (schema is simple and stable)

### 5. **Health Check API** (`api/main.py`)

Simple FastAPI endpoint for monitoring bot availability.

**Endpoint:**
- `GET /health` → `{"status": "healthy"}` (HTTP 200)
- Runs on port 8080 in a separate thread
- Used by Docker health checks and monitoring

### 6. **Message Templates** (`bot/messages.py`)

Centralized text strings in Chilean Spanish. Keeps handlers clean and allows easy localization.

**Categories:**
- Welcome/help messages
- Search results formatting
- Alert notifications
- Error messages

---

## Data Flow

### Scenario 1: User Searches for a Product

```
User: /buscar iphone 15
  │
  ├→ handlers.search_command()
  │    └→ _do_search("iphone 15")
  │
  ├→ services.search_products("iphone 15")
  │    └→ httpx.get("https://api.mercadolibre.com/sites/MLC/search?q=iphone%2015")
  │         └→ Returns [{"id": "MLC123", "price": 750000, ...}, ...]
  │
  ├→ Store results in context.user_data["search_results"]
  │
  └→ Reply with numbered list + inline buttons
```

### Scenario 2: User Creates a Price Alert

```
User: Clicks button on search result
  │
  ├→ handlers.follow_alert_callback()
  │
  ├→ Get product from context.user_data["search_results"][index]
  │
  ├→ services.create_alert(user, item_id, target_price)
  │    ├→ get_item(item_id) [fetch current price from API]
  │    └→ db.add(Alert(...))
  │         └→ db.commit()
  │
  └→ Reply with confirmation "✅ ¡Alerta creada!"
```

### Scenario 3: Price Check (Every 30 minutes)

```
JobQueue triggers at 00:30, 01:00, 01:30, ...
  │
  ├→ services.check_all_alerts()
  │    ├→ db.query(Alert).filter(is_active=True)
  │    │   └→ Returns all active alerts
  │    │
  │    └→ For each alert:
  │         ├→ get_item(item_id) [fetch current price]
  │         │
  │         ├→ Compare: current_price ≤ target_price?
  │         │
  │         ├→ If TRUE:
  │         │   ├→ alert.is_active = False
  │         │   ├→ alert.triggered_at = now()
  │         │   ├→ db.commit()
  │         │   └→ context.bot.send_message(user_id, "🔔 ¡Bajó el precio!")
  │         │
  │         └→ Update: alert.current_price = current_price
  │              └→ db.commit()
```

---

## Technology Choices & Tradeoffs

### Why Telegram Bot Over Web API?

| Aspect | Telegram Bot | REST API |
|--------|---|---|
| **UX** | Instant notifications | Requires polling |
| **Setup** | Just `/start` | Key management complexity |
| **Scalability** | Webhooks available | Full server management |

**Decision:** Telegram bot chosen for simplicity and instant notifications via `push_update` flow.

### Why SQLite Over PostgreSQL?

| Aspect | SQLite | PostgreSQL |
|--------|--------|-----------|
| **Setup** | 0 — file on disk | Docker/server required |
| **Concurrency** | Limited (1 writer) | High |
| **Suitable for** | Single-bot instances | Multi-user services |
| **Scaling** | Not viable at scale | Horizontal scaling |

**Decision:** SQLite chosen because:
1. Single-bot instance (one writer)
2. Simple deployment (no external dependencies)
3. Fast startup (important for development)
4. If scaling needed: swap to PostgreSQL later (same SQLAlchemy interface)

### Why MercadoLibre Public API?

- No credentials needed (no token exposure risk)
- No rate limiting detected
- Accurate price data (source of truth)
- Sufficient for Chilean market

---

## Error Handling & Resilience

### API Failures

**Scenario:** MercadoLibre API is slow/down during `check_all_alerts()`

```python
try:
    item = await get_item(item_id)
except Exception:
    logger.exception("Error fetching %s", item_id)
    # Skip this alert, try again in 30 minutes
    # User is not notified of failure (better UX)
    continue
```

**Rationale:** Failed API calls should not crash the bot. Silently retry in next cycle.

### Database Errors

**Scenario:** SQLite is locked (writing during read)

```python
# SQLAlchemy handles retries automatically
# If lock persists > 30 sec, error is logged
```

### Missing Products

**Scenario:** User's tracked product was deleted from MercadoLibre

```python
item = await get_item(item_id)  # Returns None (404)
if item is None:
    alert.is_active = False  # Soft delete
    db.commit()
    # No notification sent (to avoid spam)
```

---

## Concurrency Model

### Threading

```
Main Thread: Telegram polling loop (blocking)
             └→ Handles updates, calls handlers

Health Thread: FastAPI on :8080 (daemon)
             └→ Responds to GET /health

Job Queue Thread: APScheduler (background)
             └→ Triggers check_all_alerts() every 30 min
```

### Async/Await

- **Handlers:** All async (`async def handler()`)
- **API calls:** `httpx` async client (no blocking)
- **Database:** Synchronous SQLAlchemy (no async ORM needed for SQLite)
- **Result:** Responsive bot, no thread contention

---

## Testing Strategy

### Unit Tests (`tests/test_mercadolibre.py`)

Uses `respx` to mock HTTP calls:
```python
@respx.mock
async def test_search_products():
    respx.get("https://api.mercadolibre.com/sites/MLC/search?q=iphone")
        .mock(return_value=httpx.Response(200, json=[...]))
    
    results = await search_products("iphone")
    assert len(results) == 5
```

**Benefits:**
- No external API calls
- Fast & isolated
- Reproducible

### Integration Tests (`tests/test_alerts.py`)

- Use in-memory SQLite (`:memory:`)
- Full end-to-end flow: search → create alert → check price → notify
- Verify database state before/after

---

## Deployment

### Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Copy and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Run bot
CMD ["python", "main.py"]
```

**Environment:**
- `TELEGRAM_BOT_TOKEN` — required
- `DATABASE_URL` — optional (defaults to `sqlite:///./data/bot.db`)
- Volume mount `/app/data` for persistence

---

## Monitoring & Logging

### Logs

```
2024-01-15 10:23:45 INFO    ml_price_tracker.main — Database initialized
2024-01-15 10:23:45 INFO    ml_price_tracker.main — Health server listening on :8080
2024-01-15 10:23:45 INFO    ml_price_tracker.main — Bot starting — polling for updates…
2024-01-15 10:25:12 INFO    ml_price_tracker.bot.handlers — User @john_doe started
2024-01-15 10:26:03 INFO    ml_price_tracker.services.mercadolibre — Search: "iphone 15" → 5 results
2024-01-15 10:30:00 INFO    ml_price_tracker.services.alerts — Checking 12 active alerts...
2024-01-15 10:30:01 INFO    ml_price_tracker.services.alerts — Alert #42 triggered! Price: $695000
```

### Health Check

Monitor `/health` endpoint with uptime monitoring service (e.g., Pingdom, UptimeRobot).

---

## Future Enhancements

### Short-term
- [ ] Webhook mode instead of polling (more reliable, fewer API calls)
- [ ] Price history graph `/grafico`
- [ ] Custom notification frequency per alert

### Medium-term
- [ ] Multi-marketplace support (Falabella, Amazon.cl, etc.)
- [ ] PostgreSQL migration (scale to 1000+ users)
- [ ] User authentication (private alerts, no Telegram dependency)

### Long-term
- [ ] Mobile app (iOS/Android)
- [ ] Price prediction using ML
- [ ] Browser extension for quick alerts

---

## Code Quality Standards

- **Linting:** All code passes `black` (formatting) and `flake8` (style)
- **Type hints:** 100% coverage (checked with `mypy`)
- **Tests:** 18+ test cases, >85% coverage
- **Docstrings:** All public functions documented

---

## Troubleshooting

| Issue | Cause | Solution |
|-------|-------|----------|
| `TELEGRAM_BOT_TOKEN is not set` | Missing `.env` | `cp .env.example .env` + add token |
| `database is locked` | Concurrent writes | Restart bot (SQLite limit) |
| `Search returns 0 results` | Product doesn't exist in MercadoLibre | Try different search term |
| `/health` returns 500 | FastAPI server crashed | Check logs, restart bot |
| Alerts not triggering | DB not committing | Check for SQLAlchemy errors in logs |
