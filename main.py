import os
import uuid
import sqlite3
from telegram import Update, InlineQueryResultCachedVoice
from telegram.ext import (
Application,
InlineQueryHandler,
MessageHandler,
CommandHandler,
ContextTypes,
filters,
ConversationHandler
)

# Конфигурация

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID = os.getenv("ADMIN_ID")  # Замените на ваш Telegram ID
DB_NAME = “audio_bot.db”

# Состояния для ConversationHandler

ADD_TITLE, ADD_VOICE = range(2)
EDIT_CHOICE, EDIT_TITLE, EDIT_VOICE = range(3, 6)

class Database:
“”“Класс для работы с базой данных”””

```
def __init__(self, db_name):
    self.db_name = db_name
    self.init_db()

def get_connection(self):
    """Создание подключения к БД"""
    return sqlite3.connect(self.db_name)

def init_db(self):
    """Инициализация базы данных"""
    conn = self.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL UNIQUE,
            file_id TEXT NOT NULL,
            duration INTEGER,
            added_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_audio(self, title, file_id, duration, added_by):
    """Добавить аудиозапись"""
    title = title.lower().strip()
    conn = self.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO audio (title, file_id, duration, added_by) VALUES (?, ?, ?, ?)",
            (title, file_id, duration, added_by)
        )
        conn.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()

def get_all_audio(self):
    """Получить все аудиозаписи"""
    conn = self.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, file_id, duration FROM audio ORDER BY title")
    results = cursor.fetchall()
    conn.close()
    return results

def search_audio(self, query):
    """Поиск аудиозаписей по названию"""
    query = query.lower().strip()
    conn = self.get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, title, file_id, duration FROM audio WHERE title LIKE ? ORDER BY title LIMIT 50",
        (f"%{query}%",)
    )
    results = cursor.fetchall()
    conn.close()
    return results

def delete_audio(self, identifier):
    """Удалить аудиозапись по ID или названию"""
    conn = self.get_connection()
    cursor = conn.cursor()
    
    if identifier.isdigit():
        cursor.execute("DELETE FROM audio WHERE id = ?", (int(identifier),))
    else:
        identifier = identifier.lower().strip()
        cursor.execute("DELETE FROM audio WHERE title = ?", (identifier,))
    
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted > 0

def get_audio_by_identifier(self, identifier):
    """Получить аудиозапись по ID или названию"""
    conn = self.get_connection()
    cursor = conn.cursor()
    
    if identifier.isdigit():
        cursor.execute("SELECT id, title, file_id, duration FROM audio WHERE id = ?", (int(identifier),))
    else:
        identifier = identifier.lower().strip()
        cursor.execute("SELECT id, title, file_id, duration FROM audio WHERE title = ?", (identifier,))
    
    result = cursor.fetchone()
    conn.close()
    return result

def update_title(self, audio_id, new_title):
    """Обновить название аудиозаписи"""
    new_title = new_title.lower().strip()
    conn = self.get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE audio SET title = ? WHERE id = ?", (new_title, audio_id))
        conn.commit()
        success = cursor.rowcount > 0
    except sqlite3.IntegrityError:
        success = False
    finally:
        conn.close()
    return success

def update_file(self, audio_id, new_file_id, duration):
    """Обновить файл аудиозаписи"""
    conn = self.get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE audio SET file_id = ?, duration = ? WHERE id = ?", 
                  (new_file_id, duration, audio_id))
    conn.commit()
    success = cursor.rowcount > 0
    conn.close()
    return success

def get_count(self):
    """Получить количество записей"""
    conn = self.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM audio")
    count = cursor.fetchone()[0]
    conn.close()
    return count
```

# Инициализация базы данных

db = Database(DB_NAME)

def is_admin(user_id):
“”“Проверка прав администратора”””
return user_id == ADMIN_USER_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
“”“Обработчик команды /start”””
user = update.effective_user
user_name = user.first_name or user.username or “друг”

```
message = (
    f"👋 Привет, {user_name}!\n\n"
    f"Я бот для быстрого доступа к аудиосообщениям.\n\n"
    f"🔍 **Как использовать:**\n"
    f"В любом чате напиши: @{context.bot.username} название\n"
    f"и я предложу подходящие аудиозаписи!\n\n"
    f"📊 Всего в базе: {db.get_count()} аудио\n\n"
    f"ℹ️ /help - подробная справка"
)

if is_admin(user.id):
    message += "\n\n👑 Вы администратор! Используйте /help для просмотра команд управления."

await update.message.reply_text(message, parse_mode="Markdown")
```

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
“”“Обработчик команды /help”””
user_id = update.effective_user.id

```
message = (
    "📖 **Справка по боту**\n\n"
    "🔍 **Для всех пользователей:**\n"
    "• Используйте inline-режим в любом чате:\n"
    f"  @{context.bot.username} название_аудио\n"
    "• Бот предложит подходящие варианты\n"
    "• Выберите нужное аудио из списка\n\n"
)

if is_admin(user_id):
    message += (
        "👑 **Команды администратора:**\n"
        "• /add - добавить новую аудиозапись\n"
        "• /list - показать все аудиозаписи\n"
        "• /del <id или название> - удалить запись\n"
        "• /edit <id или название> - редактировать запись\n"
        "• /help - эта справка\n\n"
        "💡 **Примеры:**\n"
        "• /del 5\n"
        "• /del привет\n"
        "• /edit 3\n"
        "• /edit доброе утро"
    )
else:
    message += "ℹ️ Для добавления аудио обратитесь к администратору."

await update.message.reply_text(message, parse_mode="Markdown")
```

async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
“”“Начало процесса добавления аудио”””
user_id = update.effective_user.id

```
if not is_admin(user_id):
    await update.message.reply_text("❌ Эта команда доступна только администратору.")
    return ConversationHandler.END

await update.message.reply_text(
    "📝 Введите название для новой аудиозаписи:\n"
    "(Название будет автоматически переведено в нижний регистр)"
)
return ADD_TITLE
```

async def add_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
“”“Получение названия аудиозаписи”””
title = update.message.text.strip()

```
if not title:
    await update.message.reply_text("⚠️ Название не может быть пустым. Попробуйте снова:")
    return ADD_TITLE

# Сохраняем название в контекст
context.user_data['new_audio_title'] = title.lower()

await update.message.reply_text(
    f"✅ Название: *{title.lower()}*\n\n"
    f"🎤 Теперь отправьте голосовое сообщение.",
    parse_mode="Markdown"
)
return ADD_VOICE
```

async def add_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
“”“Получение голосового сообщения”””
if not update.message.voice:
await update.message.reply_text(
“⚠️ Пожалуйста, отправьте голосовое сообщение.\n”
“Или /cancel для отмены.”
)
return ADD_VOICE

```
voice = update.message.voice
title = context.user_data.get('new_audio_title')

# Добавление в базу данных
audio_id = db.add_audio(
    title=title,
    file_id=voice.file_id,
    duration=voice.duration,
    added_by=update.effective_user.id
)

if audio_id:
    await update.message.reply_text(
        f"✅ Аудиозапись успешно добавлена!\n\n"
        f"🆔 ID: {audio_id}\n"
        f"📝 Название: {title}\n"
        f"⏱ Длительность: {voice.duration}с\n"
        f"📊 Всего в базе: {db.get_count()} аудио"
    )
else:
    await update.message.reply_text(
        f"❌ Ошибка: аудиозапись с названием '{title}' уже существует!"
    )

# Очистка контекста
context.user_data.clear()
return ConversationHandler.END
```

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
“”“Отмена операции”””
context.user_data.clear()
await update.message.reply_text(“❌ Операция отменена.”)
return ConversationHandler.END

async def list_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
“”“Показать список всех аудио”””
user_id = update.effective_user.id

```
if not is_admin(user_id):
    await update.message.reply_text("❌ Эта команда доступна только администратору.")
    return

audio_list = db.get_all_audio()

if not audio_list:
    await update.message.reply_text("📭 База аудиозаписей пуста.")
    return

message = f"📋 **Все аудиозаписи ({len(audio_list)}):**\n\n"

for audio_id, title, file_id, duration in audio_list:
    message += f"🆔 {audio_id} | 📝 {title} | ⏱ {duration}с\n"

# Telegram ограничивает длину сообщения
if len(message) > 4000:
    parts = [message[i:i+4000] for i in range(0, len(message), 4000)]
    for part in parts:
        await update.message.reply_text(part, parse_mode="Markdown")
else:
    await update.message.reply_text(message, parse_mode="Markdown")
```

async def delete_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
“”“Удалить аудиозапись”””
user_id = update.effective_user.id

```
if not is_admin(user_id):
    await update.message.reply_text("❌ Эта команда доступна только администратору.")
    return

if not context.args:
    await update.message.reply_text(
        "⚠️ Укажите ID или название аудиозаписи:\n"
        "Примеры:\n"
        "• /del 5\n"
        "• /del привет"
    )
    return

identifier = " ".join(context.args)

# Получаем информацию перед удалением
audio_info = db.get_audio_by_identifier(identifier)

if not audio_info:
    await update.message.reply_text(f"❌ Аудиозапись '{identifier}' не найдена в базе.")
    return

# Удаляем
if db.delete_audio(identifier):
    await update.message.reply_text(
        f"✅ Аудиозапись удалена!\n\n"
        f"🆔 ID: {audio_info[0]}\n"
        f"📝 Название: {audio_info[1]}\n"
        f"📊 Осталось в базе: {db.get_count()} аудио"
    )
else:
    await update.message.reply_text(f"❌ Ошибка при удалении аудиозаписи.")
```

async def edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
“”“Начало процесса редактирования”””
user_id = update.effective_user.id

```
if not is_admin(user_id):
    await update.message.reply_text("❌ Эта команда доступна только администратору.")
    return ConversationHandler.END

if not context.args:
    await update.message.reply_text(
        "⚠️ Укажите ID или название аудиозаписи:\n"
        "Примеры:\n"
        "• /edit 5\n"
        "• /edit привет"
    )
    return ConversationHandler.END

identifier = " ".join(context.args)
audio_info = db.get_audio_by_identifier(identifier)

if not audio_info:
    await update.message.reply_text(f"❌ Аудиозапись '{identifier}' не найдена в базе.")
    return ConversationHandler.END

# Сохраняем информацию в контекст
context.user_data['edit_audio_id'] = audio_info[0]
context.user_data['edit_audio_title'] = audio_info[1]

await update.message.reply_text(
    f"✏️ **Редактирование аудиозаписи:**\n\n"
    f"🆔 ID: {audio_info[0]}\n"
    f"📝 Название: {audio_info[1]}\n"
    f"⏱ Длительность: {audio_info[3]}с\n\n"
    f"Что хотите изменить?\n\n"
    f"1️⃣ Название\n"
    f"2️⃣ Аудиофайл\n\n"
    f"Отправьте цифру (1 или 2) или /cancel для отмены:",
    parse_mode="Markdown"
)
return EDIT_CHOICE
```

async def edit_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
“”“Выбор что редактировать”””
choice = update.message.text.strip()

```
if choice == "1":
    await update.message.reply_text(
        "📝 Введите новое название:\n"
        "(Название будет автоматически переведено в нижний регистр)"
    )
    return EDIT_TITLE
elif choice == "2":
    await update.message.reply_text("🎤 Отправьте новое голосовое сообщение:")
    return EDIT_VOICE
else:
    await update.message.reply_text(
        "⚠️ Пожалуйста, отправьте 1 или 2.\n"
        "Или /cancel для отмены."
    )
    return EDIT_CHOICE
```

async def edit_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
“”“Изменение названия”””
new_title = update.message.text.strip().lower()
audio_id = context.user_data.get(‘edit_audio_id’)

```
if not new_title:
    await update.message.reply_text("⚠️ Название не может быть пустым. Попробуйте снова:")
    return EDIT_TITLE

if db.update_title(audio_id, new_title):
    await update.message.reply_text(
        f"✅ Название успешно изменено!\n\n"
        f"🆔 ID: {audio_id}\n"
        f"📝 Новое название: {new_title}"
    )
else:
    await update.message.reply_text(
        f"❌ Ошибка: аудиозапись с названием '{new_title}' уже существует!"
    )

context.user_data.clear()
return ConversationHandler.END
```

async def edit_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
“”“Изменение аудиофайла”””
if not update.message.voice:
await update.message.reply_text(
“⚠️ Пожалуйста, отправьте голосовое сообщение.\n”
“Или /cancel для отмены.”
)
return EDIT_VOICE

```
voice = update.message.voice
audio_id = context.user_data.get('edit_audio_id')

if db.update_file(audio_id, voice.file_id, voice.duration):
    await update.message.reply_text(
        f"✅ Аудиофайл успешно обновлен!\n\n"
        f"🆔 ID: {audio_id}\n"
        f"⏱ Новая длительность: {voice.duration}с"
    )
else:
    await update.message.reply_text("❌ Ошибка при обновлении аудиофайла.")

context.user_data.clear()
return ConversationHandler.END
```

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
“”“Обработчик inline-запросов”””
query = update.inline_query.query.strip()

```
# Поиск в базе данных
if query:
    results = db.search_audio(query)
else:
    results = db.get_all_audio()[:50]

# Формирование результатов для Telegram
inline_results = []

for audio_id, title, file_id, duration in results:
    inline_results.append(
        InlineQueryResultCachedVoice(
            id=str(uuid.uuid4()),
            voice_file_id=file_id,
            title=title
        )
    )

# Отправка результатов
await update.inline_query.answer(
    inline_results,
    cache_time=10,
    is_personal=False
)
```

def main():
“”“Запуск бота”””
# Создание приложения
application = Application.builder().token(BOT_TOKEN).build()

```
# ConversationHandler для добавления аудио
add_handler = ConversationHandler(
    entry_points=[CommandHandler("add", add_start)],
    states={
        ADD_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_title)],
        ADD_VOICE: [MessageHandler(filters.VOICE, add_voice)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# ConversationHandler для редактирования аудио
edit_handler = ConversationHandler(
    entry_points=[CommandHandler("edit", edit_start)],
    states={
        EDIT_CHOICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_choice)],
        EDIT_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_title)],
        EDIT_VOICE: [MessageHandler(filters.VOICE, edit_voice)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
)

# Регистрация обработчиков
application.add_handler(CommandHandler("start", start))
application.add_handler(CommandHandler("help", help_command))
application.add_handler(add_handler)
application.add_handler(CommandHandler("list", list_audio))
application.add_handler(CommandHandler("del", delete_audio))
application.add_handler(edit_handler)
application.add_handler(InlineQueryHandler(inline_query))

# Запуск бота
print("🤖 Бот запущен!")
print(f"📊 Аудиозаписей в базе: {db.get_count()}")
application.run_polling(allowed_updates=Update.ALL_TYPES)
```

if **name** == “**main**”:
main()