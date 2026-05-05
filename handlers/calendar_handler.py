import html
from datetime import datetime
import pytz
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from storage import database as db
from services import apple_calendar as ical
from keyboards.menus import (
    event_list_kb, event_actions_kb, event_delete_confirm_kb, back_home
)
from config import settings

router = Router()
log = logging.getLogger(__name__)


def _parse_dt(iso: str) -> datetime | None:
    if not iso:
        return None
    try:
        from dateutil import parser as du
        dt = du.parse(iso)
        if dt.tzinfo is None:
            dt = pytz.timezone(settings.TIMEZONE).localize(dt)
        return dt
    except Exception:
        return None


def _fmt_event(ev: dict) -> str:
    start = ev["start_dt"][:16].replace("T", " ")
    text = f"📅 <b>{html.escape(ev['title'])}</b>\n🕐 {start}"
    if ev.get("end_dt"):
        text += f" — {ev['end_dt'][11:16]}"
    if ev.get("description"):
        text += f"\n📝 {html.escape(ev['description'])}"
    text += f"\n🔔 За {ev['reminder_minutes']} мин."
    if ev.get("ical_uid"):
        text += "\n✅ Синхронизировано с iPhone"
    else:
        text += "\n📲 Напомню в Telegram (iCloud не настроен)"
    return text


async def handle_calendar_intent(message: Message, intent: str, data: dict, reply: str):
    uid = message.from_user.id

    if intent == "create_event":
        title = (data.get("title") or "Событие").strip()
        raw_dt = data.get("datetime_start") or ""
        start_dt = _parse_dt(raw_dt)
        log.info("datetime_start raw=%r parsed=%s", raw_dt, start_dt)
        if not start_dt:
            await message.answer(f"📅 Не смог разобрать дату: <code>{html.escape(raw_dt)}</code>\nСкажи, например: «завтра в 15:00»")
            return

        end_dt = _parse_dt(data.get("datetime_end") or "")
        from datetime import timedelta
        if not end_dt:
            end_dt = start_dt + timedelta(hours=1)

        description = (data.get("text") or "").strip()
        reminder = int(data.get("reminder_minutes") or 30)

        # Sync to iCloud Calendar
        ical_uid = await ical.create_event(
            title, start_dt, end_dt, description, reminder
        )

        event_id = await db.create_event(
            uid, title,
            start_dt.isoformat(), end_dt.isoformat(),
            description, reminder, ical_uid,
        )
        ev = await db.get_event(uid, event_id)

        sync_note = "\n✅ Добавлено в iPhone" if ical_uid else "\n⚠️ iCloud не настроен — напомню в Telegram"
        await message.answer(
            _fmt_event(ev) + sync_note,
            reply_markup=event_actions_kb(event_id),
        )

    elif intent == "view_events":
        date_filter = data.get("date_filter") or "all"
        events = await db.get_events(uid, date_filter)
        label = {"today": "сегодня", "week": "на неделю", "all": "предстоящие"}.get(date_filter, "")
        if not events:
            await message.answer(f"📭 Нет событий ({label}).")
            return
        await message.answer(
            f"📅 <b>События {label}</b> ({len(events)})",
            reply_markup=event_list_kb(events),
        )

    elif intent == "delete_event":
        query = data.get("query") or data.get("title") or ""
        events = await db.get_events(uid)
        matches = [e for e in events if query.lower() in e["title"].lower()]
        if not matches:
            await message.answer(f"🔍 Событие «{query}» не найдено.")
            return
        ev = matches[0]
        await message.answer(
            f"🗑 Удалить событие <b>{ev['title']}</b>?",
            reply_markup=event_delete_confirm_kb(ev["id"]),
        )

    else:
        await message.answer(f"🤔 {reply}")


# ─── Callback handlers ────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("event:"))
async def event_callbacks(cb: CallbackQuery):
    _, action, raw_id = cb.data.split(":", 2)
    event_id = int(raw_id)
    uid = cb.from_user.id

    if action == "view":
        ev = await db.get_event(uid, event_id)
        if not ev:
            await cb.answer("Событие не найдено", show_alert=True)
            return
        await cb.message.edit_text(_fmt_event(ev), reply_markup=event_actions_kb(event_id))

    elif action == "del_confirm":
        ev = await db.get_event(uid, event_id)
        title = ev["title"] if ev else "?"
        await cb.message.edit_text(
            f"🗑 Удалить событие <b>{title}</b>?",
            reply_markup=event_delete_confirm_kb(event_id),
        )

    elif action == "delete":
        ev = await db.get_event(uid, event_id)
        if ev and ev.get("ical_uid"):
            await ical.delete_event(ev["ical_uid"])
        title = ev["title"] if ev else "?"
        await db.delete_event(uid, event_id)
        events = await db.get_events(uid)
        await cb.message.edit_text(
            f"✅ Событие «{title}» удалено.",
            reply_markup=event_list_kb(events) if events else back_home(),
        )

    await cb.answer()


@router.callback_query(F.data.startswith("events:"))
async def events_filter_callbacks(cb: CallbackQuery):
    _, date_filter = cb.data.split(":", 1)
    uid = cb.from_user.id
    events = await db.get_events(uid, date_filter)
    label = {"today": "сегодня", "week": "на неделю"}.get(date_filter, "")
    if not events:
        await cb.message.edit_text(
            f"📭 Нет событий {label}.",
            reply_markup=back_home(),
        )
    else:
        await cb.message.edit_text(
            f"📅 <b>События {label}</b> ({len(events)})",
            reply_markup=event_list_kb(events),
        )
    await cb.answer()
