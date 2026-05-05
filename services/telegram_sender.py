"""Telethon user client — sends messages as the account owner, not as the bot."""

import logging
from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from config import settings

log = logging.getLogger(__name__)

_client: TelegramClient | None = None
_phone_code_hash: str | None = None


def _make_client() -> TelegramClient:
    return TelegramClient(
        "user_session",
        settings.TG_API_ID,
        settings.TG_API_HASH,
    )


async def start():
    global _client
    if not settings.TG_API_ID or not settings.TG_API_HASH:
        log.warning("TG_API_ID / TG_API_HASH not set — user messaging disabled")
        return
    _client = _make_client()
    await _client.connect()
    if await _client.is_user_authorized():
        me = await _client.get_me()
        log.info("Telethon authorized as @%s", me.username or me.id)
    else:
        log.info("Telethon not authorized — use /setup in the bot")


async def is_configured() -> bool:
    return bool(settings.TG_API_ID and settings.TG_API_HASH)


async def is_authorized() -> bool:
    if not _client:
        return False
    return await _client.is_user_authorized()


async def request_code(phone: str) -> None:
    global _phone_code_hash
    result = await _client.send_code_request(phone)
    _phone_code_hash = result.phone_code_hash


async def sign_in(phone: str, code: str) -> bool:
    """Returns True on success, raises SessionPasswordNeededError if 2FA required."""
    await _client.sign_in(phone, code, phone_code_hash=_phone_code_hash)
    return True


async def sign_in_2fa(password: str) -> bool:
    await _client.sign_in(password=password)
    return True


async def send_message(recipient: str, text: str):
    """recipient can be @username, phone number, or Telegram user ID."""
    if not _client:
        raise RuntimeError("Telethon не настроен")
    await _client.send_message(recipient, text)


async def stop():
    if _client:
        await _client.disconnect()
