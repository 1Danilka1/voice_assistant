"""Contacts management + Telegram messaging via Telethon user client."""

import html
import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from storage import database as db
from keyboards.menus import (
    contacts_kb, contact_actions_kb, contact_delete_confirm_kb,
    send_confirm_kb, back_home,
)
from services import telegram_sender as sender

router = Router()
log = logging.getLogger(__name__)

# In-memory store for pending messages awaiting confirmation: {(user_id, contact_id): text}
_pending: dict[tuple[int, int], str] = {}


def _fmt_contact(c: dict) -> str:
    status = "✅ Подключён" if c.get("telegram_user_id") else "⏳ Ещё не написал боту"
    text = f"👤 <b>{c['name']}</b>\n{status}"
    if c.get("telegram_username"):
        text += f"\n@{c['telegram_username']}"
    return text


async def handle_contacts_intent(message: Message, bot: Bot, intent: str, data: dict, reply: str):
    uid = message.from_user.id

    if intent == "view_contacts":
        contacts = await db.get_contacts(uid)
        if not contacts:
            await message.answer(
                "📭 Контактов нет.\n\n"
                "Перешли мне любое сообщение от нужного человека — я добавлю его в список.",
                reply_markup=back_home(),
            )
            return
        await message.answer(
            f"👥 <b>Контакты</b> ({len(contacts)})\n\n"
            "✅ = подключён к боту  ⏳ = ещё не написал",
            reply_markup=contacts_kb(contacts),
        )

    elif intent == "add_contact":
        name = (data.get("title") or data.get("recipient") or "").strip()
        if not name:
            await message.answer("👤 Укажи имя контакта.")
            return
        contact_id = await db.add_contact(uid, name)
        await message.answer(
            f"✅ Контакт <b>{name}</b> добавлен.\n\n"
            f"Попроси {name} написать боту /start — после этого сможешь отправлять сообщения.",
            reply_markup=back_home(),
        )

    elif intent == "send_message":
        recipient = (data.get("recipient") or "").strip()
        text = (data.get("message_text") or data.get("text") or "").strip()
        if not recipient:
            await message.answer("👤 Кому отправить сообщение?")
            return
        if not text:
            await message.answer("✉️ Что написать?")
            return

        matches = await db.find_contact(uid, recipient)
        if not matches:
            await message.answer(
                f"❌ Контакт «{html.escape(recipient)}» не найден.\n"
                "Добавь его: «Добавь контакт Имя @username»"
            )
            return

        contact = matches[0]
        if not contact.get("telegram_username"):
            await message.answer(
                f"⚠️ У контакта <b>{html.escape(contact['name'])}</b> нет @username.\n\n"
                f"Удали и добавь снова, указав username:\n"
                f"<i>«Добавь контакт Дима @dima123»</i>"
            )
            return

        if not await sender.is_authorized():
            await message.answer(
                "⚙️ Отправка сообщений не настроена.\n\n"
                "Введи /setup чтобы войти в свой Telegram аккаунт."
            )
            return

        _pending[(uid, contact["id"])] = text
        await message.answer(
            f"✉️ Отправить <b>{html.escape(contact['name'])}</b> (@{contact['telegram_username']})?\n\n"
            f"<i>{html.escape(text)}</i>",
            reply_markup=send_confirm_kb(contact["id"]),
        )

    else:
        await message.answer(f"🤔 {reply}")


# ─── Forward message → auto-add contact ───────────────────────────────────────

@router.message(F.forward_from)
async def handle_forward(message: Message):
    """User forwards a message from someone → register them as contact."""
    uid = message.from_user.id
    fwd = message.forward_from
    if fwd.is_bot:
        await message.answer("❌ Нельзя добавить бота как контакт.")
        return

    name = fwd.full_name or fwd.username or str(fwd.id)
    username = fwd.username

    # Check if already exists
    existing = await db.find_contact(uid, name)
    if existing:
        await db.update_contact_id(existing[0]["id"], fwd.id)
        await message.answer(f"✅ Контакт <b>{name}</b> обновлён (ID получен).")
        return

    contact_id = await db.add_contact(uid, name, fwd.id, username)
    await message.answer(
        f"✅ Контакт добавлен!\n\n👤 <b>{name}</b>\n{'@' + username if username else ''}",
        reply_markup=back_home(),
    )


# ─── Callback handlers ────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("contact:"))
async def contact_callbacks(cb: CallbackQuery):
    parts = cb.data.split(":", 2)
    action = parts[1]
    uid = cb.from_user.id

    if action == "view":
        contact_id = int(parts[2])
        contacts = await db.get_contacts(uid)
        c = next((x for x in contacts if x["id"] == contact_id), None)
        if not c:
            await cb.answer("Контакт не найден", show_alert=True)
            return
        await cb.message.edit_text(
            _fmt_contact(c),
            reply_markup=contact_actions_kb(contact_id, bool(c.get("telegram_user_id"))),
        )

    elif action == "msg":
        contact_id = int(parts[2])
        contacts = await db.get_contacts(uid)
        c = next((x for x in contacts if x["id"] == contact_id), None)
        if c:
            await cb.message.edit_text(
                f"✉️ Напиши сообщение для <b>{c['name']}</b> текстом или голосом."
            )

    elif action == "del_confirm":
        contact_id = int(parts[2])
        contacts = await db.get_contacts(uid)
        c = next((x for x in contacts if x["id"] == contact_id), None)
        name = c["name"] if c else "?"
        await cb.message.edit_text(
            f"🗑 Удалить контакт <b>{name}</b>?",
            reply_markup=contact_delete_confirm_kb(contact_id),
        )

    elif action == "delete":
        contact_id = int(parts[2])
        contacts = await db.get_contacts(uid)
        c = next((x for x in contacts if x["id"] == contact_id), None)
        name = c["name"] if c else "?"
        await db.delete_contact(uid, contact_id)
        remaining = await db.get_contacts(uid)
        await cb.message.edit_text(
            f"✅ Контакт «{name}» удалён.",
            reply_markup=contacts_kb(remaining) if remaining else back_home(),
        )

    await cb.answer()


@router.callback_query(F.data.startswith("msg:send:"))
async def send_message_callback(cb: CallbackQuery, bot: Bot):
    contact_id = int(cb.data.split(":")[2])
    uid = cb.from_user.id
    text = _pending.pop((uid, contact_id), None)

    if not text:
        await cb.answer("Сообщение не найдено — попробуй снова", show_alert=True)
        return

    contacts = await db.get_contacts(uid)
    c = next((x for x in contacts if x["id"] == contact_id), None)
    if not c or not c.get("telegram_username"):
        await cb.answer("Контакт недоступен", show_alert=True)
        return

    username = c.get("telegram_username")
    if not username:
        await cb.message.edit_text(
            f"⚠️ Нет @username для контакта <b>{html.escape(c['name'])}</b>.",
            reply_markup=back_home(),
        )
        await cb.answer()
        return

    try:
        await sender.send_message(username, text)
        await cb.message.edit_text(
            f"✅ Сообщение отправлено <b>{html.escape(c['name'])}</b>!"
        )
    except Exception as e:
        log.error("Send message error: %s", e)
        await cb.message.edit_text(
            f"❌ Не удалось отправить <b>{html.escape(c['name'])}</b>.\n"
            f"<code>{html.escape(str(e))}</code>\n\n"
            f"Текст:\n<code>{html.escape(text)}</code>",
            reply_markup=back_home(),
        )
    await cb.answer()
