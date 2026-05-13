"""Telethon user client — sends messages as the account owner, not as the bot."""

import asyncio
import logging
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.errors import SessionPasswordNeededError
from config import settings
from storage import database as db

log = logging.getLogger(__name__)

_client: TelegramClient | None = None
_qr_task: asyncio.Task | None = None


async def _load_session() -> str:
    s = await db.get_setting("tg_session")
    return s or ""


def _make_client(session_str: str = "") -> TelegramClient:
    return TelegramClient(StringSession(session_str), settings.TG_API_ID, settings.TG_API_HASH)


async def start():
    global _client
    if not settings.TG_API_ID or not settings.TG_API_HASH:
        log.warning("TG_API_ID / TG_API_HASH not set — user messaging disabled")
        return
    session_str = await _load_session()
    _client = _make_client(session_str)
    await _client.connect()
    if await _client.is_user_authorized():
        me = await _client.get_me()
        log.info("Telethon authorized as @%s", me.username or me.id)
    else:
        log.info("Telethon not authorized — use /setup in the bot")


async def save_session():
    if _client:
        await db.set_setting("tg_session", _client.session.save())


async def is_configured() -> bool:
    return bool(settings.TG_API_ID and settings.TG_API_HASH)


async def is_authorized() -> bool:
    if not _client:
        return False
    return await _client.is_user_authorized()


async def do_qr_login(on_done):
    """Start QR login. Returns the tg:// URL to encode as a QR code image.
    on_done(ok, exc) is called in background when the user scans or it times out."""
    global _qr_task
    qr = await _client.qr_login()

    async def _wait():
        try:
            await asyncio.wait_for(qr.wait(), timeout=90)
            await save_session()
            await on_done(True, None)
        except asyncio.TimeoutError:
            await on_done(False, TimeoutError("QR expired"))
        except SessionPasswordNeededError as e:
            await on_done(False, e)
        except Exception as e:
            await on_done(False, e)

    _qr_task = asyncio.create_task(_wait())
    return qr.url


async def sign_in_2fa(password: str):
    await _client.sign_in(password=password)
    await save_session()


async def send_message(recipient: str, text: str):
    """recipient can be @username, phone number, or Telegram user ID."""
    if not _client:
        raise RuntimeError("Telethon не настроен")
    await _client.send_message(recipient, text)


async def stop():
    if _client:
        await _client.disconnect()
