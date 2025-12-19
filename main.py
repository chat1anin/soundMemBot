import asyncio
import logging
import os
from typing import Optional

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, CommandObject
from aiogram.types import (
    Message,
    InlineQuery,
    InlineQueryResultCachedAudio,
)
from aiogram.enums import ParseMode
import aiosqlite

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

DB_PATH = "audios.db"

bot = Bot(token=BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            CREATE TABLE IF NOT EXISTS audios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                file_id TEXT NOT NULL
            );
            """
        )
        await db.commit()


def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


async def get_audio_by_id_or_name(db, key: str) -> Optional[aiosqlite.Row]:
    db.row_factory = aiosqlite.Row
    try:
        audio_id = int(key)
        cursor = await db.execute("SELECT * FROM audios WHERE id = ?", (audio_id,))
        row = await cursor.fetchone()
        await cursor.close()
        if row:
            return row
    except ValueError:
        pass

    key_lower = key.lower()
    cursor = await db.execute("SELECT * FROM audios WHERE name = ?", (key_lower,))
    row = await cursor.fetchone()
    await cursor.close()
    return row


user_states = {}


def set_state(user_id: int, state: Optional[str]):
    if state is None:
        user_states.pop(user_id, None)
    else:
        user_states.setdefault(user_id, {})["state"] = state


def get_state(user_id: int) -> Optional[str]:
    return user_states.get(user_id, {}).get("state")


def set_data(user_id: int, key: str, value):
    user_states.setdefault(user_id, {}).setdefault("data", {})[key] = value


def get_data(user_id: int) -> dict:
    return user_states.get(user_id, {}).get("data", {})


def clear_data(user_id: int):
    if user_id in user_states:
        user_states[user_id]["data"] = {}


@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_name = message.from_user.first_name or "друг"
    text = (
        f"Привет, {user_name}! 👋\n\n"
        "Этот бот ищет аудиозаписи в inline-режиме.\n"
        "Просто напиши <code>@имя_бота запрос</code> в любом чате.\n\n"
        "Команда /help — краткая справка."
    )
    await message.answer(text)


@dp.message(Command("help"))
async def cmd_help(message: Message):
    text = (
        "<b>Возможности бота</b>\n\n"
        "• Обычные пользователи:\n"
        "  - Используйте inline-режим: <code>@имя_бота название</code>.\n\n"
        "• Администратор:\n"
        "  - /add — добавить аудиозапись\n"
        "  - /list — список аудио\n"
        "  - /del &lt;id или название&gt; — удалить запись\n"
        "  - /edit &lt;id или название&gt; — редактировать запись\n"
    )
    await message.answer(text)


@dp.message(Command("add"))
async def cmd_add(message: Message):
    if not is_admin(message.from_user.id):
        return await message.answer("Команда доступна только администратору.")

    set_state(message.from_user.id, "adding_wait_audio")
    clear_data(message.from_user.id)
    await message.answer("Отправь аудиосообщение или аудиофайл, который нужно сохранить.")


@dp.message(F.content_type.in_({"voice", "audio"}))
async def handle_audio_for_add_or_edit(message: Message):
    user_id = message.from_user.id
    state = get_state(user_id)

    if state == "adding_wait_audio":
        file_id = message.voice.file_id if message.voice else message.audio.file_id
        set_data(user_id, "file_id", file_id)
        set_state(user_id, "adding_wait_name")
        await message.answer("Теперь отправь название аудио (будет сохранено в нижнем регистре).")
        return

    if state == "editing_wait_audio":
        file_id = message.voice.file_id if message.voice else message.audio.file_id
        data = get_data(user_id)
        data["new_file_id"] = file_id

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE audios SET file_id = ? WHERE id = ?",
                (data["new_file_id"], data["audio_id"]),
            )
            await db.commit()

        set_state(user_id, None)
        clear_data(user_id)
        await message.answer("Аудиофайл успешно обновлён.")
        return


@dp.message(F.text & (F.text.len() > 0))
async def handle_text_states(message: Message):
    user_id = message.from_user.id
    state = get_state(user_id)

    if state == "adding_wait_name":
        name = message.text.strip().lower()
        file_id = get_data(user_id).get("file_id")
        if not file_id:
            await message.answer("Что-то пошло не так, попробуй /add ещё раз.")
            set_state(user_id, None)
            clear_data(user_id)
            return

        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO audios (name, file_id) VALUES (?, ?)",
                (name, file_id),
            )
            await db.commit()

        set_state(user_id, None)
        clear_data(user_id)
        await message.answer(f"Запись с именем <code>{name}</code> добавлена.")
        return

    if state == "editing_wait_name":
        new_name_raw = message.text.strip()
        data = get_data(user_id)

        if new_name_raw != "-":
            new_name = new_name_raw.lower()
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute(
                    "UPDATE audios SET name = ? WHERE id = ?",
                    (new_name, data["audio_id"]),
                )
                await db.commit()
            await message.answer(f"Имя обновлено на <code>{new_name}</code>.")

        set_state(user_id, "editing_wait_audio")
        await message.answer(
            "Отправь новую аудиозапись (voice/audio).\n"
            "Если менять не нужно — отправь <code>-</code> текстом."
        )
        return

    if state == "editing_wait_audio" and message.text.strip() == "-":
        set_state(user_id, None)
        clear_data(user_id)
        await message.answer("Изменения имени применены, аудиофайл оставлен без изменений.")
        return


@dp.message(Command("list"))
async def cmd_list(message: Message):
    if not is_admin(message.from_user.id):
        return await message.answer("Команда доступна только администратору.")

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT id, name FROM audios ORDER BY id")
        rows = await cursor.fetchall()
        await cursor.close()

    if not rows:
        await message.answer("Список аудио пуст.")
        return

    lines = [f"{row['id']}: {row['name']}" for row in rows]
    text = "<b>Список аудио:</b>\n" + "\n".join(lines)
    await message.answer(text)


@dp.message(Command("del"))
async def cmd_del(message: Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        return await message.answer("Команда доступна только администратору.")

    if not command.args:
        return await message.answer("Использование: /del <id или название>")

    key = command.args.strip()

    async with aiosqlite.connect(DB_PATH) as db:
        row = await get_audio_by_id_or_name(db, key)
        if not row:
            return await message.answer("Запись не найдена.")

        await db.execute("DELETE FROM audios WHERE id = ?", (row["id"],))
        await db.commit()

    await message.answer(f"Запись <code>{row['name']}</code> (id={row['id']}) удалена.")


@dp.message(Command("edit"))
async def cmd_edit(message: Message, command: CommandObject):
    if not is_admin(message.from_user.id):
        return await message.answer("Команда доступна только администратору.")

    if not command.args:
        return await message.answer("Использование: /edit <id или название>")

    key = command.args.strip()

    async with aiosqlite.connect(DB_PATH) as db:
        row = await get_audio_by_id_or_name(db, key)
        if not row:
            return await message.answer("Запись не найдена.")

    set_state(message.from_user.id, "editing_wait_name")
    clear_data(message.from_user.id)
    set_data(message.from_user.id, "audio_id", row["id"])

    await message.answer(
        f"Редактируем запись <code>{row['name']}</code> (id={row['id']}).\n"
        "Отправь новое имя (или <code>-</code>, чтобы оставить старое)."
    )


@dp.inline_query()
async def inline_handler(inline_query: InlineQuery):
    query = (inline_query.query or "").strip().lower()

    results = []
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if query:
            cursor = await db.execute(
                "SELECT id, name, file_id FROM audios WHERE name LIKE ? LIMIT 50",
                (f"%{query}%",),
            )
        else:
            cursor = await db.execute(
                "SELECT id, name, file_id FROM audios ORDER BY id DESC LIMIT 10"
            )
        rows = await cursor.fetchall()
        await cursor.close()

    for row in rows:
        results.append(
            InlineQueryResultCachedAudio(
                id=str(row["id"]),
                audio_file_id=row["file_id"],
                caption=row["name"],
            )
        )

    await inline_query.answer(results=results, cache_time=1, is_personal=False)


async def main():
    await init_db()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
