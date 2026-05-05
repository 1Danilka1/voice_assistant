from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import CommandStart
from storage import database as db
from keyboards.menus import (
    main_menu, note_list_kb, event_list_kb, contacts_kb, back_home
)
from handlers.mood import handle_view_mood

router = Router()

PAGE_ALIASES = {
    "home": "home",
    "главная": "home",
    "notes": "notes",
    "заметки": "notes",
    "заметка": "notes",
    "calendar": "calendar",
    "календарь": "calendar",
    "события": "calendar",
    "contacts": "contacts",
    "контакты": "contacts",
    "mood": "mood",
    "настроение": "mood",
    "дневник": "mood",
}

WELCOME = (
    "👋 Привет! Я твой голосовой помощник.\n\n"
    "Отправь мне <b>голосовое сообщение</b> или напиши текстом.\n\n"
    "Что умею:\n"
    "📝 Создавать заметки\n"
    "📅 Добавлять события в календарь iPhone\n"
    "✉️ Отправлять сообщения контактам\n"
    "😊 Вести дневник настроения\n"
    "💌 Хранить капсулы времени\n\n"
    "Примеры команд:\n"
    "• <i>«Создай заметку: идея для проекта»</i>\n"
    "• <i>«Добавь встречу с врачом в пятницу в 14:00»</i>\n"
    "• <i>«Отправь Диме что опоздаю на 20 минут»</i>\n"
    "• <i>«Открой заметки»</i>"
)


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(WELCOME, reply_markup=main_menu())


async def handle_navigation_intent(message: Message, data: dict):
    page = (data.get("page") or "").lower()
    page = PAGE_ALIASES.get(page, page)
    await _show_page(message, page)


async def _show_page(message: Message, page: str, uid: int = None):
    if uid is None:
        uid = message.from_user.id

    if page == "home" or not page:
        await message.answer("🏠 Главная", reply_markup=main_menu())

    elif page == "notes":
        notes = await db.get_notes(uid)
        if not notes:
            await message.answer("📭 Заметок пока нет.", reply_markup=back_home())
        else:
            await message.answer(
                f"📝 <b>Заметки</b> ({len(notes)})",
                reply_markup=note_list_kb(notes),
            )

    elif page == "calendar":
        events = await db.get_events(uid)
        if not events:
            await message.answer("📭 Предстоящих событий нет.", reply_markup=back_home())
        else:
            await message.answer(
                f"📅 <b>События</b> ({len(events)})",
                reply_markup=event_list_kb(events),
            )

    elif page == "contacts":
        contacts = await db.get_contacts(uid)
        if not contacts:
            await message.answer(
                "📭 Контактов нет.\n\nПерешли мне сообщение от нужного человека, чтобы добавить.",
                reply_markup=back_home(),
            )
        else:
            await message.answer(
                f"👥 <b>Контакты</b> ({len(contacts)})",
                reply_markup=contacts_kb(contacts),
            )

    elif page == "mood":
        await handle_view_mood(message, uid=uid)

    else:
        await message.answer("🏠 Главная", reply_markup=main_menu())


# ─── Page navigation callbacks ────────────────────────────────────────────────

@router.callback_query(F.data.startswith("page:"))
async def page_callbacks(cb: CallbackQuery):
    page = cb.data.split(":")[1]
    await _show_page(cb.message, page, uid=cb.from_user.id)
    await cb.answer()
