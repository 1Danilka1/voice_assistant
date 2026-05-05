# Voice Assistant — Telegram Bot

Personal voice assistant on Telegram. Speak (or type) → Claude parses intent → bot creates notes, calendar events, contacts, mood entries, or sends messages on your behalf. Reminders sync to iPhone via iCloud CalDAV.

## Stack

- **aiogram 3** — Telegram Bot API client (long-polling)
- **OpenAI Whisper** — voice-to-text on incoming voice messages
- **Anthropic Claude** — intent parsing via tool-use (`services/brain.py`)
- **Telethon** — user client, lets the bot send messages *as you* to your contacts
- **SQLite** (`aiosqlite`) — local file storage, no separate DB service
- **APScheduler** — reminder loop (events + time-capsule notes)
- **caldav / icalendar** — iCloud calendar sync

## Project structure

```
bot.py                  # Entry point — wires routers, starts polling + scheduler
config.py               # Settings loaded from .env
requirements.txt
railway.json            # Railway deploy config

handlers/               # aiogram routers (one per feature)
  navigation.py         #   /start + main menu navigation
  voice.py              #   voice + text catch-all → Whisper → brain → action
  notes.py              #   note CRUD callbacks
  calendar_handler.py   #   event CRUD callbacks
  contacts.py           #   contact CRUD + message-forward flow
  mood.py               #   mood tracker callbacks
  setup.py              #   /setup FSM for first-run auth (iCloud, Telethon)

services/
  stt.py                # Whisper wrapper
  brain.py              # Claude tool-use intent parser → structured commands
  apple_calendar.py     # CalDAV sync to iCloud
  scheduler.py          # APScheduler — fires reminders + reveals time capsules
  telegram_sender.py    # Telethon user client (send-as-you)

storage/
  database.py           # All SQLite I/O — notes, events, contacts, mood

keyboards/
  menus.py              # Inline keyboard builders
```

## Local setup

```bash
python -m venv venv
venv\Scripts\activate      # PowerShell: venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env       # then fill in real values
python bot.py
```

Required env vars (see `.env.example`): `BOT_TOKEN`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`. Optional: iCloud creds, Telegram API ID/hash, `TIMEZONE`, `DB_PATH`.

## Deploying on Railway

Single service — **no separate database service needed**, SQLite is embedded.

1. New project → Deploy from GitHub repo
2. Variables → paste contents of `.env`
3. Volumes → mount at `/data`, then set `DB_PATH=/data/assistant.db` so the SQLite file survives redeploys
4. `railway.json` already sets the start command (`python bot.py`)

## Conventions

- **Router order matters** in `bot.py` — more specific routers must come before `voice.router` (the catch-all). Don't reorder without reading the comment block at `bot.py:29`.
- **All DB access goes through `storage/database.py`** — handlers never import `aiosqlite` directly.
- **Claude tool schema is the source of truth for intents** — `services/brain.py` defines the `parse_command` tool; adding a new intent means updating both the enum there *and* a handler in `handlers/voice.py`.
- **Russian + English UX** — user-facing strings are mixed (Russian primary). Keep that style when adding messages.
- **No backend / API server** — this is a polling bot, not a web service. Don't add Flask/FastAPI unless there's a real need (e.g., webhooks).
- **SQLite, not Postgres** — don't suggest a DB migration unless the user asks. Personal-scale bot, file storage is correct here.
