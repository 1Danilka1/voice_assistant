"""Mood journal — daily tracking + weekly chart."""

from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from storage import database as db
from keyboards.menus import mood_score_kb, back_home

router = Router()

MOOD_EMOJI = {5: "😄", 4: "😊", 3: "😐", 2: "😔", 1: "😞"}
MOOD_LABEL = {5: "Отлично", 4: "Хорошо", 3: "Нейтрально", 2: "Плохо", 1: "Ужасно"}

# Pending mood text before score selection: {user_id: text}
_pending_text: dict[int, str] = {}


def _mood_chart(entries: list[dict]) -> str:
    if not entries:
        return "📭 Нет записей за последние 7 дней."

    avg = sum(e["mood_score"] for e in entries) / len(entries)
    text = "😊 <b>Дневник настроения (7 дней)</b>\n\n"

    for e in entries[:7]:
        score = e["mood_score"]
        date = e["created_at"][:10]
        bar = "█" * score + "░" * (5 - score)
        emoji = MOOD_EMOJI.get(score, "😐")
        text += f"<code>{date}</code>  {bar} {emoji}\n"
        if e.get("mood_text"):
            text += f"   <i>{e['mood_text'][:60]}</i>\n"

    text += f"\n⭐ Средний балл: <b>{avg:.1f}</b>"
    return text


async def handle_mood_intent(message: Message, data: dict, reply: str):
    uid = message.from_user.id
    mood_text = (data.get("mood_text") or "").strip()
    mood_score = data.get("mood_score")

    if mood_score:
        await db.add_mood(uid, int(mood_score), mood_text)
        emoji = MOOD_EMOJI.get(int(mood_score), "")
        label = MOOD_LABEL.get(int(mood_score), "")
        await message.answer(
            f"{emoji} Настроение записано: <b>{label} ({mood_score}/5)</b>"
            + (f"\n<i>{mood_text}</i>" if mood_text else ""),
            reply_markup=back_home(),
        )
    else:
        # Ask for score via buttons
        _pending_text[uid] = mood_text
        await message.answer(
            f"😊 Как ты себя чувствуешь?\n{mood_text if mood_text else ''}",
            reply_markup=mood_score_kb(),
        )


async def handle_view_mood(message: Message, uid: int = None):
    if uid is None:
        uid = message.from_user.id
    entries = await db.get_mood_entries(uid, days=7)
    await message.answer(_mood_chart(entries), reply_markup=back_home())


# ─── Callbacks ────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("mood:score:"))
async def mood_score_callback(cb: CallbackQuery):
    score = int(cb.data.split(":")[2])
    uid = cb.from_user.id
    text = _pending_text.pop(uid, "")
    await db.add_mood(uid, score, text)
    emoji = MOOD_EMOJI.get(score, "")
    label = MOOD_LABEL.get(score, "")
    await cb.message.edit_text(
        f"{emoji} Записано: <b>{label} ({score}/5)</b>"
        + (f"\n<i>{text}</i>" if text else ""),
        reply_markup=back_home(),
    )
    await cb.answer()
