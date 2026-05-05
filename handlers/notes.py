import html
import logging
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from storage import database as db

log = logging.getLogger(__name__)
from keyboards.menus import (
    note_list_kb, note_actions_kb, note_delete_confirm_kb, back_home
)

router = Router()


def _fmt_note(note: dict) -> str:
    capsule_tag = " 💌" if note.get("is_capsule") else ""
    date = note["created_at"][:16].replace("T", " ")
    text = f"📝 <b>{html.escape(note['title'])}</b>{capsule_tag}\n"
    text += f"<i>{date}</i>\n"
    if note.get("text"):
        text += f"\n{html.escape(note['text'])}"
    return text


async def handle_note_intent(message: Message, intent: str, data: dict, reply: str):
    uid = message.from_user.id

    if intent == "create_note":
        title = (data.get("title") or "Заметка").strip()
        text = (data.get("text") or "").strip()
        note_id = await db.create_note(uid, title, text)
        log.info("Note created: id=%s title=%r uid=%s", note_id, title, uid)
        await message.answer(
            f"📝 Заметка создана!\n\n<b>{html.escape(title)}</b>"
            + (f"\n\n{html.escape(text)}" if text else ""),
            reply_markup=note_actions_kb(note_id),
        )
        log.info("Note creation message sent")

    elif intent == "time_capsule":
        title = (data.get("title") or "Капсула времени").strip()
        text = (data.get("text") or "").strip()
        reveal = data.get("reveal_date")
        if not reveal:
            await message.answer("📅 Укажи дату, когда открыть капсулу.")
            return
        note_id = await db.create_note(uid, title, text, reveal_date=reveal, is_capsule=True)
        await message.answer(
            f"💌 Капсула запечатана!\n\n<b>{html.escape(title)}</b>\n<i>Откроется: {reveal[:10]}</i>",
            reply_markup=back_home(),
        )

    elif intent == "view_notes":
        notes = await db.get_notes(uid)
        if not notes:
            await message.answer("📭 Заметок пока нет.\n\nСкажи «Создай заметку…» чтобы добавить первую.")
            return
        await message.answer(
            f"📝 <b>Заметки</b> ({len(notes)})",
            reply_markup=note_list_kb(notes),
        )

    elif intent == "search_notes":
        query = data.get("query", "")
        if not query:
            await message.answer("🔍 Укажи что искать.")
            return
        notes = await db.search_notes(uid, query)
        if not notes:
            await message.answer(f"🔍 По запросу «{query}» ничего не найдено.")
            return
        await message.answer(
            f"🔍 Найдено: {len(notes)}",
            reply_markup=note_list_kb(notes),
        )

    elif intent == "view_note":
        query = data.get("query") or data.get("title") or ""
        notes = await db.search_notes(uid, query) if query else []
        if not notes:
            await message.answer(f"🔍 Заметка «{query}» не найдена.")
            return
        note = notes[0]
        await message.answer(_fmt_note(note), reply_markup=note_actions_kb(note["id"]))

    elif intent == "delete_note":
        query = data.get("query") or data.get("title") or ""
        notes = await db.search_notes(uid, query) if query else []
        if not notes:
            await message.answer(f"🔍 Заметка «{query}» не найдена.")
            return
        note = notes[0]
        await message.answer(
            f"🗑 Удалить заметку <b>{note['title']}</b>?",
            reply_markup=note_delete_confirm_kb(note["id"]),
        )

    else:
        await message.answer(f"🤔 {reply}")


# ─── Callback handlers ────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("note:"))
async def note_callbacks(cb: CallbackQuery):
    _, action, raw_id = cb.data.split(":", 2)
    note_id = int(raw_id)
    uid = cb.from_user.id

    if action == "view":
        note = await db.get_note(uid, note_id)
        if not note:
            await cb.answer("Заметка не найдена", show_alert=True)
            return
        await cb.message.edit_text(_fmt_note(note), reply_markup=note_actions_kb(note_id))

    elif action == "del_confirm":
        note = await db.get_note(uid, note_id)
        title = note["title"] if note else "?"
        await cb.message.edit_text(
            f"🗑 Удалить заметку <b>{title}</b>?",
            reply_markup=note_delete_confirm_kb(note_id),
        )

    elif action == "delete":
        note = await db.get_note(uid, note_id)
        title = note["title"] if note else "?"
        await db.delete_note(uid, note_id)
        notes = await db.get_notes(uid)
        await cb.message.edit_text(
            f"✅ Заметка «{title}» удалена.\n\n📝 <b>Заметки</b> ({len(notes)})",
            reply_markup=note_list_kb(notes) if notes else back_home(),
        )

    await cb.answer()
