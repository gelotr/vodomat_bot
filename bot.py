import os
import re
import asyncio
import aiosqlite
from dotenv import load_dotenv
from aiogram.types import Update

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.types import (
    Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
OPERATOR_CHAT_ID_RAW = os.getenv("OPERATOR_CHAT_ID", "").strip()
OPERATOR_CHAT_ID = int(OPERATOR_CHAT_ID_RAW) if OPERATOR_CHAT_ID_RAW else None

DB_PATH = "claims.db"

class Claim(StatesGroup):
    phone = State()
    amount = State()
    comment = State()

def phone_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отправить номер", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT DEFAULT (datetime('now')),
            tg_user_id INTEGER,
            tg_username TEXT,
            phone TEXT,
            amount INTEGER,
            comment TEXT,
            status TEXT DEFAULT 'new'
        )
        """)
        await db.commit()

async def save_claim(*, user_id: int, username: str | None, phone: str, amount: int, comment: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(
            "INSERT INTO claims (tg_user_id, tg_username, phone, amount, comment) VALUES (?, ?, ?, ?, ?)",
            (user_id, username, phone, amount, comment),
        )
        await db.commit()
        return cur.lastrowid

async def notify_operator(bot: Bot, claim_id: int, phone: str, amount: int, comment: str, user_id: int, username: str | None):
    if not OPERATOR_CHAT_ID:
        return
    uname = f"@{username}" if username else "(нет username)"
    text = (
        "Новая заявка на возврат\n"
        f"ID: {claim_id}\n"
        f"Телефон: {phone}\n"
        f"Сумма: {amount}\n"
        f"Комментарий: {comment}\n"
        f"Пользователь: {uname} | tg_id={user_id}"
    )
    await bot.send_message(OPERATOR_CHAT_ID, text)

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start(message: Message, state: FSMContext):
    await state.clear()
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Оформить заявку")]],
        resize_keyboard=True,
        one_time_keyboard=False,
    )
    await message.answer(
        "Привет! Если вода не пошла из аппарата — оформи заявку на возврат денег.",
        reply_markup=kb
    )

@dp.message(F.text == "Оформить заявку")
async def claim_start(message: Message, state: FSMContext):
    await state.set_state(Claim.phone)
    await message.answer("Отправь номер телефона кнопкой ниже:", reply_markup=phone_kb())

@dp.message(Claim.phone, F.contact)
async def got_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number
    await state.update_data(phone=phone)
    await state.set_state(Claim.amount)
    await message.answer("Сколько списалось? (только число, например 50)", reply_markup=ReplyKeyboardRemove())

@dp.message(Claim.phone)
async def phone_fallback(message: Message, state: FSMContext):
    phone = message.text.strip()
    await state.update_data(phone=phone)
    await state.set_state(Claim.amount)
    await message.answer("Сколько списалось? (только число, например 50)", reply_markup=ReplyKeyboardRemove())

@dp.message(Claim.amount)
async def got_amount(message: Message, state: FSMContext):
    t = message.text.strip()
    if not re.fullmatch(r"\d{1,6}", t):
        await message.answer("Нужно число без букв. Пример: 50")
        return
    await state.update_data(amount=int(t))
    await state.set_state(Claim.comment)
    await message.answer("Коротко опиши проблему (что случилось). Можно 1–2 предложения.")

@dp.message(Claim.comment)
async def got_comment(message: Message, state: FSMContext):
    data = await state.get_data()
    phone = data.get("phone", "")
    amount = int(data.get("amount", 0))
    comment = message.text.strip()

    claim_id = await save_claim(
        user_id=message.from_user.id,
        username=message.from_user.username,
        phone=phone,
        amount=amount,
        comment=comment,
    )
    await notify_operator(
        bot=bot,
        claim_id=claim_id,
        phone=phone,
        amount=amount,
        comment=comment,
        user_id=message.from_user.id,
        username=message.from_user.username,
    )

    await state.clear()
    await message.answer(
        f"Заявка принята. Номер заявки: {claim_id}\n"
        "Поддержка свяжется с тобой для возврата.",
    )

async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN пустой. Заполни .env")
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    if os.getenv("WEBHOOK_URL"):
        print("WEBHOOK_URL set: polling disabled (webhook mode)")
    else:
        asyncio.run(main())



