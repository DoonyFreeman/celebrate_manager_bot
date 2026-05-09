# Celebrate Manager Bot

Telegram bot that sends daily notifications about holidays. Fetches holiday data from Calendarific API and lets users subscribe to specific holiday categories.

## Architecture

### Tech Stack
- **Language:** Python 3.12
- **Telegram Framework:** aiogram 3.x (async-native)
- **HTTP Client:** httpx (async)
- **Database:** SQLite + aiosqlite
- **Validation:** Pydantic v2
- **Scheduler:** APScheduler (AsyncIOScheduler)
- **Config:** pydantic-settings (via `.env`)
- **External API:** [Calendarific](https://calendarific.com/) (free tier: 1000 req/month)

### Architecture Pattern
Modular monolith — single process, well-separated modules.

### Project Structure
```
celebrate_manager_bot/
├── main.py                    # Entry point: запуск бота + scheduler
├── config.py                  # Pydantic Settings из .env
├── bot/
│   ├── handlers.py            # /start, /subscribe, /unsubscribe, /categories, /today
│   └── keyboards.py           # Inline-клавиатуры (категории праздников)
├── services/
│   ├── holiday_service.py     # Загрузка и кэширование праздников из Calendarific
│   ├── notification_service.py # Формирование и отправка уведомлений
│   └── user_service.py        # CRUD пользователей и подписок
├── db/
│   ├── models.py              # Таблицы SQLite
│   └── repository.py          # Data Access Layer
└── scheduler.py               # APScheduler — ежедневная рассылка в 07:00
```

### Data Flow (Daily Notification)
```
07:00 — APScheduler триггерит daily_job

1. HolidayService.get_today_holidays()
   ├── Проверить кэш в SQLite на сегодня
   ├── Если нет → GET Calendarific API (за месяц)
   ├── Сохранить в holidays_cache
   └── Вернуть записи за сегодня

2. UserService.get_active_subscribers()
   └── SELECT активных пользователей

3. Для каждого пользователя:
   ├── UserService.get_subscriptions(user_id)
   ├── Отфильтровать праздники по категориям
   ├── NotificationService.send_notification(chat_id, holidays)
   ├── Запись в notifications_log
   └── Обработка BotBlocked → деактивация
```

### Database Schema
```sql
users (
  id INTEGER PK,
  telegram_id INTEGER UNIQUE,
  username TEXT,
  is_active BOOLEAN,
  notify_time TEXT,          -- HH:MM
  created_at DATETIME,
  updated_at DATETIME
)

subscriptions (
  id INTEGER PK,
  user_id INTEGER FK → users,
  category TEXT,              -- "national", "observance", "seasonal", "all"
  UNIQUE(user_id, category)
)

holidays_cache (
  id INTEGER PK,
  date DATE,
  name TEXT,
  category TEXT,
  description TEXT,
  external_id TEXT,           -- ID из Calendarific
  UNIQUE(date, name, category)
)

notifications_log (
  id INTEGER PK,
  user_id INTEGER FK → users,
  holiday_id INTEGER FK → holidays_cache,
  sent_at DATETIME,
  UNIQUE(user_id, holiday_id)
)
```

### Bot Commands
| Command | Description |
|---------|-------------|
| `/start` | Регистрация, предложение подписаться |
| `/subscribe` | Выбор категорий (inline keyboard) |
| `/unsubscribe` | Отписка от всех |
| `/categories` | Просмотр/изменение подписок |
| `/today` | Показать праздники сегодня (вручную) |
| `/help` | Справка |

---

## Key Decisions

### ADR-001: External API — Calendarific
- **Why:** Есть категоризация праздников (national, observance, seasonal), критичная для фичи подписки
- **Trade-off:** Требуется API key, лимит 1000 запросов/мес
- **Mitigation:** Кэширование — 1 запрос загружает весь месяц

### ADR-002: Framework — aiogram 3.x
- **Why:** Async-native, FSM, middleware, современный API

### ADR-003: Storage — SQLite
- **Why:** Zero-config, ACID, достаточно для тысяч пользователей
- **Trade-off:** При 10k+ пользователей миграция на PostgreSQL

### ADR-004: Scheduler — APScheduler
- **Why:** AsyncIOScheduler в том же процессе, не нужен внешний cron

---

## Setup

### Environment Variables
```bash
cp .env.example .env
```

| Variable | Description | Required |
|----------|-------------|----------|
| `BOT_TOKEN` | Telegram Bot Token (от @BotFather) | Yes |
| `CALENDARIFIC_API_KEY` | API ключ Calendarific | Yes |
| `NOTIFY_TIME` | Время рассылки (HH:MM), default `07:00` | No |

### Installation
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Run
```bash
python main.py
```

---

## Development Guidelines

### Code Style
- Type hints everywhere
- Strict mypy (`--strict`)
- Ruff for linting + formatting
- Pydantic for all data models / config
- Async/await for all I/O (no blocking calls)

### Naming Conventions
- Modules: `snake_case.py`
- Classes: `PascalCase`
- Functions/variables: `snake_case`
- DB columns: `snake_case`
- Environment variables: `UPPER_SNAKE_CASE`

### Error Handling
- Catch `BotBlocked` → mark user as inactive
- Retry Calendarific API on 5xx (up to 3 times)
- Log all exceptions with traceback
- Graceful degradation: use cached data if API unavailable

---

## Implementation Plan

### Stage 1: Foundation
- `pyproject.toml` — dependencies (aiogram, httpx, aiosqlite, pydantic-settings, APScheduler)
- `config.py` — Pydantic Settings from `.env`
- `db/models.py` — 4 tables (users, subscriptions, holidays_cache, notifications_log)
- `db/__init__.py` — package init
- `db/repository.py` — CRUD, DB initialization

### Stage 2: Services
- `services/__init__.py` — package init
- `services/user_service.py` — registration, subscriptions, active users
- `services/holiday_service.py` — Calendarific API client, caching
- `services/notification_service.py` — message formatting, sending

### Stage 3: Bot
- `bot/__init__.py` — package init
- `bot/keyboards.py` — inline keyboards for category selection
- `bot/handlers.py` — commands: `/start`, `/subscribe`, `/unsubscribe`, `/categories`, `/today`
- Callback query handling for inline buttons

### Stage 4: Scheduler + Entry Point
- `scheduler.py` — APScheduler, daily_job at `NOTIFY_TIME`
- `main.py` — wire bot + scheduler, graceful shutdown

### Stage 5: Finalization
- `mypy --strict` — fix all type errors
- `ruff check` — formatting and linting
- Manual verification: run and test commands

### Git Rules
- `.env` is in `.gitignore` — never commit secrets
- After completing each stage/task, create a **quality commit**
- Commit message format: conventional commits (`feat:`, `fix:`, `refactor:`, `chore:`)
- Squash trivial commits before pushing
