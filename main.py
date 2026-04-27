import os
import re
import logging
from aiogram import Bot, Dispatcher, F, Router
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from dotenv import load_dotenv

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]
GROUP_CHAT_ID = os.environ.get("GROUP_CHAT_ID", "")

bot = Bot(token=BOT_TOKEN, default=None)
router = Router()


class ApplicationForm(StatesGroup):
    name = State()
    phone = State()
    description = State()


PHONE_PATTERN = re.compile(r"^[\+]?[\d\s\-\(\)]{7,20}$")


def is_valid_name(text: str) -> bool:
    if not text or len(text.strip()) < 2:
        return False
    if len(text) > 100:
        return False
    if text.strip().isdigit():
        return False
    return True


def is_valid_phone(text: str) -> bool:
    cleaned = text.strip()
    if not cleaned:
        return False
    return bool(PHONE_PATTERN.match(cleaned))


def is_valid_description(text: str) -> bool:
    if not text or len(text.strip()) < 3:
        return False
    if len(text) > 2000:
        return False
    return True


# ── /start ──────────────────────────────────────────────
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 Здравствуйте! Я помогу вам оставить заявку.\n\n"
        "Пожалуйста, введите ваше <b>имя</b>:",
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(ApplicationForm.name)


# ── /cancel ─────────────────────────────────────────────
@router.message(Command("cancel"))
async def cmd_cancel(message: Message, state: FSMContext):
    current = await state.get_state()
    if current is None:
        await message.answer("Нет активной заявки для отмены.\nНажмите /start чтобы оставить заявку.")
        return
    await state.clear()
    await message.answer(
        "❌ Заявка отменена.\nЧтобы начать заново, нажмите /start",
        reply_markup=ReplyKeyboardRemove(),
    )


# ── /chatid ─────────────────────────────────────────────
@router.message(Command("chatid"))
async def cmd_chatid(message: Message):
    await message.answer(
        f"ID этого чата: <code>{message.chat.id}</code>",
        parse_mode=ParseMode.HTML,
    )


# ── Шаг 1: Имя ─────────────────────────────────────────
@router.message(ApplicationForm.name, F.text)
async def process_name(message: Message, state: FSMContext):
    if not is_valid_name(message.text):
        await message.answer(
            "⚠️ Пожалуйста, введите корректное имя (минимум 2 буквы, без цифр):",
            parse_mode=ParseMode.HTML,
        )
        return

    await state.update_data(name=message.text.strip())

    keyboard = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Поделиться контактом", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await message.answer(
        "👍 Отлично! Теперь укажите ваш <b>номер телефона</b>.\n\n"
        "Нажмите кнопку ниже или введите номер вручную:",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard,
    )
    await state.set_state(ApplicationForm.phone)


@router.message(ApplicationForm.name)
async def process_name_invalid_type(message: Message, state: FSMContext):
    await message.answer(
        "⚠️ Пожалуйста, отправьте ваше имя текстом:",
    )


# ── Шаг 2: Телефон (контакт) ───────────────────────────
@router.message(ApplicationForm.phone, F.contact)
async def process_phone_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    await state.update_data(phone=phone)
    await message.answer(
        "✅ Номер получен! Теперь <b>опишите вашу заявку</b> или вопрос:",
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(ApplicationForm.description)


# ── Шаг 2: Телефон (текст) ─────────────────────────────
@router.message(ApplicationForm.phone, F.text)
async def process_phone_text(message: Message, state: FSMContext):
    if not is_valid_phone(message.text):
        await message.answer(
            "⚠️ Неверный формат номера. Введите телефон в формате:\n"
            "<code>+7 999 123 45 67</code> или <code>89991234567</code>",
            parse_mode=ParseMode.HTML,
        )
        return

    await state.update_data(phone=message.text.strip())
    await message.answer(
        "✅ Номер получен! Теперь <b>опишите вашу заявку</b> или вопрос:",
        parse_mode=ParseMode.HTML,
        reply_markup=ReplyKeyboardRemove(),
    )
    await state.set_state(ApplicationForm.description)


@router.message(ApplicationForm.phone)
async def process_phone_invalid_type(message: Message, state: FSMContext):
    await message.answer(
        "⚠️ Пожалуйста, отправьте номер телефона текстом или нажмите кнопку «Поделиться контактом».",
    )


# ── Шаг 3: Описание → отправка заявки ──────────────────
@router.message(ApplicationForm.description, F.text)
async def process_description(message: Message, state: FSMContext):
    if not is_valid_description(message.text):
        await message.answer(
            "⚠️ Описание слишком короткое. Пожалуйста, напишите подробнее (минимум 3 символа):",
        )
        return

    await state.update_data(description=message.text.strip())
    data = await state.get_data()
    await state.clear()

    username = f"@{message.from_user.username}" if message.from_user.username else "не указан"
    user_id = message.from_user.id

    application_text = (
        f"📋 <b>Новая заявка!</b>\n\n"
        f"👤 <b>Имя:</b> {data['name']}\n"
        f"📱 <b>Телефон:</b> {data['phone']}\n"
        f"📝 <b>Описание:</b> {data['description']}\n\n"
        f"🆔 <b>От:</b> {username} (id: <code>{user_id}</code>)"
    )

    if GROUP_CHAT_ID:
        try:
            await bot.send_message(
                chat_id=int(GROUP_CHAT_ID),
                text=application_text,
                parse_mode=ParseMode.HTML,
            )
            await message.answer(
                "✅ <b>Ваша заявка успешно отправлена!</b>\n\n"
                "Мы свяжемся с вами в ближайшее время.\n"
                "Если хотите оставить ещё одну заявку — нажмите /start",
                parse_mode=ParseMode.HTML,
                reply_markup=ReplyKeyboardRemove(),
            )
            logger.info(f"Заявка от {username} (id: {user_id}) отправлена в группу {GROUP_CHAT_ID}")
        except Exception as e:
            logger.error(f"Ошибка отправки заявки в группу: {e}")
            await message.answer(
                "⚠️ Ваша заявка принята, но произошла ошибка при отправке администратору. "
                "Попробуйте позже или свяжитесь напрямую.",
                parse_mode=ParseMode.HTML,
                reply_markup=ReplyKeyboardRemove(),
            )
    else:
        logger.warning("GROUP_CHAT_ID не задан!")
        await message.answer(
            "✅ Ваша заявка принята!\n\n"
            "⚠️ Администратор ещё не настроил группу для получения заявок.",
            parse_mode=ParseMode.HTML,
            reply_markup=ReplyKeyboardRemove(),
        )


@router.message(ApplicationForm.description)
async def process_description_invalid_type(message: Message, state: FSMContext):
    await message.answer(
        "⚠️ Пожалуйста, опишите вашу заявку текстом:",
    )


# ── Фолбэк: любые сообщения без состояния ──────────────
@router.message()
async def fallback(message: Message):
    await message.answer(
        "👋 Чтобы оставить заявку, нажмите /start\n"
        "Для отмены — /cancel",
    )


async def main():
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    if not GROUP_CHAT_ID:
        logger.warning(
            "⚠️  GROUP_CHAT_ID не задан! Заявки не будут "
            "отправляться в группу. Используйте /chatid чтобы узнать ID."
        )

    logger.info("Бот запущен и готов к работе!")

    # Drop pending updates to avoid handling old messages
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, allowed_updates=["message"])


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
