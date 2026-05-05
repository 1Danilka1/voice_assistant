from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup


def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📝 Заметки",    callback_data="page:notes")
    kb.button(text="📅 Календарь",  callback_data="page:calendar")
    kb.button(text="👤 Контакты",   callback_data="page:contacts")
    kb.button(text="😊 Настроение", callback_data="page:mood")
    kb.adjust(2)
    return kb.as_markup()


def back_home() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🏠 Главная", callback_data="page:home")
    return kb.as_markup()


def note_list_kb(notes: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for n in notes[:15]:
        label = n["title"][:38] + ("…" if len(n["title"]) > 38 else "")
        if n.get("is_capsule") and not n.get("is_revealed"):
            label = f"💌 {label}"
        kb.button(text=label, callback_data=f"note:view:{n['id']}")
    kb.button(text="🏠 Главная", callback_data="page:home")
    kb.adjust(1)
    return kb.as_markup()


def note_actions_kb(note_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🗑 Удалить",     callback_data=f"note:del_confirm:{note_id}")
    kb.button(text="◀ К заметкам",  callback_data="page:notes")
    kb.adjust(2)
    return kb.as_markup()


def note_delete_confirm_kb(note_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, удалить", callback_data=f"note:delete:{note_id}")
    kb.button(text="❌ Отмена",      callback_data=f"note:view:{note_id}")
    kb.adjust(2)
    return kb.as_markup()


def event_list_kb(events: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for ev in events[:15]:
        label = ev["title"][:38] + ("…" if len(ev["title"]) > 38 else "")
        kb.button(text=label, callback_data=f"event:view:{ev['id']}")
    kb.button(text="📅 Сегодня",  callback_data="events:today")
    kb.button(text="📆 Неделя",   callback_data="events:week")
    kb.button(text="🏠 Главная",  callback_data="page:home")
    kb.adjust(1)
    return kb.as_markup()


def event_actions_kb(event_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🗑 Удалить",    callback_data=f"event:del_confirm:{event_id}")
    kb.button(text="◀ К событиям", callback_data="page:calendar")
    kb.adjust(2)
    return kb.as_markup()


def event_delete_confirm_kb(event_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, удалить", callback_data=f"event:delete:{event_id}")
    kb.button(text="❌ Отмена",      callback_data=f"event:view:{event_id}")
    kb.adjust(2)
    return kb.as_markup()


def contacts_kb(contacts: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for c in contacts[:15]:
        icon = "✅" if c.get("telegram_user_id") else "⏳"
        kb.button(text=f"{icon} {c['name']}", callback_data=f"contact:view:{c['id']}")
    kb.button(text="🏠 Главная", callback_data="page:home")
    kb.adjust(1)
    return kb.as_markup()


def contact_actions_kb(contact_id: int, has_user_id: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if has_user_id:
        kb.button(text="✉️ Написать",   callback_data=f"contact:msg:{contact_id}")
    kb.button(text="🗑 Удалить",        callback_data=f"contact:del_confirm:{contact_id}")
    kb.button(text="◀ К контактам",    callback_data="page:contacts")
    kb.adjust(1)
    return kb.as_markup()


def contact_delete_confirm_kb(contact_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Да, удалить", callback_data=f"contact:delete:{contact_id}")
    kb.button(text="❌ Отмена",      callback_data=f"contact:view:{contact_id}")
    kb.adjust(2)
    return kb.as_markup()


def send_confirm_kb(contact_id: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📤 Отправить",  callback_data=f"msg:send:{contact_id}")
    kb.button(text="❌ Отмена",     callback_data=f"contact:view:{contact_id}")
    kb.adjust(2)
    return kb.as_markup()


def mood_score_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    scores = [("😞 1", 1), ("😔 2", 2), ("😐 3", 3), ("😊 4", 4), ("😄 5", 5)]
    for label, score in scores:
        kb.button(text=label, callback_data=f"mood:score:{score}")
    kb.adjust(5)
    return kb.as_markup()
