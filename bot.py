import asyncio
import html
import logging
import aiosqlite
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

BOT_TOKEN = "9206737354:AAHXwTLrC94r0Bk8snpDNyrQgtexb7OU-VI"
DB_PATH = "tasks.db"

class AddTask(StatesGroup):
    waiting_text = State()

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                user_name TEXT NOT NULL,
                text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()


def main_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Посмотреть список желаний", callback_data="list_tasks")],
        [InlineKeyboardButton(text="➕ Добавить желание/напоминание", callback_data="add_task")],
    ])


@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "Привет! ❤️ Это бот для заметок и напоминаний для Ани и возможно для Максима:).\n\n"
        "Нажми «Добавить желание\напоминание», чтобы записать.",
        reply_markup=main_kb(),
    )


@dp.callback_query(F.data == "add_task")
async def ask_task(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddTask.waiting_text)
    await callback.message.answer("Напиши текст желания (до 1000 символов):")
    await callback.answer()


@dp.callback_query(F.data == "list_tasks")
async def show_tasks(callback: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT user_name, text FROM tasks WHERE user_id = ? ORDER BY id",
            (callback.from_user.id,),
        )
        rows = await cursor.fetchall()

    if not rows:
        await callback.message.answer("Список пока пуст! Добавь первое желание.", reply_markup=main_kb())
    else:
        lines = ["<b>📋 Твой список желаний и напоминаний:</b>\n"]
        for i, (user_name, text) in enumerate(rows, 1):
            lines.append(f"{i}. {html.escape(text)} <i>({html.escape(user_name)})</i>")
        await callback.message.answer("\n".join(lines), parse_mode="HTML", reply_markup=main_kb())
    await callback.answer()


@dp.message(StateFilter(AddTask.waiting_text), F.text, ~Command(commands=["start", "help"]))
async def save_task(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text:
        await message.answer("Пустое сообщение не сохранено. Напиши текст.")
        return
    if len(text) > 1000:
        await message.answer("Слишком длинно (макс. 1000 символов). Сократи, пожалуйста.")
        return

    user_name = message.from_user.first_name or "Аня"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO tasks (user_id, user_name, text) VALUES (?, ?, ?)",
            (message.from_user.id, user_name, text),
        )
        await db.commit()

    await state.clear()
    await message.answer(
        f"✨ Записано!\n\n<b>{html.escape(text)}</b>",
        parse_mode="HTML",
        reply_markup=main_kb(),
    )


@dp.message(F.text, ~Command(commands=["start", "help"]))
async def fallback_text(message: Message):
    await message.answer(
        "Чтобы добавить желание, нажми кнопку 👇",
        reply_markup=main_kb(),
    )


async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    )
    await init_db()
    logging.info("Бот газ!")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот тормоз.")
