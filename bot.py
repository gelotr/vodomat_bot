import asyncio
import logging
import os
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, CallbackQuery, Update, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

# ------------------------------------------------
# Базовые настройки логгирования
# ------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ------------------------------------------------
# Чтение токена из окружения + жёсткая проверка
# ------------------------------------------------
RAW_BOT_TOKEN = os.getenv("BOT_TOKEN")
if RAW_BOT_TOKEN is None:
    raise RuntimeError("Переменная окружения BOT_TOKEN не задана")

BOT_TOKEN = RAW_BOT_TOKEN.strip()

# диагностический вывод, чтобы ловить косяки окружения
logger.info("BOT_TOKEN is None: %s", RAW_BOT_TOKEN is None)
logger.info("BOT_TOKEN len: %s", len(BOT_TOKEN))
logger.info("BOT_TOKEN has colon: %s", (":" in BOT_TOKEN))
logger.info("BOT_TOKEN has spaces: %s", (" " in BOT_TOKEN))
logger.info("BOT_TOKEN has newline: %s", ("\n" in BOT_TOKEN or "\r" in BOT_TOKEN))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN пустой после strip()")

if ":" not in BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN без двоеточия — формат токена Telegram неверный")

# ------------------------------------------------
# Инициализация бота и диспетчера
# ------------------------------------------------
bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# ------------------------------------------------
# Примеры состояний / простых данных (если у тебя были)
# ------------------------------------------------

# здесь можно хранить временные данные по пользователям
user_state: dict[int, dict] = {}


# ------------------------------------------------
# Хэндлеры
# ------------------------------------------------

@dp.message(CommandStart())
async def cmd_start(message: Message):
    text = (
        "Привет! Я бот для управления водоматом.\n"
        "Используй /help, чтобы увидеть доступные команды."
    )
    await message.answer(text)


@dp.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "Доступные команды:\n"
        "/start — запуск бота\n"
        "/help — помощь\n"
        "/status — статус\n"
        "/menu — главное меню"
    )
    await message.answer(text)


@dp.message(Command("status"))
async def cmd_status(message: Message):
    # заглушка — сюда подключается твоя логика статуса
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    await message.answer(f"Бот жив. Серверное время: {now}")


@dp.message(Command("menu"))
async def cmd_menu(message: Message):
    kb = InlineKeyboardBuilder()
    kb.button(text="Пополнить баланс", callback_data="topup")
    kb.button(text="История операций", callback_data="history")
    kb.adjust(1)
    await message.answer("Главное меню:", reply_markup=kb.as_markup())


@dp.callback_query(F.data == "topup")
async def cb_topup(callback: CallbackQuery):
    await callback.message.answer("Функция пополнения баланса пока не реализована.")
    await callback.answer()


@dp.callback_query(F.data == "history")
async def cb_history(callback: CallbackQuery):
    await callback.message.answer("История операций пока не реализована.")
    await callback.answer()


# ------------------------------------------------
# Функции для вебхуков (вызываются из run_render.py)
# ------------------------------------------------

async def process_update(data: dict):
    """
    Эту функцию дергает run_render.py:
    data -> Update -> dp.feed_update().
    """
    update = Update.model_validate(data)
    await dp.feed_update(bot, update)


async def on_startup_webhook(webhook_url: str):
    """
    Вызывается при запуске веб-приложения (run_render.py:on_startup).
    """
    webhook_url = webhook_url.strip()
    if not webhook_url:
        raise RuntimeError("WEBHOOK_URL пустой при настройке вебхука")

    await bot.set_webhook(webhook_url, drop_pending_updates=True)
    logger.info("Webhook установлен: %s", webhook_url)


async def on_cleanup_webhook():
    """
    Вызывается при остановке веб-приложения (run_render.py:on_cleanup).
    """
    await bot.delete_webhook()
    await bot.session.close()
    logger.info("Webhook удалён, сессия бота закрыта")


# ------------------------------------------------
# Локальный запуск (polling) — на всякий случай
# ------------------------------------------------

async def _polling():
    """
    Локальный запуск бота через long polling.
    На Amvera он не нужен, используется run_render + вебхуки.
    """
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(_polling())
