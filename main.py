import os
import uuid
import sqlite3
from telegram import Update, InlineQueryResultCachedVoice
from telegram.ext import Application, InlineQueryHandler, MessageHandler, CommandHandler, ContextTypes, filters, ConversationHandler

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_ID")) if os.getenv("ADMIN_ID") else None
DB_NAME = "audio_bot.db"

ADD_TITLE, ADD_VOICE = range(2)
EDIT_CHOICE, EDIT_TITLE, EDIT_VOICE = range(3, 6)

class Database:
    def __init__(self, db_name):
        self.db_name = db_name
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_name, check_same_thread=False)

    def init_db(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS audio (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL UNIQUE,
            file_id TEXT NOT NULL,
            duration INTEGER,
            added_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )''')
        conn.commit()
        conn.close()

    def add_audio(self, title, file_id, duration, added_by):
        title = title.lower().strip()
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO audio (title, file_id, duration, added_by) VALUES (?, ?, ?, ?)",
                           (title, file_id, duration, added_by))
            conn.commit()
            return cursor.lastrowid
        except sqlite3.IntegrityError:
            return None
        finally:
            conn.close()

    def get_all_audio(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, file_id, duration FROM audio ORDER BY title")
        results = cursor.fetchall()
        conn.close()
        return results

    def search_audio(self, query):
        query = query.lower().strip()
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, title, file_id, duration FROM audio WHERE title LIKE ? ORDER BY title LIMIT 50",
                       (f"%{query}%",))
        results = cursor.fetchall()
        conn.close()
        return results

    def delete_audio(self, identifier):
        conn = self.get_connection()
        cursor = conn.cursor()
        if identifier.isdigit():
            cursor.execute("DELETE FROM audio WHERE id = ?", (int(identifier),))
        else:
            identifier = identifier.lower().strip()
            cursor.execute("DELETE FROM audio WHERE title = ?", (identifier,))
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return deleted

    def get_audio_by_identifier(self, identifier):
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
        new_title = new_title.lower().strip()
        conn = self.get_connection()
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE audio SET title = ? WHERE id = ?", (new_title, audio_id))
            conn.commit()
            return cursor.rowcount > 0
        except sqlite3.IntegrityError:
            return False
        finally:
            conn.close()

    def update_file(self, audio_id, new_file_id, duration):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE audio SET file_id = ?, duration = ? WHERE id = ?", (new_file_id, duration, audio_id))
        conn.commit()
        success = cursor.rowcount > 0
        conn.close()
        return success

    def get_count(self):
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM audio")
        count = cursor.fetchone()[0]
        conn.close()
        return count

db = Database(DB_NAME)

def is_admin(user_id):
    return user_id == ADMIN_USER_ID

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_name = user.first_name or "друг"
    await update.message.reply_text(
        f"Привет, {user_name}!\n\n"
        "Я бот для быстрого доступа к голосовым мемам\n\n"
        f"Напиши в любом чате: @{context.bot.username} текст\n"
        f"Всего аудио в базе: {db.get_count()}\n\n"
        "/help — справка"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = "Inline: @{context.bot.username} текст\n\n"
    if is_admin(update.effective_user.id):
        text += "Админ-команды:\n/add — добавить\n/list — список\n/del <id/название>\n/edit <id/название>"
    await update.message.reply_text(text)

async def add_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("Только админ")
        return ConversationHandler.END
    await update.message.reply_text("Название аудио:")
    return ADD_TITLE

async def add_title(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["title"] = update.message.text.lower().strip()
    await update.message.reply_text("Теперь голосовое:")
    return ADD_VOICE

async def add_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.voice:
        return ADD_VOICE
    voice = update.message.voice
    title = context.user_data["title"]
    if db.add_audio(title, voice.file_id, voice.duration, update.effective_user.id):
        await update.message.reply_text(f"Добавлено: {title}")
    else:
        await update.message.reply_text("Такое название уже есть!")
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено")
    return ConversationHandler.END

async def list_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    audios = db.get_all_audio()
    text = "\n".join([f"{i}. {t} ({d}с)" for i, t, _, d in audios[:50]])
    await update.message.reply_text(text or "Пусто")

async def delete_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id) or not update.message.text.split(maxsplit=1)[1:]:
        return
    identifier = update.message.text.split(maxsplit=1)[1]
    if db.delete_audio(identifier):
        await update.message.reply_text("Удалено")

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query.lower().strip()
    results = db.search_audio(query) if query else db.get_all_audio()[:50]
    inline_results = [
        InlineQueryResultCachedVoice(
            id=str(uuid.uuid4()),
            voice_file_id=file_id,
            title=title.title()
        )
        for _, title, file_id, _ in results
    ]
    await update.inline_query.answer(inline_results, cache_time=1)

def main():
    if not BOT_TOKEN or not ADMIN_USER_ID:
        print("Установите BOT_TOKEN и ADMIN_ID!")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(ConversationHandler(
        entry_points=[CommandHandler("add", add_start)],
        states={ADD_TITLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_title)],
                ADD_VOICE: [MessageHandler(filters.VOICE, add_voice)]},
        fallbacks=[CommandHandler("cancel", cancel)]
    ))
    app.add_handler(CommandHandler("list", list_audio))
    app.add_handler(CommandHandler("del", delete_audio))
    app.add_handler(InlineQueryHandler(inline_query))

    print("Бот запущен!")
    app.run_polling()

if __name__ == "__main__":
    main()