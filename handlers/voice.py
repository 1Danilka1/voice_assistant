"""Main pipeline: voice/text → STT → Claude → action."""

import io
import html
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.utils.chat_action import ChatActionSender

from services.stt import transcribe
from services.brain import parse_intent
from handlers.notes import handle_note_intent
from handlers.calendar_handler import handle_calendar_intent
from handlers.contacts import handle_contacts_intent
from handlers.mood import handle_mood_intent, handle_view_mood
from handlers.navigation import handle_navigation_intent
from keyboards.menus import main_menu, back_home
from storage import database as db

router = Router()
log = logging.getLogger(__name__)


async def _route(message: Message, bot: Bot, result: dict):
    intent = result.get("intent", "unknown")
    reply = result.get("reply", "Готово.")
    data = {k: v for k, v in result.items() if k not in ("intent", "reply")}

    log.info("Intent: %s | data keys: %s", intent, list(data.keys()))

    match intent:
        case "create_note" | "view_notes" | "view_note" | "delete_note" | "search_notes" | "time_capsule":
            await handle_note_intent(message, intent, data, reply)

        case "create_event" | "view_events" | "delete_event":
            await handle_calendar_intent(message, intent, data, reply)

        case "send_message" | "add_contact" | "view_contacts":
            await handle_contacts_intent(message, bot, intent, data, reply)

        case "navigate":
            await handle_navigation_intent(message, data)

        case "mood_note":
            await handle_mood_intent(message, data, reply)

        case "stream_capture":
            await _handle_stream(message, data, reply)

        case _:
            await message.answer(f"🤔 {html.escape(reply)}", reply_markup=main_menu())


async def _handle_stream(message: Message, data: dict, reply: str):
    """Free-form voice dump: extract notes, events, tasks automatically."""
    uid = message.from_user.id
    items = data.get("items") or []

    if not items:
        from datetime import datetime
        title = f"Поток мыслей {datetime.now().strftime('%d.%m %H:%M')}"
        text = data.get("text") or reply
        await db.create_note(uid, title, text)
        await message.answer(
            f"🌊 Записано в заметки!\n\n<b>{html.escape(title)}</b>\n{html.escape(text)}",
            reply_markup=back_home(),
        )
        return

    created = {"note": 0, "event": 0, "task": 0, "idea": 0}
    for item in items:
        itype = item.get("type", "note")
        title = item.get("title", "Без названия")
        text = item.get("text", "")

        if itype == "event" and item.get("datetime"):
            from handlers.calendar_handler import _parse_dt
            from datetime import timedelta
            start = _parse_dt(item["datetime"])
            if start:
                end = start + timedelta(hours=1)
                from services import apple_calendar as ical
                ical_uid = await ical.create_event(title, start, end)
                await db.create_event(uid, title, start.isoformat(), end.isoformat(),
                                      ical_uid=ical_uid)
                created["event"] += 1
                continue

        await db.create_note(uid, title, text or f"[{itype}]")
        created[itype] += 1

    parts = []
    if created["note"]:  parts.append(f"📝 {created['note']} заметки")
    if created["idea"]:  parts.append(f"💡 {created['idea']} идеи")
    if created["task"]:  parts.append(f"✅ {created['task']} задачи")
    if created["event"]: parts.append(f"📅 {created['event']} события")
    summary = "  ".join(parts) if parts else "ничего"

    await message.answer(
        f"🌊 <b>Поток мыслей разобран</b>\n\n{summary}\n\n<i>{html.escape(reply)}</i>",
        reply_markup=back_home(),
    )


# ─── Voice message handler ────────────────────────────────────────────────────

@router.message(F.voice | F.audio)
async def handle_voice(message: Message, bot: Bot):
    async with ChatActionSender.typing(bot=bot, chat_id=message.chat.id):
        voice = message.voice or message.audio
        try:
            file_info = await bot.get_file(voice.file_id)
            buf = io.BytesIO()
            await bot.download_file(file_info.file_path, destination=buf)
            buf.seek(0)
        except Exception as e:
            await message.reply(f"❌ Не удалось загрузить аудио: {html.escape(str(e))}")
            return

        try:
            text = await transcribe(buf)
        except Exception as e:
            await message.reply(f"❌ Ошибка распознавания речи: {html.escape(str(e))}")
            return

        if not text:
            await message.reply("🤷 Не разобрал — попробуй ещё раз, говори чётче.")
            return

        await message.reply(f"🎤 <i>{html.escape(text)}</i>")

    try:
        result = await parse_intent(text)
    except Exception as e:
        log.error("Brain error: %s", e)
        await message.answer("⚙️ Ошибка AI — попробуй ещё раз.")
        return

    try:
        await _route(message, bot, result)
    except Exception as e:
        log.error("Route error: %s", e, exc_info=True)
        await message.answer(f"❌ Ошибка обработки: <code>{html.escape(str(e))}</code>")


# ─── Plain text → same pipeline ──────────────────────────────────────────────

@router.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: Message, bot: Bot):
    async with ChatActionSender.typing(bot=bot, chat_id=message.chat.id):
        try:
            result = await parse_intent(message.text)
        except Exception as e:
            log.error("Brain error: %s", e)
            await message.answer("⚙️ Ошибка AI — попробуй ещё раз.")
            return

    try:
        await _route(message, bot, result)
    except Exception as e:
        log.error("Route error: %s", e, exc_info=True)
        await message.answer(f"❌ Ошибка обработки: <code>{html.escape(str(e))}</code>")
