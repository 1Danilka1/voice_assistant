"""One-time Telethon auth flow: /setup → phone → code → (2FA password)."""

import html
from aiogram import Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from services import telegram_sender as sender

router = Router()


class SetupState(StatesGroup):
    waiting_phone = State()
    waiting_code = State()
    waiting_2fa = State()


@router.message(Command("setup"))
async def cmd_setup(message: Message, state: FSMContext):
    if not await sender.is_configured():
        await message.answer(
            "⚠️ Сначала добавь <b>TG_API_ID</b> и <b>TG_API_HASH</b> в файл .env\n\n"
            "Получи их на <b>my.telegram.org</b> → Apps → Create new application\n"
            "Затем перезапусти бота и снова введи /setup"
        )
        return

    if await sender.is_authorized():
        await message.answer("✅ Уже авторизован! Отправка сообщений работает.")
        return

    await state.set_state(SetupState.waiting_phone)
    await message.answer(
        "📱 Введи свой номер телефона (с кодом страны):\n"
        "Например: <code>+48123456789</code>"
    )


@router.message(SetupState.waiting_phone)
async def got_phone(message: Message, state: FSMContext):
    phone = message.text.strip()
    await state.update_data(phone=phone)
    try:
        await sender.request_code(phone)
    except Exception as e:
        await message.answer(f"❌ Ошибка: <code>{html.escape(str(e))}</code>")
        await state.clear()
        return

    await state.set_state(SetupState.waiting_code)
    await message.answer(
        "📩 Код отправлен в Telegram (или SMS).\n"
        "Введи его сюда:"
    )


@router.message(SetupState.waiting_code)
async def got_code(message: Message, state: FSMContext):
    code = message.text.strip().replace(" ", "")
    data = await state.get_data()
    phone = data["phone"]

    try:
        await sender.sign_in(phone, code)
        await state.clear()
        await message.answer(
            "✅ <b>Авторизован!</b>\n\n"
            "Теперь можешь отправлять сообщения любому контакту голосом:\n"
            "<i>«Отправь Диме что опоздаю на 20 минут»</i>"
        )
    except SessionPasswordNeededError:
        await state.set_state(SetupState.waiting_2fa)
        await message.answer("🔐 Введи пароль двухфакторной аутентификации:")
    except PhoneCodeInvalidError:
        await message.answer("❌ Неверный код. Попробуй ещё раз:")
    except Exception as e:
        await message.answer(f"❌ Ошибка: <code>{html.escape(str(e))}</code>")
        await state.clear()


@router.message(SetupState.waiting_2fa)
async def got_2fa(message: Message, state: FSMContext):
    password = message.text.strip()
    try:
        await sender.sign_in_2fa(password)
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
