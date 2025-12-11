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

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_USER_ID = int(os.getenv("ADMIN_ID"))
DB_NAME = "audio_bot.db"

ADD_TITLE, ADD_VOICE = range(2)
EDIT_CHOICE, EDIT_TITLE, EDIT_VOICE = range(3, 6)


class Database:
    
    def __init__(self, db_name):
        self.db_name = db_name
        self.init​​​​​​​​​​​​​​​​
```
