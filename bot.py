import sqlite3
import logging
from datetime import datetime, timezone
import random
from typing import Optional, Tuple
from telegram import Update, Bot, Message, User, ChatPermissions, BotCommand
from telegram.ext import Application, CommandHandler
from datetime import datetime, timedelta, timezone  # Добавлено timedelta
import time  # Добавлено для работы с time.time()
import requests
import json
import re
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, Application, CommandHandler
import sqlite3
import random
from datetime import date
from telegram.ext import MessageHandler, filters
import logging
import html
from telegram.constants import ParseMode
import json
import os
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ContextTypes
from telegram import ChatPermissions
from datetime import datetime, timedelta
from difflib import SequenceMatcher
from telegram import ChatMemberUpdated
from telegram.ext import ChatMemberHandler
import logging
from telegram import Update, User
from telegram import Update
from telegram.ext import ContextTypes, ChatMemberHandler
import sqlite3
print("Модули импортирован успешно!")

import time
from telegram import Update, ChatMember
from telegram.ext import ContextTypes, MessageHandler, filters

# Глобальный словарь для хранения времени добавления бота
bot_added_times = {}


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# === НАСТРОЙКИ ===
TOKEN = "8560378565:AAEHvQdBQteRZzaeGhmPas6bjOe4wk-tU-E"  # Замените на токен вашего бота
DB_PATH = "bot.db"
RULES_FILE = "rules.json"
ANTIFLUD_HISTORY_FILE = "antiflud_history.json"
ANTIFLUD_STATUS_FILE = "antiflud_status.json"
MSK = timezone(timedelta(hours=3))  # UTC+3
ADMINS = [1678221039, 987654321]
ADMIN_ID = 1678221039

# Логгер
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Глобальная переменная для режима техобслуживания
is_maintenance = False

FLUD_WINDOW_SEC = 60
FLUD_MESSAGE_COUNT = 3
SIMILARITY_THRESHOLD = 0.8

# === ИНИЦИАЛИЗАЦИЯ БД ===
def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        # Пользователи чатаа
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chats (
                chat_id INTEGER PRIMARY KEY,
                invite_link TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        # Админы чата
        conn.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                level INTEGER NOT NULL CHECK (level BETWEEN 1 AND 6),
                is_frozen INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (chat_id, user_id)
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_rules (
                chat_id     INTEGER PRIMARY KEY,
                rules       TEXT NOT NULL,
                updated_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Замороженные админы
        conn.execute("""
            CREATE TABLE IF NOT EXISTS frozen_admins (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                frozen_by INTEGER NOT NULL,
                frozen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (chat_id, user_id)
            )
        """)
        # Логи модерации
        conn.execute("""
            CREATE TABLE IF NOT EXISTS moderation_logs (
                chat_id INTEGER NOT NULL,
                action TEXT NOT NULL,
                target_user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                reason TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        # Размеры "письки"
        conn.execute("""
            CREATE TABLE IF NOT EXISTS penis_sizes (
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                size INTEGER DEFAULT 0,
                last_played DATE,
                PRIMARY KEY (chat_id, user_id)
            )
        """)
        conn.commit()
# === ФУНКЦИИ РАБОТЫ С БД ===
def check_level(user_id: int, required_level: int, chat_id: int) -> bool:
    """Проверяет, имеет ли пользователь достаточный уровень."""
    # Владелец бота имеет полный доступ ко всем командам
    if user_id == 1678221039:
        return True

    # Для остальных — проверка по БД
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT level FROM admins WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id)
        ).fetchone()
        return row is not None and row[0] >= required_level

def get_user_size(user_id: int, chat_id: int) -> Optional[int]:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT size FROM penis_sizes WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id)
        ).fetchone()
        return row[0] if row else None

def check_level(user_id: int, required_level: int, chat_id: int) -> bool:
    """Проверяет, имеет ли пользователь достаточный уровень."""
    if user_id == 1678221039:  # Разработчик (всегда имеет доступ)
        return True
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT level FROM admins WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id)
        ).fetchone()
        return row is not None and row[0] >= required_level

def is_frozen(user_id: int, chat_id: int) -> bool:
    """Проверяет, заморожены ли права пользователя."""
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT 1 FROM frozen_admins WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id)
        ).fetchone()
        return row is not None

def get_user_level(user_id: int, chat_id: int) -> Optional[int]:
    """Возвращает уровень пользователя."""
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT level FROM admins WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id)
        ).fetchone()
        return row[0] if row else None

def update_user_size(user_id: int, chat_id: int, new_size: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT OR REPLACE INTO penis_sizes (chat_id, user_id, size, last_played) VALUES (?, ?, ?, DATE('now'))",
            (chat_id, user_id, new_size)
        )
        conn.commit()

def user_played_today(user_id: int, chat_id: int) -> bool:
    today = datetime.now(MSK).strftime("%Y-%m-%d")
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT 1 FROM penis_sizes WHERE chat_id = ? AND user_id = ? AND last_played = ?",
            (chat_id, user_id, today)
        ).fetchone()
    return row is not None

def log_moderation_action(action: str, target_id: int, moderator_id: int, reason: Optional[str], chat_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO moderation_logs (chat_id, action, target_user_id, moderator_id, reason) VALUES (?, ?, ?, ?, ?)",
            (chat_id, action, target_id, moderator_id, reason)
        )
        conn.commit()

def register_user(message: Message):
    """Добавляет/обновляет пользователя в глобальной БД при любом сообщении."""
    user = message.from_user
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO users
            (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
            """,
            (
                user.id,
                user.username,
                user.first_name,
                user.last_name
            )
        )
        conn.commit()

def get_user_info(identifier: str | int) -> Optional[dict]:
    """Возвращает данные пользователя из БД по ID или username (LOWER)."""
    with sqlite3.connect(DB_PATH) as conn:
        if isinstance(identifier, int):
            row = conn.execute(
                "SELECT user_id, username, first_name, last_name FROM users WHERE user_id = ?",
                (identifier,)
            ).fetchone()
        else:
            username = identifier.lstrip("@").strip().lower()
            row = conn.execute(
                "SELECT user_id, username, first_name, last_name FROM users WHERE LOWER(username) = ?",
                (username,)
            ).fetchone()

        if row:
            return {
                "user_id": row[0],
                "username": row[1] or f"ID{row[0]}",
                "first_name": row[2],
                "last_name": row[3]
            }
        return None

def get_target_from_args(args: list, message: Message) -> Tuple[Optional[int], Optional[str]]:
    """
    Извлекает target_id только:
    - из ответа на сообщение;
    - из первого аргумента (если это числовой ID).
    Username (@user) не поддерживается.
    """
    target_id = None
    username = None

    # 1. Ответ на сообщение
    if message.reply_to_message:
        replied = message.reply_to_message.from_user
        target_id = replied.id
        username = replied.username or str(replied.id)
        return target_id, username

    # 2. Первый аргумент — ID (число)
    if args:
        arg = args[0].strip()
        if arg.isdigit():
            target_id = int(arg)

    return target_id, username

def get_target_user_from_message(message, args):
    """
    Извлекает target_id и username из:
    - упоминания в тексте (/mute @username ...)
    - первого аргумента (если это числовой ID)
    Возвращает (target_id, username) или (None, None)
    """
    # 1. Ищем упоминания (@username) в тексте
    if message.entities:
        for entity in message.entities:
            if entity.type == "mention":
                # Получаем упомянутый username (без @)
                mentioned_username = message.text[entity.offset:entity.offset + entity.length]
                if mentioned_username.startswith("@"):
                    mentioned_username = mentioned_username[1:]
                # Здесь нужно запросить ID по username из БД или API — пример упрощён
                # В реальном коде: get_user_id_by_username(mentioned_username)
                return None, mentioned_username  # Пока возвращаем только username

    # 2. Проверяем первый аргумент на числовой ID
    if args and args[0].isdigit():
        return int(args[0]), None

    return None, None

def make_request(method: str, data: dict) -> dict:
    """
    Отправляет запрос к Telegram Bot API.
    :param method: метод API (например, 'restrictChatMember')
    :param data: словарь параметров
    :return: ответ в виде словаря
    """
    token = "8560378565:AAEHvQdBQteRZzaeGhmPas6bjOe4wk-tU-E"  # Укажите токен бота
    url = f"https://api.telegram.org/bot{token}/{method}"

    try:
        response = requests.post(url, json=data)
        return response.json()
    except Exception as e:
        return {"ok": False, "description": str(e)}

async def parse_target(message: Message, args: list) -> tuple[int | None, str | None]:
    target_id = None
    username = None

    # 1. Ищем упоминания (@username)
    if message.entities:
        for entity in message.entities:
            if entity.type == "mention":
                mentioned = message.text[entity.offset:entity.offset + entity.length]
                if mentioned.startswith("@"):
                    username = mentioned[1:]
                    # Пробуем получить ID (только для публичных юзернеймов)
                    try:
                        chat = await context.bot.get_chat(username)
                        target_id = chat.id
                    except Exception:
                        pass  # Оставляем target_id = None для fallback

    # 2. Проверяем первый аргумент на числовой ID
    if not target_id and args and args[0].isdigit():
        target_id = int(args[0])

    # 3. Проверяем ответ на сообщение
    if not target_id and message.reply_to_message:
        replied_user = message.reply_to_message.from_user
        target_id = replied_user.id
        username = replied_user.username

    return target_id, username

async def parse_target_extended(message: Message, args: list) -> tuple[int | None, str | None]:
    target_id = None
    username = None

    # 1. Ответ на сообщение (приоритет 1)
    if message.reply_to_message:
        replied_user = message.reply_to_message.from_user
        target_id = replied_user.id
        username = replied_user.username
        return target_id, username

    # 2. Упоминания в тексте (приоритет 2)
    if message.entities:
        for entity in message.entities:
            if entity.type == "mention":
                mentioned = message.text[entity.offset:entity.offset + entity.length]
                if mentioned.startswith("@"):
                    username = mentioned[1:]
                    # Пытаемся получить ID (только для публичных юзернеймов)
                    try:
                        chat = await context.bot.get_chat(username)
                        target_id = chat.id
                        return target_id, username
                    except Exception:
                        pass  # продолжаем поиск

    # 3. Первый аргумент как ID (приоритет 3)
    if args and args[0].isdigit():
        target_id = int(args[0])
        return target_id, None

    return None, None  # не удалось определить

def get_penis_data(chat_id: int, user_id: int) -> tuple[int, str | None]:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT size, last_played FROM penis_sizes WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id)
        ).fetchone()
        if row:
            return row[0], row[1]
        return 0, None

def update_penis_data(chat_id: int, user_id: int, new_size: int, last_played: str):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO penis_sizes (chat_id, user_id, size, last_played)
            VALUES (?, ?, ?, ?)
            """,
            (chat_id, user_id, new_size, last_played)
        )
        conn.commit()

def get_top_position(chat_id: int, user_id: int) -> int:
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT user_id FROM penis_sizes WHERE chat_id = ? ORDER BY size DESC",
            (chat_id,)
        ).fetchall()
        user_ids = [r[0] for r in rows]
        return user_ids.index(user_id) + 1 if user_id in user_ids else len(user_ids) + 1

def get_top_10(chat_id: int) -> list[tuple[int, int]]:
    """
    Возвращает топ‑10 пользователей в чате по полю `size`.
    Возвращает список кортежей: [(user_id, size), ...]
    """
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute(
            "SELECT user_id, size FROM penis_sizes WHERE chat_id = ? ORDER BY size DESC LIMIT 10",
            (chat_id,)
        ).fetchall()
    return rows

async def get_user_name(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> str:
    try:
        user = await context.bot.get_chat(user_id)
        if user.username:
            return f"@{user.username}"
        elif user.first_name:
            return user.first_name
        else:
            return f"ID{user_id}"
    except:
        return f"ID{user_id}"

async def private_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user_to_db(update.effective_user)

    # Проверяем, что это личный чат
    if update.effective_chat.type != "private":
        await update.message.reply_text(
            "Эта функция доступна только в личном чате с ботом."
        )
        return

    # Получаем текст сообщения
    text = update.message.text.strip().lower()

    # Обрабатываем команды
    if text == "/start":
        user_name = update.effective_user.first_name or "пользователь"
        response = (
            f"Привет, {user_name}! 👋\n\n"
            "Я бот для модерации чатов.\n"
            "Я умею мутить банить и наказывать\n"
            "Чтоб я мог наказывать в взаимодействовать с твоим чатом\n"
            "Дабавь меня в чат и выдай мне доступ к админке\n"
            "Мой разработчик: Fil\n"
            "Я буду еще обновляться в лучшую сторону"
        )
        await update.message.reply_text(response)

    elif text == "/help":
        response = (
            "🛠 Справочная информация:\n\n"
            "Этот бот предназначен для личного взаимодействия.\n\n"
            "Доступные команды:\n"
            "• /start — приветственное сообщение и список команд\n"
            "• /help — эта справочная информация\n\n"
            "Если у вас есть вопросы, напишите нам!"
        )
        await update.message.reply_text(response)

    elif text == "/pudlis":
        message = update.message
        text = message.text
        user_id = update.effective_user.id
        chat = update.effective_chat
        chat_type = chat.type
        chat_id = chat.id
        if user_id != ADMIN_ID:
            await message.reply_text("❌ Доступ запрещён. Эта команда доступна только администратору.")
            return

        chats = get_all_chats()
        if not chats:
            await message.reply_text("📭 Нет зарегистрированных чатов.")
            return

        lines = ["🔗 Список чатов и пригласительных ссылок:\n"]
        for db_chat_id, link in chats:
            try:
                # Обновляем ссылку (если бот всё ещё админ)
                new_link = await context.bot.export_chat_invite_link(db_chat_id)
                update_invite_link(db_chat_id, new_link)
                lines.append(f"{db_chat_id}: {new_link}")
            except Exception as e:
                logger.error(f"Не удалось обновить ссылку для {db_chat_id}: {e}")
                lines.append(f"{db_chat_id}: {link or 'ошибка/нет ссылки'}")

        response = "\n".join(lines)
        await message.reply_text(response, disable_web_page_preview=True)

            # Ответ на любые другие сообщения
        await update.message.reply_text(
            "Я понимаю команды: /start, /help. Попробуй одну из них!"
        )

def get_admin_status(chat_id: int, user_id: int) -> tuple[int, bool] | None:
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT level, is_frozen FROM admins WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id)
        ).fetchone()
        return (row[0], bool(row[1])) if row else None

def freeze_admin(chat_id: int, target_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE admins SET is_frozen = 1 WHERE chat_id = ? AND user_id = ?",
            (chat_id, target_id)
        )
        conn.commit()

def unfreeze_admin(chat_id: int, target_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE admins SET is_frozen = 0 WHERE chat_id = ? AND user_id = ?",
            (chat_id, target_id)
        )
        conn.commit()

def save_user_to_db(user: User):
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
            """,
            (
                user.id,
                user.username,
                user.first_name,
                user.last_name
            )
        )
        conn.commit()

def get_level_rights(level: int) -> str:
    rights = {
        1: "Базовые модерации (mute/unmute)",
        2: "Бан/разбан",
        3: "Заморозка админов",
        4: "Назначение админов / Полные права",
        6: "Владелец / Разработчик"
    }
    return rights.get(level, "Неизвестно")

async def profile_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    target_id = None
    username = None

    # 1. Определяем target_id: reply, ID из аргументов или текущий пользователь
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
        username = update.message.reply_to_message.from_user.username
    elif context.args and context.args[0].isdigit():
        target_id = int(context.args[0])
    else:
        target_id = update.effective_user.id
        username = update.effective_user.username

    # 2. Проверяем статус в чате
    try:
        user = await context.bot.get_chat_member(chat_id, target_id)
        member_status = "В чате"
        join_date = (
            user.join_date.strftime("%Y-%m-%d %H:%M")
            if user.join_date
            else "неизвестно"
        )
    except Exception as e:
        member_status = "Не в чате / Неизвестен"
        join_date = "—"

    # 3. Проверяем наличие в базе данных бота
    in_db = False
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT username FROM users WHERE user_id = ?",
            (target_id,)
        ).fetchone()
        if row:
            in_db = True
            # Обновляем username из БД, если его не было
            if not username:
                username = row[0]

    # 4. Проверяем статус администратора
    admin_info = None
    with sqlite3.connect(DB_PATH) as conn:
        row = conn.execute(
            "SELECT level, is_frozen FROM admins WHERE chat_id = ? AND user_id = ?",
            (chat_id, target_id)
        ).fetchone()
        if row:
            admin_info = {
                "level": row[0],
                "frozen": bool(row[1]),
                "rights": get_level_rights(row[0])
            }

    # 5. Формируем отображаемое имя с экранированием
    if username:
        display_name = html.escape(f"@{username}")
    else:
        display_name = f"[{target_id}]"

    # 6. Собираем ответ в MarkdownV2
    response = (
        f"📊 *Профиль пользователя:* {display_name}\n\n"
        f"• *ID:* {target_id}\n"
        f"• *Статус в чате:* {member_status}\n"
        f"• *Дата вступления:* {join_date}\n"
        f"• *В базе бота:* {'Да' if in_db else 'Нет'}\n"
    )

    if admin_info:
        response += (
            f"\n🛡️ *Администратор:*\n"
            f"• *Уровень:* {admin_info['level']}\n"
            f"• *Заморожен:* {'Да' if admin_info['frozen'] else 'Нет'}\n"
            f"• *Права:* {html.escape(admin_info['rights'])}"
        )
    else:
        response += "\n• *Администратор:* Нет"

    # 7. Отправляем сообщение
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=response,
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        # Если MarkdownV2 всё же сломался — отправляем без форматирования
        await context.bot.send_message(
            chat_id=chat_id,
            text=response.replace("*", ""),  # Убираем звёздочки
            parse_mode=None
        )

def load_rules() -> dict:
    """Загружает правила из JSON-файла"""
    if not os.path.exists(RULES_FILE):
        return {}
    try:
        with open(RULES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}

def save_rules(rules: dict) -> bool:
    """Сохраняет правила в JSON-файл"""
    try:
        with open(RULES_FILE, "w", encoding="utf-8") as f:
            json.dump(rules, f, ensure_ascii=False, indent=4)
        return True
    except IOError:
        return False

def check_admin_level(user_id: int, required_level: int, chat_id: int) -> bool:
    """Проверяет уровень прав администратора (пример для SQLite)"""
    try:
        with sqlite3.connect("bot.db") as conn:
            row = conn.execute(
                "SELECT level FROM admins WHERE chat_id = ? AND user_id = ?",
                (chat_id, user_id)
            ).fetchone()
            return row is not None and row[0] >= required_level
    except:
        return False  # На случай ошибки БД

# === Команда /rules ===

async def rules_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)  # JSON требует строки
    user_id = update.effective_user.id

    # Проверка прав (только lvl 4+)
    if not check_admin_level(user_id, 4, int(chat_id)):
        await update.message.reply_text("❌ Только администраторы lvl 4+ могут управлять правилами.")
        return

    args = context.args

    if not args:
        # Просмотр правил текущего чата
        rules = load_rules()
        if chat_id in rules:
            response = f"📜 Правила чата\n\n{rules[chat_id]}"
        else:
            response = "📜 Правила чата\n\nПравила не установлены."
        await update.message.reply_text(response)
    else:
        command = args[0].lower()

        if command == "set" and len(args) >= 2:
            # Установка новых правил
            new_rules = " ".join(args[1:])
            if len(new_rules) > 4000:
                await update.message.reply_text("❌ Максимум 4000 символов.")
                return

            rules = load_rules()
            rules[chat_id] = new_rules
            if save_rules(rules):
                await update.message.reply_text("✅ Правила обновлены.")
            else:
                await update.message.reply_text("❌ Ошибка сохранения в файл.")

        elif command == "get" and len(args) == 2:
            # Просмотр правил другого чата
            target_chat_id = args[1]
            rules = load_rules()
            if target_chat_id in rules:
                response = f"📜 Правила чата {target_chat_id}\n\n{rules[target_chat_id]}"
            else:
                response = f"📜 Правила чата {target_chat_id}\n\nНе найдены."
            await update.message.reply_text(response)

        elif command == "del":
            # Удаление правил текущего чата
            rules = load_rules()
            if chat_id in rules:
                del rules[chat_id]
                if save_rules(rules):
                    await update.message.reply_text("✅ Правила удалены.")
                else:
                    await update.message.reply_text("❌ Ошибка удаления.")
            else:
                await update.message.reply_text("🚫 Правил для этого чата нет.")

        else:
            # Справка по командам
            await update.message.reply_text(
                "🛠 Управление правилами\n\n"
                "/rules — показать правила текущего чата\n"
                "/rules set <текст> — установить правила\n"
                "/rules get <chat_id> — посмотреть правила другого чата\n"
                "/rules del — удалить правила текущего чата"
            )

def load_antiflud_config() -> bool:
    """Загружает настройки антифлуда для чатов."""
    if not os.path.exists(ANTIFLUD_STATUS_FILE ):
        return {}  # Возвращаем пустой словарь, если файла нет
    try:
        with open(ANTIFLUD_STATUS_FILE , "r", encoding="utf-8") as f:
            data = json.load(f)
            # Приводим ключи к str (если были int) и проверяем тип
            if isinstance(data, dict):
                return {str(k): v for k, v in data.items()}
            else:
                print(f"[WARNING] {ANTIFLUD_STATUS_FILE } содержит не словарь. Вернули.")
                return {}
    except (json.JSONDecodeError, IOError) as e:
        print(f"[ERROR] Не удалось прочитать {ANTIFLUD_STATUS_FILE }:. Вернули.")
        return {}

# Сохраняем статус антифлуда
def save_antiflud_config(enabled: bool) -> None:
    try:
        with open(ANTIFLUD_STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump({"enabled": enabled}, f, ensure_ascii=False, indent=4)
    except IOError as e:
        print(f"[ERROR]")

def load_history() -> dict:
    try:
        if os.path.exists(ANTIFLUD_HISTORY_FILE):
            with open(ANTIFLUD_HISTORY_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        return {}
    except Exception as e:
        logger.error(f"Ошибка чтения history: {e}")
        return {}

def save_history(history: dict) -> bool:
    try:
        with open(ANTIFLUD_HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=4)
        logger.info("История сохранена")
        return True
    except Exception as e:
        logger.error(f"Ошибка сохранения history: {e}")
        return False

async def antiflood_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = str(update.effective_chat.id)

    if not check_level(user_id, 4, chat_id):  # lvl ≥ 4
        await context.bot.send_message(chat_id=chat_id, text="❌ Требуется lvl 4+.")
        return

    config = load_antiflud_config()
    config[chat_id] = True
    save_antiflud_config(config)

    await update.message.reply_text("✅ Антифлуд включён для этого чата.")


async def antiflood_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = str(update.effective_chat.id)

    if not check_level(user_id, 4, chat_id):  # lvl ≥ 4
        await context.bot.send_message(chat_id=chat_id, text="❌ Требуется lvl 4+.")
        return

    config = load_antiflud_config()
    config[chat_id] = False
    save_antiflud_config(config)

    await update.message.reply_text("🛑 Антифлуд выключен для этого чата.")

def is_similar(a: str, b: str) -> bool:
    return SequenceMatcher(None, a, b).ratio() >= SIMILARITY_THRESHOLD

# --- Основная функция антифлуда ---
async def check_and_mute_for_flood(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = str(update.effective_chat.id)
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    message_text = update.message.text.strip()

    logger.info(f"[Антифлуд] Чат {chat_id}, пользователь {user_id} (@{username}): '{message_text}'")

    # 1. Проверка на пустое/короткое сообщение
    if not message_text or len(message_text) < 1:
        logger.debug("Пустое или слишком короткое сообщение")
        return

    # 2. Проверка статуса антифлуда
    config = load_antiflud_config()
    if chat_id not in config:
        config[chat_id] = True
        save_antiflud_config(config)
    if not config[chat_id]:
        logger.info("Антифлуд выключен для чата")
        return

    # 4. Загрузка истории
    history = load_history()
    if chat_id not in history:
        history[chat_id] = []
    elif not isinstance(history[chat_id], list):
        logger.warning(f"history['{chat_id}'] не список — пересоздаём")
        history[chat_id] = []

    now = datetime.now()

    # 5. Добавление сообщения в историю (с нормализацией времени)
    history[chat_id].append({
        "user_id": user_id,
        "username": username,
        "text": message_text,
        "timestamp": now.isoformat(timespec='milliseconds')  # Точное время
    })

    # 6. Сохранение истории (критично!)
    if not save_history(history):
        logger.error("Не удалось сохранить историю после добавления сообщения")
        return  # Прерываем, если история не сохранена


    # 7. Фильтрация сообщений за последний интервал
    cutoff = now - timedelta(seconds=FLUD_WINDOW_SEC)
    recent_messages = []
    for msg in history[chat_id]:
        try:
            # Нормализация формата времени (заменяем запятую на точку)
            ts_str = msg["timestamp"].replace(',', '.')
            msg_time = datetime.fromisoformat(ts_str)
            if msg_time >= cutoff:
                recent_messages.append(msg)
        except (ValueError, KeyError) as e:
            logger.warning(f"Ошибка парсинга времени: {msg.get('timestamp', 'N/A')} ({e})")
            continue
    history[chat_id] = recent_messages

    # 8. Сообщения текущего пользователя
    user_msgs = [msg for msg in recent_messages if msg["user_id"] == user_id]
    if len(user_msgs) < FLUD_MESSAGE_COUNT:
        logger.debug(f"Недостаточно сообщений: {len(user_msgs)} < {FLUD_MESSAGE_COUNT}")
        return

    # 9. Проверка схожести (с отладкой)
    last_n = user_msgs[-FLUD_MESSAGE_COUNT:]
    texts = [msg["text"] for msg in last_n]
    similar_pairs = 0

    for i in range(len(texts) - 1):
        # Убираем пробелы и приводим к нижнему регистру для надёжности
        a = texts[i].lower().strip()
        b = texts[i + 1].lower().strip()
        similarity = SequenceMatcher(None, a, b).ratio()
        logger.debug(f"Схожесть '{a}' и '{b}': {similarity:.3f} (порог: {SIMILARITY_THRESHOLD})")
        if similarity >= SIMILARITY_THRESHOLD:
            similar_pairs += 1

    logger.info(f"Найдено схожих пар: {similar_pairs} из {FLUD_MESSAGE_COUNT - 1}")


    # 10. Мут при обнаружении флуда
    if similar_pairs >= FLUD_MESSAGE_COUNT - 1:
        until_date = int((now + timedelta(minutes=10)).timestamp())
        try:
            permissions = ChatPermissions(
                can_send_messages=False,
                can_send_polls=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False
            )

            await context.bot.restrict_chat_member(
                chat_id=chat_id,
                user_id=user_id,
                permissions=permissions,
                until_date=until_date
            )
            logger.info(f"Пользователь {user_id} замучен на 10 минут")

            await update.message.reply_text(
                f"🔇 **Флуд обнаружен!**\n\n"
                f"Пользователь @{username} замучен на 10 минут.\n"
                f"Причина: {FLUD_MESSAGE_COUNT}+ одинаковых сообщений за {FLUD_WINDOW_SEC} сек.\n"
                f"Выдано ботом: {context.bot.first_name}",
                parse_mode="Markdown"
            )

            # Очистка истории нарушителя
            history[chat_id] = [
                msg for msg in history[chat_id] if msg["user_id"] != user_id
            ]
            save_history(history)

        except Exception as e:
            logger.error(f"Ошибка при муте {user_id}: {e}")

    save_history(history)

# === ОБРАБОТЧИК КОМАНД ===
async def handle_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_user_to_db(update.effective_user)
    global is_maintenance

    message: Message = update.message
    chat_id = message.chat_id
    user_id = message.from_user.id
    text = message.text.strip()
    args = text.split()[1:]  # Аргументы после команды
    cmd = text.lower().split()[0]
    message = update.message
    text = message.text
    user_id = update.effective_user.id
    chat = update.effective_chat
    chat_type = chat.type
    chat_id = chat.id

    # Режим техобслуживания
    if is_maintenance and user_id != 1678221039:
        await message.reply_text("⚙️ Бот в режиме техобслуживания. Подождите.")
        return

    try:

        # Общий чат — команды
        if cmd == "/help":
            chat_id = update.effective_chat.id
            user_id = update.effective_user.id

            # Получаем уровень админа (если есть)
            with sqlite3.connect(DB_PATH) as conn:
                row = conn.execute(
                    "SELECT level FROM admins WHERE chat_id = ? AND user_id = ?",
                    (chat_id, user_id)
                ).fetchone()
                admin_level = row[0] if row else 0  # 0 — не админ


            # Формируем список доступных команд в зависимости от уровня
            help_text = "📜 **Доступные команды**:\n\n"

            # Базовые команды (доступны всем)
            help_text += (
                "• /help — справка\n"
                "• /dick — сыграть в 'письку'\n"
                "• /top — топ размеров\n"
                "• /profile — ваш профиль\n"
                "• /staff — список админов\n"
                "• /bot — статус бота\n"
            )

            # Команды для админов уровня 1+
            if admin_level >= 1:
                help_text += "• /awarn — сообщить о нарушении (lvl 1+)\n"


            # Команды для админов уровня 2+
            if admin_level >= 2:
                help_text += (
                    "• /mute @user [время] [причина] — мут (lvl 2+)\n"
                    "• /unmute @user — снять мут (lvl 2+)\n"
                )

            # Команды для админов уровня 3+
            if admin_level >= 3:
                help_text += (
                    "• /ban @user [время] [причина] — бан (lvl 3+)\n"
                    "• /unban @user — снять бан (lvl 3+)\n"
                )

            # Команды для админов уровня 4+
            if admin_level >= 4:
                help_text += (
                    "• /freeze @user — заморозить права (lvl 4+)\n"
                    "• /unfreeze @user — разморозить права (lvl 4+)\n"
                )

            # Команды для админов уровня 5+
            if admin_level >= 5:
                help_text += "• /id @user — ID пользователя (lvl 5+)\n"


            # Команды для разработчиков (уровень 6)
            if admin_level == 6:
                help_text += (
                    "• /maintenance_on — включить техобслуживание (разраб)\n"
                    "• /maintenance_off — выключить техобслуживание (разраб)\n"
                )


            await update.message.reply_text(help_text, parse_mode="Markdown")

        elif cmd == "/bot":
            text = ("Бот связан с базой данных и работает")
            await message.reply_text(text, parse_mode="Markdown")

        elif cmd == "/rules":
            await rules_command(update, context)

        elif cmd == "/freeze":
            chat_id = update.effective_chat.id
            moderator_id = update.effective_user.id

            # 1. Проверка: может ли текущий модератор замораживать?
            mod_status = get_admin_status(chat_id, moderator_id)
            if mod_status and mod_status[1]:  # is_frozen == 1
                await update.message.reply_text("❌ Вы заморожены.")
                return

            if not check_level(moderator_id, 4, chat_id):  # lvl ≥ 4
                await context.bot.send_message(chat_id=chat_id, text="❌ Требуется lvl 4+.")
                return

            # 2. Разбор аргументов
            args = context.args
            if len(args) < 1:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ Укажите пользователя: /freeze <ID/username/reply> [причина]"
                )
                return

            target_id, username = None, None
            reason = " ".join(args[1:]) if len(args) > 1 else "без причины"

            # 3. Определение target_id (reply, ID, username)
            if update.message.reply_to_message:
                target_id = update.message.reply_to_message.from_user.id
                username = update.message.reply_to_message.from_user.username
            elif args[0].isdigit():
                target_id = int(args[0])
            else:
                username_input = args[0].lstrip('@').lower()
                with sqlite3.connect(DB_PATH) as conn:
                    row = conn.execute(
                        "SELECT user_id FROM users WHERE LOWER(username) = ?",
                        (username_input,)
                    ).fetchone()
                    if row:
                        target_id = row[0]
                        username = username_input
                    else:
                        try:
                            user = await context.bot.get_chat(username_input)
                            target_id = user.id
                            username = user.username or username_input
                        except:
                            await context.bot.send_message(
                                chat_id=chat_id,
                                text=f"❌ Не найден: @{username_input}"
                            )
                            return

            if not target_id:
                await context.bot.send_message(chat_id=chat_id, text="❌ ID не определён.")
                return

            # 4. Проверка: является ли target администратором чата?
            target_status = get_admin_status(chat_id, target_id)
            if not target_status:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ {f'@{username}' if username else f'[{target_id}]'} не является администратором."
                )
                return

            # 5. Замораживаем (обновляем is_frozen=1)
            try:
                with sqlite3.connect(DB_PATH) as conn:
                    conn.execute(
                        "UPDATE admins SET is_frozen = 1 WHERE chat_id = ? AND user_id = ?",
                        (chat_id, target_id)
                    )
                    conn.commit()

                display_name = f"@{username}" if username else f"[{target_id}]"
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"❄️ {display_name} заморожен.\n"
                        f"• Причина: {reason}\n"
                        f"• Заморозил: {update.effective_user.first_name}"
                    ),
                    parse_mode="Markdown"
                )
                log_moderation_action("freeze", target_id, moderator_id, reason, chat_id)

            except Exception as e:
                await context.bot.send_message(chat_id=chat_id, text=f"❌ Ошибка: {str(e)}")

        elif cmd == "/unfreeze":
            chat_id = update.effective_chat.id
            moderator_id = update.effective_user.id


            # 1. Проверка: может ли текущий модератор размораживать?
            mod_status = get_admin_status(chat_id, moderator_id)
            if mod_status and mod_status[1]:
                await update.message.reply_text("❌ Вы заморожены.")
                return

            if not check_level(moderator_id, 4, chat_id):  # lvl ≥ 4
                await context.bot.send_message(chat_id=chat_id, text="❌ Требуется lvl 4+.")
                return

            # 2. Разбор аргументов
            args = context.args
            if len(args) < 1:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ Укажите пользователя: /unfreeze <ID/username/reply>"
                )
                return

            target_id, username = None, None

            # 3. Определение target_id (reply, ID, username)
            if update.message.reply_to_message:
                target_id = update.message.reply_to_message.from_user.id
                username = update.message.reply_to_message.from_user.username
            elif args[0].isdigit():
                target_id = int(args[0])
            else:
                username_input = args[0].lstrip('@').lower()  # Объявляем с подчёркиванием

                with sqlite3.connect(DB_PATH) as conn:
                    row = conn.execute(
                        "SELECT user_id FROM users WHERE LOWER(username) = ?",
                        (username_input,)  # Используем ту же переменную
                    ).fetchone()
                    if row:
                        target_id = row[0]
                        username = username_input  # Используем ту же переменную
                    else:
                        try:
                            user = await context.bot.get_chat(username_input)  # Используем ту же переменную
                            target_id = user.id
                            username = user.username or username_input  # Используем ту же переменную
                        except:
                            await context.bot.send_message(
                                chat_id=chat_id,
                                text=f"❌ Не найден: @{username_input}"  # Используем ту же переменную
                            )
                            return

            if not target_id:
                await context.bot.send_message(chat_id=chat_id, text="❌ ID не определён.")
                return

            # 4. Проверка: заморожен ли target?
            target_status = get_admin_status(chat_id, target_id)
            if not target_status or not target_status[1]:  # is_frozen == 0
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ {f'@{username}' if username else f'[{target_id}]'} не заморожен."
                )
                return

            # 5. Размораживаем (обновляем is_frozen=0)
            try:
                with sqlite3.connect(DB_PATH) as conn:
                    conn.execute(
                        "UPDATE admins SET is_frozen = 0 WHERE chat_id = ? AND user_id = ?",
                        (chat_id, target_id)
                    )
                    conn.commit()

                display_name = f"@{username}" if username else f"[{target_id}]"
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"🔥 {display_name} разморожен.\n• Разморозил: {update.effective_user.first_name}",
                    parse_mode="Markdown"
                )
                log_moderation_action("unfreeze", target_id, moderator_id, "", chat_id)

            except Exception as e:
                await context.bot.send_message(chat_id=chat_id, text=f"❌ Ошибка: {str(e)}")


        elif cmd == "/top":
            chat_id = update.effective_chat.id

            # Получаем топ‑10
            top_users = get_top_10(chat_id)


            if not top_users:
                await update.message.reply_text("В этом чате ещё никто не играл в «Письку».")
                return

            # Формируем сообщение
            lines = ["🏆 Топ‑10 «Писек» в этом чате:\n"]

            for i, (user_id, size) in enumerate(top_users, 1):
                name = await get_user_name(context, user_id)
                lines.append(f"{i}. {name} — {size} см")


            message = "\n".join(lines)
            await update.message.reply_text(message)

        elif cmd == "/unban":
            chat_id = update.effective_chat.id
            moderator_id = update.effective_user.id

            # 1. Проверка заморозки модератора
            mod_status = get_admin_status(chat_id, moderator_id)
            if mod_status and mod_status[1]:
                await update.message.reply_text("❌ Вы заморожены.")
                return

            # 2. Проверка уровня доступа (lvl ≥ 3)
            if not check_level(moderator_id, 3, chat_id):
                await context.bot.send_message(chat_id=chat_id, text="❌ Требуется lvl 3+.")
                return

            # 3. Разбор аргументов
            args = context.args
            if len(args) < 1:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ Укажите пользователя: /unban <ID/username/reply> [сообщение]"
                )
                return

            target_id, username = None, None
            custom_message = "Вы были разблокированы. Можете вернуться в чат!"

            # 4. Определение target_id (reply, ID, username)
            if update.message.reply_to_message:
                target_id = update.message.reply_to_message.from_user.id
                username = update.message.reply_to_message.from_user.username
            elif args[0].isdigit():
                target_id = int(args[0])
            else:
                username_input = args[0].lstrip('@').lower()  # <-- Здесь было: usernameinput

                with sqlite3.connect(DB_PATH) as conn:
                    row = conn.execute(
                        "SELECT user_id FROM users WHERE LOWER(username) = ?",
                        (username_input,)  # <-- Здесь было: (usernameinput,)
                    ).fetchone()
                    if row:
                        target_id = row[0]
                        username = username_input  # <-- Здесь было: usernameinput
                    else:
                        try:
                            user = await context.bot.get_chat(username_input)  # <-- Здесь было: usernameinput
                            target_id = user.id
                            username = user.username or username_input  # <-- Здесь было: usernameinput
                        except:
                            await context.bot.send_message(
                                chat_id=chat_id,
                                text=f"❌ Не найден: @{username_input}"  # <-- Здесь было: usernameinput
                            )
                            return

            if not target_id:
                await context.bot.send_message(chat_id=chat_id, text="❌ ID не определён.")
                return

            # 5. Извлекаем кастомное сообщение
            if len(args) > 1:
                custom_message = " ".join(args[1:])

            # 6. Снимаем бан
            try:
                await context.bot.unban_chat_member(chat_id=chat_id, user_id=target_id)

                # 7. Формируем текст для чата
                display_name = f"@{username}" if username else f"[{target_id}]"
                chat_text = f"✅ {display_name} разбанен."
                if custom_message:
                    chat_text += f"\n• Сообщение: {custom_message}"
                await context.bot.send_message(chat_id=chat_id, text=chat_text, parse_mode="Markdown")

                # 8. Получаем активную пригласительную ссылку чата
                try:
                    # Получаем все invite links чата
                    invite_links = await context.bot.export_chat_invite_link(chat_id)
                    invite_url = invite_links  # В новых версиях это прямая ссылка

                except Exception as link_err:
                    invite_url = None
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"⚠️ Не удалось получить ссылку для приглашения: {link_err}"
                    )

                # 9. Отправляем личное сообщение с приглашением
                if invite_url:
                    pm_text = (
                        f"Вы были разблокированы в чате «{update.effective_chat.title or 'этот чат'}».\n\n"
                        f"{custom_message}\n\n"
                        f"Чтобы вернуться, перейдите по ссылке:\n{invite_url}"
                    )
                    try:
                        await context.bot.send_message(chat_id=target_id, text=pm_text)
                        log_moderation_action("unban", target_id, moderator_id, f"PM+invite sent: {custom_message}", chat_id)
                    except Exception as pm_err:
                        # Если не можем написать в PM — сообщаем в чат
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=(
                                f"{display_name} разбанен, но PM не отправлен.\n"
                                "Пользователь должен самостоятельно перейти по ссылке, чтобы вернуться в чат."
                            )
                        )
                        log_moderation_action("unban", target_id, moderator_id, f"PM failed, invite: {invite_url}", chat_id)
                else:
                    # Если нет ссылки — просто уведомляем, что нужно вернуться вручную
                    try:
                        await context.bot.send_message(
                            chat_id=target_id,
                            text=(
                                f"Вы были разблокированы в чате.\n\n"
                                f"{custom_message}\n\n"
                                "Чтобы вернуться в чат, найдите его в списке чатов или попросите ссылку у администратора."
                            )
                        )
                        log_moderation_action("unban", target_id, moderator_id, "PM sent (no invite link)", chat_id)
                    except:
                        await context.bot.send_message(
                            chat_id=chat_id,
                            text=f"{display_name} разбанен. Нет ссылки и не удалось отправить PM."
                        )
                        log_moderation_action("unban", target_id, moderator_id, "No invite, PM failed", chat_id)

            except Exception as e:
                await context.bot.send_message(chat_id=chat_id, text=f"❌ Ошибка при разбане: {str(e)}")

        elif cmd == "/dick":
            user_id = update.effective_user.id
            chat_id = update.effective_chat.id
            username = update.effective_user.first_name or f"Пользователь {user_id}"

            # Получаем текущие данные
            current_size, last_played_str = get_penis_data(chat_id, user_id)

            # Проверяем, играл ли сегодня
            today = date.today().isoformat()  # YYYY-MM-DD
            if last_played_str == today:
                await update.message.reply_text(
                    f"{username}, твоя следующая попытка завтра!\n"
                    "Попробуй снова завтра."
                )
                return

            # Генерируем изменение (-5 до +10)
            change = random.randint(-5, 10)
            new_size = current_size + change

            # Обновляем БД
            update_penis_data(chat_id, user_id, new_size, today)

            # Получаем позицию в топе
            position = get_top_position(chat_id, user_id)

            # Формируем текст изменения
            if change > 0:
                verb = f"вырос на {change} см"
            elif change < 0:
                verb = f"сократился на {-change} см"
            else:
                verb = "не изменился"

            # Отправляем ответ
            message = (
                f"{username}, твой писюн {verb}.\n"
                f"Теперь он равен {new_size} см.\n"
                f"Ты занимаешь {position} место в топе.\n"
                "Следующая попытка завтра!"
            )
            await update.message.reply_text(message)

        elif cmd == "/setadmin":
            chat_id = update.effective_chat.id
            moderator_id = update.effective_user.id

            # 1. Проверка: заморожен ли текущий модератор?
            mod_status = get_admin_status(chat_id, moderator_id)
            if mod_status and mod_status[1]:  # is_frozen == 1
                await update.message.reply_text("❌ Вы заморожены.")
                return

            # 2. Проверка уровня доступа (только lvl 4 может назначать админов)
            if not check_level(moderator_id, 4, chat_id):
                await context.bot.send_message(chat_id=chat_id, text="❌ Требуется lvl 4+.")
                return

            # 3. Разбор аргументов
            args = context.args
            if len(args) < 2 or not args[1].isdigit():
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ Используйте: /setadmin <ID/username/reply> <уровень (1–4)> [причина]"
                )
                return

            target_id, username = None, None
            level = int(args[1])
            reason = " ".join(args[2:]) if len(args) > 2 else "без причины"

            # Проверка уровня: 1–4
            if level < 1 or level > 4:
                await context.bot.send_message(chat_id=chat_id, text="❌ Уровень должен быть от 1 до 4.")
                return

            # 4. Определение target_id (reply, ID, username)
            if update.message.reply_to_message:
                target_id = update.message.reply_to_message.from_user.id
                username = update.message.reply_to_message.from_user.username
            elif args[0].isdigit():
                target_id = int(args[0])
            else:
                username_input = args[0].lstrip('@').lower()
                with sqlite3.connect(DB_PATH) as conn:
                    row = conn.execute(
                        "SELECT user_id FROM users WHERE LOWER(username) = ?",
                        (username_input,)
                    ).fetchone()
                    if row:
                        target_id = row[0]
                        username = username_input
                    else:
                        try:
                            user = await context.bot.get_chat(username_input)
                            target_id = user.id
                            username = user.username or username_input
                        except:
                            await context.bot.send_message(
                                chat_id=chat_id,
                                text=f"❌ Не найден: @{username_input}"
                            )
                            return

            if not target_id:
                await context.bot.send_message(chat_id=chat_id, text="❌ ID не определён.")
                return

            # 5. Проверка: не является ли target ботом?
            if target_id == context.bot.id:
                await context.bot.send_message(chat_id=chat_id, text="❌ Нельзя назначить ботом администратором.")
                return

            # 6. Сохраняем/обновляем в БД
            try:
                with sqlite3.connect(DB_PATH) as conn:
                    # Проверяем, есть ли уже запись
                    exists = conn.execute(
                        "SELECT 1 FROM admins WHERE chat_id = ? AND user_id = ?",
                        (chat_id, target_id)
                    ).fetchone()

                    if exists:
                        # Обновляем уровень
                        conn.execute(
                            "UPDATE admins SET level = ?, is_frozen = 0, updated_at = CURRENT_TIMESTAMP WHERE chat_id = ? AND user_id = ?",
                            (level, chat_id, target_id)
                        )
                    else:
                        # Добавляем нового админа
                        conn.execute(
                            "INSERT INTO admins (chat_id, user_id, level, is_frozen) VALUES (?, ?, ?, 0)",
                            (chat_id, target_id, level)
                        )

                    conn.commit()

                display_name = f"@{username}" if username else f"[{target_id}]"
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"🛡️ {display_name} назначен администратором.\n"
                        f"• Уровень: {level}\n"
                        f"• Причина: {reason}\n"
                        f"• Назначил: {update.effective_user.first_name}"
                    ),
                    parse_mode="Markdown"
                )
                log_moderation_action("setadmin", target_id, moderator_id, f"level={level}, {reason}", chat_id)

            except Exception as e:
                await context.bot.send_message(chat_id=chat_id, text=f"❌ Ошибка: {str(e)}")

        elif cmd == "/getowner":
            if user_id != 1678221039:
                await message.reply_text("❌ Доступ запрещён.")
                return

            with sqlite3.connect(DB_PATH) as conn:
                # Записываем владельца в таблицу admins с lvl 6
                conn.execute(
                    "INSERT OR REPLACE INTO admins (chat_id, user_id, level) VALUES (?, ?, 6)",
                    (chat_id, user_id)
                )
                conn.commit()

            await message.reply_text("✅ Вы получили уровень 6 (Владелец).")
            return

        elif cmd == "/staff":
            with sqlite3.connect(DB_PATH) as conn:
                rows = conn.execute(
                    "SELECT user_id, level FROM admins WHERE chat_id = ? ORDER BY level DESC",
                    (chat_id,)
                ).fetchall()

            if not rows:
                await message.reply_text("👥 Нет зарегистрированных админов.")
                return

            text = "👥 <b>Список админов</b>:\n\n"
            level_names = {
                6: "Владелец",
                5: "Руководитель",
                4: "Зам. руководителя",
                3: "Старший модератор",
                2: "Младщий модератор",
                1: "Кандидат"
            }
            for user_id, level in rows:
                username = f"ID {user_id}"
                if (user := update.effective_user) and user.id == user_id:
                    username = "@" + (user.username or "no_username")
                text += f"• <b>{level_names.get(level, f'LVL {level}')}</b> ({level}): {username}\n"

            await message.reply_text(text, parse_mode="HTML")

        elif cmd == "/rules":
            await rules_command(update, context)

        elif cmd == "/mute":
            chat_id = update.effective_chat.id
            moderator_id = update.effective_user.id

            # 1. Проверка заморозки админа
            mod_status = get_admin_status(chat_id, moderator_id)
            if mod_status and mod_status[1]:  # is_frozen == 1
                await update.message.reply_text("❌ Вы заморожены и не можете применять модерации.")
                return

            # 2. Проверка уровня доступа (lvl ≥ 2)
            if not check_level(moderator_id, 2, chat_id):
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ Требуется лвл 2+ для мута."
                )
                return

            # 3. Разбор аргументов
            args = context.args
            if len(args) < 2:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "❌ Недостаточно аргументов.\n"
                        "Используйте:\n"
                        "/mute <цель> <длительность> [причина]\n\n"
                        "Примеры:\n"
                        "/mute 123456789 1h Спам\n"
                        "/mute @username 30m Флуд\n"
                        "[ответ на сообщение] /mute 2h Оффтоп"
                    )
                )
                return

            # 4. Определение target_id
            target_id = None
            username = None

            # a) Если есть reply — берём ID из replied message
            if update.message.reply_to_message:
                replied_user = update.message.reply_to_message.from_user
                target_id = replied_user.id
                username = replied_user.username

            # b) Если первый аргумент — число, считаем это user_id
            elif args[0].isdigit():
                target_id = int(args[0])

            # c) Если первый аргумент — username (@...) или просто имя
            else:
                username_input = args[0].lstrip('@').lower()  # Приводим к нижнему регистру

                # Ищем в БД (с учётом регистра-независимого поиска)
                with sqlite3.connect(DB_PATH) as conn:
                    row = conn.execute(
                        "SELECT user_id, username FROM users WHERE LOWER(username) = ?",
                        (username_input,)
                    ).fetchone()

                    if row:
                        target_id = row[0]
                        username = row[1] or username_input  # Берём сохранённое username или используем введённое
                    else:
                        # Если не нашли в БД — пробуем через API Telegram
                        try:
                            user = await context.bot.get_chat(username_input)
                            target_id = user.id
                            username = user.username or username_input
                        except:
                            await context.bot.send_message(
                                chat_id=chat_id,
                                text=f"❌ Не удалось найти пользователя: @{username_input}"
                            )
                            return

            if not target_id:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ Не удалось определить ID пользователя."
                )
                return

            # 5. Валидация длительности
            duration_str = args[1]
            valid_durations = {
                **{f"{m}m": m * 60 for m in range(1, 61)},
                **{f"{h}h": h * 3600 for h in range(1, 25)},
                **{f"{d}d": d * 86400 for d in range(1, 31)}
            }
            if duration_str not in valid_durations:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        "❌ Неверная длительность.\n"
                        "Допустимые форматы:\n"
                        "- 1m–60m (минуты)\n"
                        "- 1h–24h (часы)\n"
                        "- 1d–30d (дни)\n\n"
                        "Примеры: 30m, 2h, 5d"
                    )
                )
                return
            duration_sec = valid_durations[duration_str]
            until_date = int(time.time()) + duration_sec

            # 6. Причина (опционально)
            reason = " ".join(args[2:]) if len(args) >= 3 else "не указана"

            # 7. Настройки прав (полный мут)
            permissions = ChatPermissions(
                can_send_messages=False,
                can_send_other_messages=False,
                can_send_polls=False,
                can_add_web_page_previews=False,
                can_change_info=False,
                can_invite_users=False,
                can_pin_messages=False
            )

            # 8. Применяем мут
            try:
                await context.bot.restrict_chat_member(
                    chat_id=chat_id,
                    user_id=target_id,
                    permissions=permissions,
                    until_date=until_date
                )

                # 9. Формируем сообщение
                display_name = f"@{username}" if username else f"[{target_id}]"
                end_time = datetime.fromtimestamp(until_date).strftime("%d.%m.%Y %H:%M")

                await context.bot.send_message(
                    chat_id=chat_id,
                    text=(
                        f"{display_name} 🔇 замучен.\n"
                        f"• До: {end_time}\n"
                        f"• Длительность: {duration_str}\n"
                        f"• Причина: {reason}"
                    ),
                    parse_mode="Markdown"
                )

                log_moderation_action("mute", target_id, moderator_id, reason, chat_id)

            except Exception as e:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"❌ Не удалось применить мут: {str(e)}"
                )

        elif text == "/start" and chat_type in ["group", "supergroup"]:
            try:
                # Получаем текущую пригласительную ссылку
                invite_link = await context.bot.export_chat_invite_link(chat_id)
                add_chat_to_db(chat_id, invite_link)
                await message.reply_text(
                    f"Я помощник по модерации чата\n"
                    f"Можно связаться с моим разработчиком через бота @q_shimokuroda\n"
                    f"Я буду помогать в модерации по чату и улучшать безопасность в чате"
                    f"Так же пропиши /getadmin чтоб тебе выдалась админка в чате"
                )
            except Exception as e:
                logger.error(f"Ошибка при добавлении чата {chat_id}: {e}")
            return

        elif cmd == "/unmute":
            chat_id = update.effective_chat.id
            moderator_id = update.effective_user.id

            # Проверка заморозки
            mod_status = get_admin_status(chat_id, moderator_id)
            if mod_status and mod_status[1]:
                await update.message.reply_text("❌ Вы заморожены.")
                return

            # Уровень доступа ≥ 2
            if not check_level(moderator_id, 2, chat_id):
                await context.bot.send_message(chat_id=chat_id, text="❌ Требуется lvl 2+.")
                return

            # Разбор аргументов
            args = context.args
            if len(args) < 1:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ Укажите пользователя: /unmute <ID/username/reply>"
                )
                return

            target_id = None
            username = None

            # a) Reply
            if update.message.reply_to_message:
                target_id = update.message.reply_to_message.from_user.id
                username = update.message.reply_to_message.from_user.username

            # b) ID
            elif args[0].isdigit():
                target_id = int(args[0])

            # c) Username
            else:
                username_input = args[0].lstrip('@').lower()
                with sqlite3.connect(DB_PATH) as conn:
                    row = conn.execute(
                        "SELECT user_id FROM users WHERE LOWER(username) = ?",
                        (username_input,)
                    ).fetchone()
                    if row:
                        target_id = row[0]
                        username = username_input
                    else:
                        try:
                            user = await context.bot.get_chat(username_input)
                            target_id = user.id
                            username = user.username or username_input
                        except:
                            await context.bot.send_message(
                                chat_id=chat_id,
                                text=f"❌ Не найден пользователь: @{username_input}"
                            )
                            return

            if not target_id:
                await context.bot.send_message(chat_id=chat_id, text="❌ Не удалось определить ID.")
                return

            # Снятие мута (восстановление прав)
            permissions = ChatPermissions(
                can_send_messages=True,
                can_send_other_messages=True,
                can_send_polls=True,
                can_add_web_page_previews=True,
                can_change_info=False,  # обычно не возвращаем
                can_invite_users=False,
                can_pin_messages=False
            )

            try:
                await context.bot.restrict_chat_member(
                    chat_id=chat_id,
                    user_id=target_id,
                    permissions=permissions
                )
                display_name = f"@{username}" if username else f"[{target_id}]"
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"✅ {display_name} размучен.",
                    parse_mode="Markdown"
                )
                log_moderation_action("unmute", target_id, moderator_id, "", chat_id)
            except Exception as e:
                await context.bot.send_message(chat_id=chat_id, text=f"❌ Ошибка: {str(e)}")

        elif cmd == "/ban":
            chat_id = update.effective_chat.id

            # 1. Объявляем moderator_id В САМОМ НАЧАЛЕ
            moderator_id = update.effective_user.id

            # 2. Проверяем заморозку (используем moderator_id)
            mod_status = get_admin_status(chat_id, moderator_id)
            if mod_status and mod_status[1]:  # is_frozen == 1
                await update.message.reply_text("❌ Вы заморожены.")
                return

            # 3. Проверяем уровень доступа (используем moderator_id)
            if not check_level(moderator_id, 3, chat_id):  # lvl ≥ 3
                await context.bot.send_message(chat_id=chat_id, text="❌ Требуется lvl 3+.")
                return

            # 4. Разбор аргументов
            args = context.args
            if len(args) < 1:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ Укажите пользователя: /ban <ID/username/reply> [причина]"
                )
                return

            target_id, username = None, None

            # 5. Определяем target_id (reply, ID, username)
            if update.message.reply_to_message:
                target_id = update.message.reply_to_message.from_user.id
                username = update.message.reply_to_message.from_user.username
            elif args[0].isdigit():
                target_id = int(args[0])
            else:
                username_input = args[0].lstrip('@').lower()
                with sqlite3.connect(DB_PATH) as conn:
                    row = conn.execute(
                        "SELECT user_id FROM users WHERE LOWER(username) = ?",
                        (username_input,)
                    ).fetchone()
                    if row:
                        target_id = row[0]
                        username = username_input
                    else:
                        try:
                            user = await context.bot.get_chat(username_input)
                            target_id = user.id
                            username = user.username or username_input
                        except:
                            await context.bot.send_message(
                                chat_id=chat_id,
                                text=f"❌ Не найден: @{username_input}"
                            )
                            return

            if not target_id:
                await context.bot.send_message(chat_id=chat_id, text="❌ ID не определён.")
                return

            # 6. Причина (опционально)
            reason = " ".join(args[1:]) if len(args) > 1 else "без причины"

            # 7. Применяем бан
            try:
                await context.bot.ban_chat_member(chat_id=chat_id, user_id=target_id)
                display_name = f"@{username}" if username else f"[{target_id}]"
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"🚫 {display_name} забанен.\n• Причина: {reason}",
                    parse_mode="Markdown"
                )
                log_moderation_action("ban", target_id, moderator_id, reason, chat_id)
            except Exception as e:
                await context.bot.send_message(chat_id=chat_id, text=f"❌ Ошибка: {str(e)}")

        elif cmd == "/kick":
            chat_id = update.effective_chat.id
            moderator_id = update.effective_user.id
            mod_status = get_admin_status(chat_id, moderator_id)
            if mod_status and mod_status[1]:
                await update.message.reply_text("❌ Вы заморожены и не можете применять модерации.")
                return

            if not check_level(user_id, 2, chat_id):
                await context.bot.send_message(chat_id, "❌ Требуется лвл 2+ для кика.")
                return

            args = (message.text or "").split()[1:]
            if len(args) < 1:
                await context.bot.send_message(chat_id, "❌ Укажите пользователя.")
                return

            target_id, username = await parse_target(message, args)
            if not target_id:
                await context.bot.send_message(chat_id, "❌ Не удалось определить пользователя.")
                return

            reason = " ".join(args[1:]) if len(args) > 1 else "не указана"

            try:
                # Проверяем, состоит ли пользователь в чате
                member = await context.bot.get_chat_member(chat_id, target_id)
                if member.status in ["left", "kicked"]:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"❌ Пользователь {target_id} уже не состоит в чате."
                    )
                    return

                # Баним и сразу разбаним (кик)
                await context.bot.ban_chat_member(chat_id=chat_id, user_id=target_id)
                await context.bot.unban_chat_member(chat_id=chat_id, user_id=target_id)

                display_name = f"@{username}" if username else f"[{target_id}]"
                await context.bot.send_message(
                    chat_id=chat_id,
                    text=f"👋 {display_name} выкинут из чата.\n• Причина: {reason}",
                    parse_mode="Markdown"
                )
                log_moderation_action("kick", target_id, user_id, reason, chat_id)

            except Exception as e:
                error_msg = str(e)
                if "not a member" in error_msg:
                    error_msg = "Пользователь не состоит в чате."
                elif "user is administrator" in error_msg:
                    error_msg = "Нельзя кикнуть администратора."
                await context.bot.send_message(chat_id, f"❌ Не удалось выкинуть: {error_msg}")

        elif cmd == "/unfreeze":
            if user_id != 1678221039 and (not check_level(user_id, 4, chat_id) or is_frozen(user_id, chat_id)):
                await message.reply_text("❌ Требуется lvl 4+ и активные права для /unfreeze.")
                return

            target_id, username = get_target_from_args(args, message)
            if not target_id:
                await message.reply_text("❌ Укажите пользователя (ответ, @username или ID).")
                return

            with sqlite3.connect(DB_PATH) as conn:
                cursor = conn.execute(
                    "DELETE FROM frozen_admins WHERE chat_id = ? AND user_id = ?",
                    (chat_id, target_id)
                )
                if cursor.rowcount == 0:
                    await message.reply_text(f"⚠️ Пользователь @{username or f'ID {target_id}'} не заморожен.")
                    return
                conn.commit()

            await message.reply_text(
                f"✅ Права @{username or f'ID {target_id}'} разморожены.",
                parse_mode="Markdown"
            )
            log_moderation_action("unfreeze", target_id, user_id, None, chat_id)


        elif cmd == "/id":
            if not check_level(user_id, 5, chat_id) or is_frozen(user_id, chat_id):
                await message.reply_text("❌ Требуется lvl 5+ и активные права для /id.")
                return

            target_id, username = get_target_from_args(args, message)
            if not target_id:
                await message.reply_text("❌ Укажите пользователя (ответ, @username или ID).")
                return

            level = get_user_level(target_id, chat_id) or "не админ"

            await message.reply_text(
                f"🔍 **Информация о пользователе**:\n"
                f"• ID: {target_id}\n"
                f"• Username: @{username or 'не указан'}\n"
                f"• Уровень в чате: {level}",
                parse_mode="Markdown"
            )

        else:
            await message.reply_text("⚠️ Неизвестная команда. Используйте /help.")

    except Exception as e:
        logger.error(f"Ошибка в handle_command: {e}")
        await message.reply_text("⚠️ Произошла ошибка. Попробуйте ещё раз.")
# === ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ===
def get_target_from_args(args: list, message: Message) -> Tuple[Optional[int], Optional[str]]:
    """Извлекает target_id и username из:
    - ответа на сообщение
    - @username в args[0]
    - числового ID в args[0]
    """
    target_id = None
    username = None

    # 1. Ответ на сообщение
    if message.reply_to_message:
        replied = message.reply_to_message.from_user
        target_id = replied.id
        username = replied.username
        return target_id, username

    # 2. @username или ID в args[0]
    if args:
        arg = args[0].strip()
        if arg.startswith("@"):
            username = arg[1:]
            # В реальной системе: запрос к Telegram API для получения ID
            # Здесь — заглушка
        elif arg.isdigit():
            target_id = int(arg)
        else:
            return None, None  # Неизвестный формат

    return target_id, username

async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    target_id = None
    username = None
    first_name = None

    # 1. Определяем target_id: reply, аргумент или текущий пользователь
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
        username = update.message.reply_to_message.from_user.username
        first_name = update.message.reply_to_message.from_user.first_name
    elif context.args:
        arg = context.args[0]
        if arg.isdigit():
            target_id = int(arg)
        else:
            # Пытаемся найти по username (без @)
            username_input = arg.lstrip('@').lower()
            with sqlite3.connect(DB_PATH) as conn:
                row = conn.execute(
                    "SELECT user_id, username, first_name FROM users WHERE LOWER(username) = ?",
                    (username_input,)
                ).fetchone()
                if row:
                    target_id, username, first_name = row
                else:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=f"❌ Не найден пользователь: @{username_input}",
                        parse_mode=ParseMode.MARKDOWN_V2
                    )
                    return
    else:
        # Если нет аргументов — берём текущего пользователя
        target_id = update.effective_user.id
        username = update.effective_user.username
        first_name = update.effective_user.first_name

    # 2. Получаем данные пользователя из Telegram (если возможно)
    try:
        user = await context.bot.get_chat_member(chat_id, target_id)
        member_status = "В чате"
    except:
        member_status = "Не в чате / Неизвестен"

    # 3. Формируем отображаемое имя
    if first_name:
        display_name = html.escape(first_name)
    elif username:
        display_name = html.escape(f"@{username}")
    else:
        display_name = f"[{target_id}]"

    # 4. Собираем ответ в MarkdownV2
    response = (
        f"🔢 *ID пользователя:*\n\n"
        f"• *Отображаемое имя:* {display_name}\n"
        f"• *User ID:* `{target_id}`\n"
        f"• *Статус в чате:* {member_status}"
    )

    # 5. Отправляем сообщение
    try:
        await context.bot.send_message(
            chat_id=chat_id,
            text=response,
            parse_mode=ParseMode.MARKDOWN_V2
        )
    except Exception as e:
        # Если MarkdownV2 сломался — отправляем простой текст
        await context.bot.send_message(
            chat_id=chat_id,
            text=response.replace("*", "").replace("`", ""),
            parse_mode=None
        )

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    if chat.type not in ["group", "supergroup"]:
        await update.message.reply_text("Этот бот работает только в групповых чатах.")
        return

    chat_id = chat.id

    # Запоминаем время добавления бота (текущее время)
    bot_added_times[chat_id] = time.time()
    await update.message.reply_text(
        "✅ Бот добавлен в чат. \n"
        "Первый администратор, написавший сообщение в течение 60 секунд, \n"
        "получит уровень 5 автоматически."
    )

def get_admin_level(chat_id: int, user_id: int) -> int:
    try:
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        cursor.execute(
            "SELECT level FROM admins WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id)
        )
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 0
    except sqlite3.Error as e:
        logger.error(f"[DB] Ошибка получения уровня для chat_id={chat_id}, user_id={user_id}: {e}")
        return 0


async def grant_admin_on_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    message = update.message

    if chat.type not in ["group", "supergroup"]:
        await message.reply_text("Этот бот работает только в групповых чатах.")
        return

    chat_id = chat.id
    logger.info(f"[{chat_id}] Обработка /getadmin — поиск создателя чата")

    try:
        # Получаем всех администраторов
        admins = await context.bot.get_chat_administrators(chat_id)
        logger.debug(f"[{chat_id}] Администраторы чата: {admins}")

        # Список возможных названий роли «создатель/владелец» (с учётом локализации)
        owner_titles = [
            "creator",  # официальный статус в API
            "Owner",    # английская локализация
            "Владелец", # русская локализация
            "Admin",    # альтернативный вариант
            "Создатель" # русская альтернатива
            "владелец"
        ]

        creator = None
        for admin in admins:
            # Проверяем статус и название роли
            if (admin.status == "creator" or
                any(title.lower() in str(admin.custom_title).lower()
                    for title in owner_titles)):
                creator = admin.user
                break

        if not creator:
            admin_usernames = []
            for admin in admins:
                name = admin.user.username or admin.user.first_name or str(admin.user.id)
                admin_usernames.append(f"@{name} ({admin.status}, {admin.custom_title})")

            logger.warning(f"[{chat_id}] Создатель не найден среди администраторов: {admin_usernames}")
            await message.reply_text(
                "❌ Не удалось определить создателя чата.\n"
                "Возможные причины:\n"
                "1. Создатель вышел из чата.\n"
                "2. У бота нет прав на просмотр администраторов.\n"
                "3. Роль создателя не соответствует ожидаемым названиям."
                "Связаться с разработчиком можно через @q_shimokuroda"
            )
            return

        creator_id = creator.id
        creator_username = creator.username or creator.first_name or str(creator_id)
        logger.info(f"[{chat_id}] Создатель найден: {creator_id} (@{creator_username})")

        # Проверка уровня в БД
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        cursor.execute(
            "SELECT level FROM admins WHERE chat_id = ? AND user_id = ?",
            (chat_id, creator_id)
        )
        row = cursor.fetchone()
        current_level = row[0] if row else 0
        conn.close()

        if current_level >= 5:
            await message.reply_text(f"✅ @{creator_username}, у вас уже есть уровень 5.")
            return

        # Запись в БД
        conn = sqlite3.connect('bot.db', timeout=10)
        cursor = conn.cursor()

        sql = """
        INSERT OR REPLACE INTO admins
            (chat_id, user_id, level, is_frozen, created_at, updated_at)
        VALUES
            (?, ?, 5, 0,
             COALESCE(
                (SELECT created_at FROM admins WHERE chat_id = ? AND user_id = ?),
                CURRENT_TIMESTAMP
             ),
             CURRENT_TIMESTAMP)
        """
        cursor.execute(sql, (chat_id, creator_id, chat_id, creator_id))

        if cursor.rowcount > 0:
            conn.commit()
            logger.info(f"[{chat_id}] Уровень 5 записан для {creator_id}")
            await message.reply_text(f"✅ @{creator_username}, вам присвоен уровень 5 как создателю чата!")
        else:
            logger.error(f"[{chat_id}] Не удалось вставить запись в БД")
            await message.reply_text("❌ Ошибка при записи в базу данных.")


    except Exception as e:
        logger.error(f"[{chat_id}] Ошибка при поиске создателя: {e}")
        await message.reply_text("❌ Произошла ошибка. Проверьте права бота и повторите попытку.")

def get_admin_level(chat_id: int, user_id: int) -> int:
    try:
        conn = sqlite3.connect('bot.db')
        cursor = conn.cursor()
        cursor.execute(
            "SELECT level FROM admins WHERE chat_id = ? AND user_id = ?",
            (chat_id, user_id)
        )
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else 0
    except sqlite3.Error as e:
        logger.error(f"[DB] Ошибка чтения уровня для {chat_id}/{user_id}: {e}")
        return 0

def set_admin_level(chat_id: int, user_id: int, level: int) -> bool:
    logger.debug(f"[DB] Попытка записи: chat_id={chat_id}, user_id={user_id}, level={level}")


    try:
        conn = sqlite3.connect('bot.db', timeout=10)
        cursor = conn.cursor()

        sql = """
        INSERT OR REPLACE INTO admins
            (chat_id, user_id, level, is_frozen, created_at, updated_at)
        VALUES
            (?, ?, ?, 0,
             COALESCE((SELECT created_at FROM admins WHERE chat_id=? AND user_id=?), CURRENT_TIMESTAMP),
             CURRENT_TIMESTAMP)
        """
        cursor.execute(sql, (chat_id, user_id, level, chat_id, user_id))

        if cursor.rowcount > 0:
            conn.commit()
            logger.info(f"[DB] Успешно записано: chat_id={chat_id}, user_id={user_id}")
            return True
        else:
            logger.warning(f"[DB] rowcount=0 — запись не добавлена")
            return False

    except sqlite3.IntegrityError as e:
        logger.error(f"[DB] Ошибка целостности (PRIMARY KEY и т.п.): {e}")
        return False
    except Exception as e:
        logger.error(f"[DB] Неожиданная ошибка: {e}")
        return False
    finally:
        if conn:
            conn.close()

def parse_duration(duration: str) -> Optional[int]:
    """
    Парсит длительность мута в формате 1m–24h.
    Возвращает секунды или None, если формат неверный.
    """
    duration = duration.strip().lower()

    if duration.endswith("m"):
        try:
            minutes = int(duration[:-1])
            if 1 <= minutes <= 1440:  # 1440m = 24h
                return minutes * 60
        except ValueError:
            pass

    elif duration.endswith("h"):
        try:
            hours = int(duration[:-1])
            if 1 <= hours <= 24:
                return hours * 3600
        except ValueError:
            pass

    return None  # Неверный формат

def add_chat_to_db(chat_id: int, invite_link: str = None):
    """Добавляет чат в БД или обновляет ссылку."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO chats (chat_id, invite_link, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            """,
            (chat_id, invite_link)
        )
        conn.commit()

def get_all_chats() -> list:
    """Возвращает список всех чатов из БД."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.execute("SELECT chat_id, invite_link FROM chats")
        return cursor.fetchall()

def update_invite_link(chat_id: int, invite_link: str):
    """Обновляет пригласительную ссылку для чата."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "UPDATE chats SET invite_link = ?, updated_at = CURRENT_TIMESTAMP WHERE chat_id = ?",
            (invite_link, chat_id)
        )
        conn.commit()

def log_moderation_action(action: str, target_id: int, moderator_id: int, reason: Optional[str], chat_id: int):
    """Логирует действие модерации."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute(
            "INSERT INTO moderation_logs (chat_id, action, target_user_id, moderator_id, reason) VALUES (?, ?, ?, ?, ?)",
            (chat_id, action, target_id, moderator_id, reason)
        )
        conn.commit()

def add_chat_if_new(chat_id: int):
    """Добавляет чат в БД, только если его там ещё нет."""
    with sqlite3.connect(DB_PATH) as conn:
        # Проверяем, есть ли чат в БД
        cursor = conn.execute("SELECT 1 FROM chats WHERE chat_id = ?", (chat_id,))
        if cursor.fetchone():
            return  # Чат уже есть, ничего не делаем

        # Добавляем новый чат (без ссылки — получим позже)
        conn.execute(
            "INSERT INTO chats (chat_id, invite_link, updated_at) VALUES (?, NULL, CURRENT_TIMESTAMP)",
            (chat_id,)
        )
        conn.commit()

async def on_bot_added(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Получаем информацию о событии изменения статуса участника
    chat_member = update.my_chat_member
    if not chat_member:
        return

    chat = chat_member.chat
    chat_id = chat.id

    # Проверяем, что бот был добавлен (статус стал 'member')
    was_member = chat_member.old_chat_member and chat_member.old_chat_member.status == "member"
    is_member = chat_member.new_chat_member.status == "member"

    if is_member and not was_member:  # Бот только что добавлен
        try:
            # Отправляем приветственное сообщение
            welcome_text = (
                "🤖 Привет! Я бот для управления чатом.\n\n"
                "НЕ забудь выдать мне админку"
                "Доступные команды:\n"
                "• /start - прописать после выдачи админки боту\n"
                "• /help — справка\n\n"
                "Для настройки пригласительных ссылок обратитесь к администратору."
            )
            await context.bot.send_message(chat_id=chat_id, text=welcome_text)

            # Добавляем чат в БД (если его ещё нет)
            add_chat_if_new(chat_id)


            logger.info(f"Бот добавлен в чат {chat_id}. Отправлено приветствие.")
        except Exception as e:
            logger.error(f"Не удалось отправить приветствие в чат {chat_id}: {e}")

def main():
    init_db()

    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("help", handle_command))
    application.add_handler(CommandHandler("dick", handle_command))
    application.add_handler(CommandHandler("top", handle_command))
    application.add_handler(CommandHandler("profile", profile_command))
    application.add_handler(CommandHandler("staff", handle_command))
    application.add_handler(CommandHandler("mute", handle_command))
    application.add_handler(CommandHandler("unmute", handle_command))
    application.add_handler(CommandHandler("ban", handle_command))
    application.add_handler(CommandHandler("unban", handle_command))
    application.add_handler(CommandHandler("permban", handle_command))
    application.add_handler(CommandHandler("unpermban", handle_command))
    application.add_handler(CommandHandler("freeze", handle_command))
    application.add_handler(CommandHandler("unfreeze", handle_command))
    application.add_handler(CommandHandler("id", id_command))
    application.add_handler(CommandHandler("maintenanceon", handle_command))
    application.add_handler(CommandHandler("maintenanceoff", handle_command))
    application.add_handler(CommandHandler("bot", handle_command))
    application.add_handler(CommandHandler("getowner", handle_command))
    application.add_handler(CommandHandler("setadmin", handle_command))
    application.add_handler(CommandHandler("kick", handle_command))
    application.add_handler(CommandHandler("bot", handle_command))
    application.add_handler(CommandHandler("rules", handle_command))
    application.add_handler(CommandHandler("antiflood_on", antiflood_on))
    application.add_handler(CommandHandler("antiflood_off", antiflood_off))
    application.add_handler(CommandHandler("getadmin", grant_admin_on_message))
    application.add_handler(CommandHandler("start", handle_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_and_mute_for_flood))
    application.add_handler(CommandHandler("start", private_chat_handler))

    # Обработчик события добавления бота в чат
    application.add_handler(ChatMemberHandler(on_bot_added, ChatMemberHandler.MY_CHAT_MEMBER))

    application.add_handler(CommandHandler("pudlis", private_chat_handler))



    application.run_polling()

if __name__ == "__main__":
    main()
