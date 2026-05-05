import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

from config import settings
from storage.database import init_db
from services.scheduler import start_scheduler
from services import telegram_sender as sender

from handlers import navigation, voice, notes, calendar_handler, contacts, mood, setup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


async def main():
    bot = Bot(
        token=settings.BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()

    # Order matters: more specific routers first
    dp.include_router(setup.router)        # /setup auth flow (FSM states first)
    dp.include_router(navigation.router)   # /start + page: callbacks
    dp.include_router(notes.router)        # note: callbacks
    dp.include_router(calendar_handler.router)  # event: callbacks
    dp.include_router(contacts.router)     # contact:/msg: callbacks + forward
    dp.include_router(mood.router)         # mood: callbacks
    dp.include_router(voice.router)        # voice + text (catch-all last)

    await init_db()
    log.info("Database ready")

    await sender.start()
    await start_scheduler(bot)

    log.info("Bot starting…")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
