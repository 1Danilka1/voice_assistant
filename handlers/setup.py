"""Telethon QR auth flow: /setup → QR code image → scan with phone → (2FA password)."""

import html
import io
import qrcode
from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, BufferedInputFile
from telethon.errors import SessionPasswordNeededError
from services import telegram_sender as sender

router = Router()

_pending: dict[int, Message] = {}


class SetupState(StatesGroup):
    waiting_2fa = State()


@router.message(Command("setup"))
async def cmd_setup(message: Message, state: FSMContext):
    if not await sender.is_configured():
        await message.answer(
            "⚠️ Сначала добавь <b>TG_API_ID</b> и <b>TG_API_HASH</b> в .env\n\n"
            "Получи их на <b>my.telegram.org</b> → API development tools"
        )
        return

    if await sender.is_authorized():
        await message.answer("✅ Уже авторизован! Отправка сообщений работает.")
        return

    uid = message.from_user.id
    status_msg = await message.answer("⏳ Генерирую QR-код...")

    async def on_done(ok: bool, exc: Exception | None):
        if ok:
            await status_msg.edit_text("✅ <b>Авторизован!</b> Отправка сообщений работает.")
            _pending.pop(uid, None)
        elif isinstance(exc, SessionPasswordNeededError):
            await status_msg.edit_text("🔐 Введи пароль двухфакторной аутентификации:")
            await state.set_state(SetupState.waiting_2fa)
        elif isinstance(exc, TimeoutError):
            await status_msg.edit_text("⏰ QR-код истёк. Введи /setup ещё раз.")
            _pending.pop(uid, None)
        else:
            await status_msg.edit_text(f"❌ Ошибка: <code>{html.escape(str(exc))}</code>")
            _pending.pop(uid, None)

    try:
        url = await sender.do_qr_login(on_done)
    except Exception as e:
        await status_msg.edit_text(f"❌ Ошибка: <code>{html.escape(str(e))}</code>")
        return

    qr_img = qrcode.make(url)
    buf = io.BytesIO()
    qr_img.save(buf, format="PNG")
    buf.seek(0)

    await status_msg.delete()
    _pending[uid] = await message.answer_photo(
        BufferedInputFile(buf.read(), filename="qr.png"),
        caption=(
            "📱 Отсканируй QR-код в Telegram на телефоне:\n\n"
            "<b>Настройки → Устройства → Подключить устройство</b>\n\n"
            "⏳ Код действителен 90 секунд"
        ),
    )


@router.message(SetupState.waiting_2fa)
async def got_2fa(message: Message, state: FSMContext):
    try:
        await sender.sign_in_2fa(message.text.strip())
        await state.clear()
        await message.answer("✅ <b>Авторизован!</b> Отправка сообщений работает.")
    except Exception as e:
        await message.answer(f"❌ Неверный пароль: <code>{html.escape(str(e))}</code>")
        await state.clear()


@router.message(Command("setup_status"))
async def cmd_status(message: Message):
    if not await sender.is_configured():
        await message.answer("⚙️ TG_API_ID / TG_API_HASH не заданы в .env")
    elif await sender.is_authorized():
        await message.answer("✅ Авторизован — отправка сообщений работает")
    else:
        await message.answer("❌ Не авторизован — введи /setup")
