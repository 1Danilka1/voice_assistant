import aiosqlite
from config import settings

DB = settings.DB_PATH


async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.executescript("""
            CREATE TABLE IF NOT EXISTS notes (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id     INTEGER NOT NULL,
                title       TEXT    NOT NULL,
                text        TEXT    DEFAULT '',
                created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
                reveal_date DATETIME,
                is_capsule  INTEGER  DEFAULT 0,
                is_revealed INTEGER  DEFAULT 0
            );

            CREATE TABLE IF NOT EXISTS events (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id          INTEGER NOT NULL,
                title            TEXT    NOT NULL,
                description      TEXT    DEFAULT '',
                start_dt         DATETIME NOT NULL,
                end_dt           DATETIME,
                reminder_minutes INTEGER  DEFAULT 30,
                ical_uid         TEXT,
                notified         INTEGER  DEFAULT 0,
                created_at       DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS contacts (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_user_id    INTEGER NOT NULL,
                name             TEXT    NOT NULL,
                telegram_user_id INTEGER,
                telegram_username TEXT,
                created_at       DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS mood_entries (
                id         INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id    INTEGER NOT NULL,
                mood_score INTEGER NOT NULL,
                mood_text  TEXT    DEFAULT '',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS bot_settings (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
        """)
        await db.commit()


# ─── Notes ────────────────────────────────────────────────────────────────────

async def create_note(user_id: int, title: str, text: str = "",
                      reveal_date=None, is_capsule: bool = False) -> int:
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "INSERT INTO notes (user_id, title, text, reveal_date, is_capsule) VALUES (?,?,?,?,?)",
            (user_id, title, text, reveal_date, int(is_capsule)),
        )
        await db.commit()
        return cur.lastrowid


async def get_notes(user_id: int) -> list[dict]:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT * FROM notes
               WHERE user_id = ? AND (is_capsule = 0 OR is_revealed = 1)
               ORDER BY created_at DESC""",
            (user_id,),
        )
        return [dict(r) for r in await cur.fetchall()]


async def get_note(user_id: int, note_id: int) -> dict | None:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM notes WHERE id = ? AND user_id = ?", (note_id, user_id)
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def search_notes(user_id: int, query: str) -> list[dict]:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT * FROM notes WHERE user_id = ?
               AND (title LIKE ? OR text LIKE ?)
               AND (is_capsule = 0 OR is_revealed = 1)
               ORDER BY created_at DESC""",
            (user_id, f"%{query}%", f"%{query}%"),
        )
        return [dict(r) for r in await cur.fetchall()]


async def delete_note(user_id: int, note_id: int):
    async with aiosqlite.connect(DB) as db:
        await db.execute("DELETE FROM notes WHERE id = ? AND user_id = ?", (note_id, user_id))
        await db.commit()


# ─── Events ───────────────────────────────────────────────────────────────────

async def create_event(user_id: int, title: str, start_dt: str,
                       end_dt: str = None, description: str = "",
                       reminder_minutes: int = 30, ical_uid: str = None) -> int:
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            """INSERT INTO events
               (user_id, title, description, start_dt, end_dt, reminder_minutes, ical_uid)
               VALUES (?,?,?,?,?,?,?)""",
            (user_id, title, description, start_dt, end_dt, reminder_minutes, ical_uid),
        )
        await db.commit()
        return cur.lastrowid


async def get_events(user_id: int, date_filter: str = "all") -> list[dict]:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        if date_filter == "today":
            cur = await db.execute(
                "SELECT * FROM events WHERE user_id = ? AND DATE(start_dt) = DATE('now') ORDER BY start_dt",
                (user_id,),
            )
        elif date_filter == "week":
            cur = await db.execute(
                """SELECT * FROM events WHERE user_id = ?
                   AND DATE(start_dt) BETWEEN DATE('now') AND DATE('now', '+7 days')
                   ORDER BY start_dt""",
                (user_id,),
            )
        else:
            cur = await db.execute(
                "SELECT * FROM events WHERE user_id = ? AND start_dt >= datetime('now') ORDER BY start_dt",
                (user_id,),
            )
        return [dict(r) for r in await cur.fetchall()]


async def get_event(user_id: int, event_id: int) -> dict | None:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM events WHERE id = ? AND user_id = ?", (event_id, user_id)
        )
        row = await cur.fetchone()
        return dict(row) if row else None


async def delete_event(user_id: int, event_id: int):
    async with aiosqlite.connect(DB) as db:
        await db.execute("DELETE FROM events WHERE id = ? AND user_id = ?", (event_id, user_id))
        await db.commit()


async def get_pending_reminders() -> list[dict]:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT * FROM events
               WHERE notified = 0
                 AND datetime(start_dt, '-' || reminder_minutes || ' minutes') <= datetime('now')
                 AND start_dt > datetime('now', '-1 hour')""",
        )
        return [dict(r) for r in await cur.fetchall()]


async def mark_notified(event_id: int):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE events SET notified = 1 WHERE id = ?", (event_id,))
        await db.commit()


async def get_unrevealed_capsules() -> list[dict]:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT * FROM notes
               WHERE is_capsule = 1 AND is_revealed = 0
                 AND reveal_date <= datetime('now')"""
        )
        return [dict(r) for r in await cur.fetchall()]


async def mark_capsule_revealed(note_id: int):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE notes SET is_revealed = 1 WHERE id = ?", (note_id,))
        await db.commit()


# ─── Contacts ─────────────────────────────────────────────────────────────────

async def add_contact(owner_user_id: int, name: str,
                      telegram_user_id: int = None, telegram_username: str = None) -> int:
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "INSERT INTO contacts (owner_user_id, name, telegram_user_id, telegram_username) VALUES (?,?,?,?)",
            (owner_user_id, name, telegram_user_id, telegram_username),
        )
        await db.commit()
        return cur.lastrowid


async def get_contacts(owner_user_id: int) -> list[dict]:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM contacts WHERE owner_user_id = ? ORDER BY name", (owner_user_id,)
        )
        return [dict(r) for r in await cur.fetchall()]


async def find_contact(owner_user_id: int, name: str) -> list[dict]:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM contacts WHERE owner_user_id = ? AND name LIKE ?",
            (owner_user_id, f"%{name}%"),
        )
        return [dict(r) for r in await cur.fetchall()]


async def update_contact_id(contact_id: int, telegram_user_id: int):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "UPDATE contacts SET telegram_user_id = ? WHERE id = ?",
            (telegram_user_id, contact_id),
        )
        await db.commit()


async def delete_contact(owner_user_id: int, contact_id: int):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "DELETE FROM contacts WHERE id = ? AND owner_user_id = ?", (contact_id, owner_user_id)
        )
        await db.commit()


# ─── Mood ─────────────────────────────────────────────────────────────────────

async def add_mood(user_id: int, mood_score: int, mood_text: str = ""):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO mood_entries (user_id, mood_score, mood_text) VALUES (?,?,?)",
            (user_id, mood_score, mood_text),
        )
        await db.commit()


async def get_mood_entries(user_id: int, days: int = 7) -> list[dict]:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            """SELECT * FROM mood_entries
               WHERE user_id = ? AND created_at >= datetime('now', ? || ' days')
               ORDER BY created_at DESC""",
            (user_id, f"-{days}"),
        )
        return [dict(r) for r in await cur.fetchall()]


async def get_setting(key: str) -> str | None:
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT value FROM bot_settings WHERE key = ?", (key,))
        row = await cur.fetchone()
        return row[0] if row else None


async def set_setting(key: str, value: str):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO bot_settings (key, value) VALUES (?,?) "
            "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
        await db.commit()


async def get_dashboard_stats(user_id: int) -> dict:
    async with aiosqlite.connect(DB) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT COUNT(*) FROM notes WHERE user_id = ? AND (is_capsule = 0 OR is_revealed = 1)",
            (user_id,),
        )
        notes_count = (await cur.fetchone())[0]
        cur = await db.execute(
            "SELECT title, start_dt FROM events WHERE user_id = ? AND DATE(start_dt) = DATE('now') ORDER BY start_dt",
            (user_id,),
        )
        events_today = [dict(r) for r in await cur.fetchall()]
        cur = await db.execute(
            "SELECT mood_score FROM mood_entries WHERE user_id = ? ORDER BY created_at DESC LIMIT 1",
            (user_id,),
        )
        row = await cur.fetchone()
        last_mood = None
        if row:
            score = row["mood_score"]
            emoji_map = {5: "😄", 4: "😊", 3: "😐", 2: "😔", 1: "😞"}
            last_mood = (score, emoji_map.get(score, "😐"))
        return {"notes_count": notes_count, "events_today": events_today, "last_mood": last_mood}
