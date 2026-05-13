from datetime import datetime
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardMarkup

_RU_MONTHS_SHORT = {
    1: "янв", 2: "фев", 3: "мар", 4: "апр", 5: "мая", 6: "июн",
    7: "июл", 8: "авг", 9: "сен", 10: "окт", 11: "ноя", 12: "дек",
}


def _fmt_date_short(iso: str) -> str:
    try:
        d = datetime.strptime(iso[:10], "%Y-%m-%d")
        return f"{d.day} {_RU_MONTHS_SHORT[d.month]}"
    except Exception:
        return iso[:10]


def _fmt_event_label(start_dt: str) -> str:
    dt = None
    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"):
        try:
            dt = datetime.strptime(start_dt[:16], fmt)
            break
        except ValueError:
            continue
    if dt is None:
        return start_dt[:10]
    today = datetime.now().date()
    t = dt.strftime("%H:%M")
    if dt.date() == today:
        return f"Сег {t}"
    if (dt.date() - today).days == 1:
        return f"Зав {t}"
    return f"{dt.day} {_RU_MONTHS_SHORT[dt.month]} {t}"


def main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="📝 Заметки",    callback_data="page:notes")
    kb.button(text="📅 Календарь",  callback_data="page:calendar")
    kb.button(text="👤 Контакты",   callback_data="page:contacts")
    kb.button(text="😊 Настроение", callback_data="page:mood")
    kb.button(text="⚙️ Настройки", callback_data="page:settings")
    kb.adjust(2, 2, 1)
    return kb.as_markup()


def back_home() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="🏠 Главная", callback_data="page:home")
    return kb.as_markup()


def mood_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.button(text="➕ Записать настроение", callback_data="mood:record")
    kb.button(text="🏠 Главная",             callback_data="page:home")
    kb.adjust(1)
    return kb.as_markup()


def note_list_kb(notes: list[dict]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for n in notes[:15]:
        date_str = _fmt_date_short(n.get("created_at", ""))
        title = n["title"][:30] + ("…" if len(n["title"]) > 30 else "")
        label = f"{title} • {date_str}"
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
        date_label = _fmt_event_label(ev.get("start_dt", ""))
        title = ev["title"][:28] + ("…" if len(ev["title"]) > 28 else "")
        label = f"{title} • {date_label}"
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
        icon = "✅" if c.get("telegram_username") else "⏳"
        kb.button(text=f"{icon} {c['name']}", callback_data=f"contact:view:{c['id']}")
    kb.button(text="🏠 Главная", callback_data="page:home")
    kb.adjust(1)
    return kb.as_markup()


def contact_actions_kb(contact_id: int, has_username: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if has_username:
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
