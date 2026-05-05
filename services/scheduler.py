import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from storage import database as db

log = logging.getLogger(__name__)
_scheduler = AsyncIOScheduler()


async def _check_reminders(bot):
    pending = await db.get_pending_reminders()
    for ev in pending:
        mins = ev["reminder_minutes"]
        text = (
            f"⏰ <b>Напоминание</b>\n\n"
            f"📅 <b>{ev['title']}</b>\n"
            f"🕐 Через {mins} мин.\n"
        )
        if ev.get("description"):
            text += f"📝 {ev['description']}"
        try:
            await bot.send_message(ev["user_id"], text, parse_mode="HTML")
        except Exception as e:
            log.warning("Reminder send error for user %s: %s", ev["user_id"], e)
        await db.mark_notified(ev["id"])


async def _check_capsules(bot):
    capsules = await db.get_unrevealed_capsules()
    for note in capsules:
        text = (
            f"💌 <b>Ваша капсула времени открылась!</b>\n\n"
            f"<b>{note['title']}</b>\n\n"
            f"{note['text']}"
        )
        try:
            await bot.send_message(note["user_id"], text, parse_mode="HTML")
        except Exception as e:
            log.warning("Capsule send error for user %s: %s", note["user_id"], e)
        await db.mark_capsule_revealed(note["id"])


async def start_scheduler(bot):
    _scheduler.add_job(
        _check_reminders,
        IntervalTrigger(minutes=1),
        args=[bot],
        id="reminders",
        replace_existing=True,
    )
    _scheduler.add_job(
        _check_capsules,
        IntervalTrigger(hours=1),
        args=[bot],
        id="capsules",
        replace_existing=True,
    )
    _scheduler.start()
    log.info("Scheduler started")
