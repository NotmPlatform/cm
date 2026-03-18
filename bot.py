import logging
import os
import sqlite3
from datetime import datetime
from typing import Optional

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatMemberStatus
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# =========================
# НАСТРОЙКИ
# =========================

BOT_TOKEN = os.getenv("BOT_TOKEN", "PASTE_BOT_TOKEN_HERE")

# Webhook (если пусто — бот запустится на polling)
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "webhook")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
PORT = int(os.getenv("PORT", "8080"))

# ID админов для команды /stats
# Формат в .env: ADMIN_USER_IDS=12345,67890
ADMIN_USER_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_USER_IDS", "").split(",")
    if x.strip().isdigit()
}

# Проверка подписки на группу и канал перед выдачей бонусов
# Укажите chat_id канала/группы, например: -1001234567890
BONUS_GROUP_CHAT = os.getenv("BONUS_GROUP_CHAT", "")
BONUS_CHANNEL_CHAT = os.getenv("BONUS_CHANNEL_CHAT", "")

# Ссылки для вступления
COMMUNITY_URL = os.getenv("COMMUNITY_URL", "https://t.me/your_group")
CHANNEL_URL = os.getenv("CHANNEL_URL", "https://t.me/your_channel")

# Ссылка на бота с тестом для получения сертификата
CERT_TEST_BOT_URL = os.getenv("CERT_TEST_BOT_URL", "https://t.me/your_test_bot")

DB_PATH = os.getenv("DB_PATH", "web3_cm_paid_course.db")

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

COURSE_TITLE = "Платный курс: Web3 Community Manager"

WELCOME_TEXT = (
    f"Добро пожаловать в <b>{COURSE_TITLE}</b>.\n\n"
    "Внутри тебя ждут 15 уроков:\n"
    "• текстовые материалы\n"
    "• видеоуроки\n"
    "• бонусные шаблоны и материалы\n\n"
    "Проходи уроки по порядку. После завершения откроются бонусы."
)

HELP_TEXT = (
    "Команды:\n"
    "/start — открыть курс\n"
    "/help — помощь\n"
    "/stats — статистика (только для администратора)"
)

# =========================
# УРОКИ КУРСА
# Заполни text_url и video_url своими ссылками
# =========================

LESSONS = [
    {"number": 1, "title": "Урок 1", "text_url": "https://telegra.ph/Urok-1--Pochemu-v-Web3-komyuniti-reshaet-vsyo--i-pochemu-CM-ehto-ne-moderator-a-tochka-vliyaniya-03-18", "video_url": "https://rutube.ru/video/a09d052994202df2f70ac0a0b34dc4c5/?r=wd"},
    {"number": 2, "title": "Урок 2", "text_url": "https://telegra.ph/Urok-2--Pochemu-bolshinstvo-obychnyh-komyuniti-menedzherov-provalivayutsya-v-Web3-03-18", "video_url": "https://rutube.ru/video/a09d052994202df2f70ac0a0b34dc4c5/?r=wd"},
    {"number": 3, "title": "Урок 3", "text_url": "https://telegra.ph/Urok-3--5-tipov-lyudej-v-chate-kogo-nuzhno-rastit-kogo-nelzya-zlit-a-kogo-luchshe-srazu-obezvredit-03-18", "video_url": "https://rutube.ru/video/a09d052994202df2f70ac0a0b34dc4c5/?r=wd"},
    {"number": 4, "title": "Урок 4", "text_url": "https://telegra.ph/Urok-4--Telegram-Discord-i-X-tri-polya-boya-gde-formiruetsya-doverie-k-brendu-03-18", "video_url": "https://rutube.ru/video/a09d052994202df2f70ac0a0b34dc4c5/?r=wd"},
    {"number": 5, "title": "Урок 5", "text_url": "https://telegra.ph/Urok-5--Kak-govorit-ot-lica-brenda-tak-chtoby-tebe-verili-a-ne-prosto-chitali-03-18", "video_url": "https://rutube.ru/video/a09d052994202df2f70ac0a0b34dc4c5/?r=wd"},
    {"number": 6, "title": "Урок 6", "text_url": "https://telegra.ph/Urok-6--Kak-ne-dat-odnomu-angry-user-zarazit-ves-chat-03-18", "video_url": "https://rutube.ru/video/a09d052994202df2f70ac0a0b34dc4c5/?r=wd"},
    {"number": 7, "title": "Урок 7", "text_url": "https://telegra.ph/Urok-7--CHto-dolzhen-ponimat-CM-o-produkte-chtoby-ego-ne-schitali-bespoleznym-03-18", "video_url": "https://rutube.ru/video/a09d052994202df2f70ac0a0b34dc4c5/?r=wd"},
    {"number": 8, "title": "Урок 8", "text_url": "https://telegra.ph/Urok-8--Gde-CM-dolzhen-otvechat-sam-a-gde-odno-lishnee-slovo-mozhet-navredit-03-18", "video_url": "https://rutube.ru/video/a09d052994202df2f70ac0a0b34dc4c5/?r=wd"},
    {"number": 9, "title": "Урок 9", "text_url": "https://telegra.ph/Urok-9--Kak-prevrashchat-shum-komyuniti-v-razveddannye-dlya-vsej-kompanii-03-18", "video_url": "https://rutube.ru/video/a09d052994202df2f70ac0a0b34dc4c5/?r=wd"},
    {"number": 10, "title": "Урок 10", "text_url": "https://telegra.ph/Urok-10--Pochemu-odni-chaty-zhivye-a-drugie-umirayut--i-kak-ehto-menyat-03-18", "video_url": "https://rutube.ru/video/a09d052994202df2f70ac0a0b34dc4c5/?r=wd"},
    {"number": 11, "title": "Урок 11", "text_url": "https://telegra.ph/Urok-11--AMA-kvizy-i-aktivacii-kak-zastavit-komyuniti-ne-prosto-chitat-a-uchastvovat-03-18", "video_url": "https://rutube.ru/video/a09d052994202df2f70ac0a0b34dc4c5/?r=wd"},
    {"number": 12, "title": "Урок 12", "text_url": "https://telegra.ph/Urok-12--Kak-vyrastit-vnutri-komyuniti-lyudej-kotorye-nachnut-usilivat-brend-za-vas-03-18", "video_url": "https://rutube.ru/video/a09d052994202df2f70ac0a0b34dc4c5/?r=wd"},
    {"number": 13, "title": "Урок 13", "text_url": "https://telegra.ph/Urok-13--Odin-den-iz-zhizni-Web3-CM-kak-ne-utonut-v-haose-i-ne-poteryat-kontrol-03-18", "video_url": "https://rutube.ru/video/a09d052994202df2f70ac0a0b34dc4c5/?r=wd"},
    {"number": 14, "title": "Урок 14", "text_url": "https://telegra.ph/Urok-14--Kak-otvechaet-slabyj-CM-i-kak-otvechaet-silnyj--10-realnyh-razborov-03-18", "video_url": "https://rutube.ru/video/a09d052994202df2f70ac0a0b34dc4c5/?r=wd"},
    {"number": 15, "title": "Урок 15", "text_url": "https://telegra.ph/Urok-15--Kak-poluchit-rabotu-v-Web3-esli-u-tebya-poka-net-gromkogo-opyta-03-18", "video_url": "https://rutube.ru/video/a09d052994202df2f70ac0a0b34dc4c5/?r=wd"},
]

# =========================
# БОНУСЫ
# =========================

BONUS_ITEMS = [
    {"key": "negativity", "title": "Шаблоны ответов на негатив", "url": "https://example.com/bonus-negativity"},
    {"key": "faq", "title": "Шаблон FAQ", "url": "https://example.com/bonus-faq"},
    {"key": "weekly_report", "title": "Шаблон weekly report", "url": "https://example.com/bonus-weekly-report"},
    {"key": "community_report", "title": "Шаблон community report", "url": "https://example.com/bonus-community-report"},
    {"key": "chat_rules", "title": "Шаблон правил чата", "url": "https://example.com/bonus-chat-rules"},
    {"key": "ama", "title": "Шаблон AMA", "url": "https://example.com/bonus-ama"},
    {"key": "cv", "title": "CV template", "url": "https://example.com/bonus-cv"},
    {"key": "cert_test", "title": "Тест для получения сертификата", "url": CERT_TEST_BOT_URL},
]

# =========================
# БАЗА
# =========================

def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                created_at TEXT NOT NULL,
                last_seen_at TEXT NOT NULL,
                current_lesson INTEGER NOT NULL DEFAULT 1,
                completed_lessons INTEGER NOT NULL DEFAULT 0,
                bonuses_unlocked INTEGER NOT NULL DEFAULT 0
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS lesson_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                lesson_number INTEGER NOT NULL,
                event_type TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
            """
        )
        conn.commit()


def upsert_user(user_id: int, username: Optional[str], first_name: Optional[str]) -> None:
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        cur = conn.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        row = cur.fetchone()
        if row:
            conn.execute(
                """
                UPDATE users
                SET username = ?, first_name = ?, last_seen_at = ?
                WHERE user_id = ?
                """,
                (username, first_name, now, user_id),
            )
        else:
            conn.execute(
                """
                INSERT INTO users (user_id, username, first_name, created_at, last_seen_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, username, first_name, now, now),
            )
        conn.commit()


def get_user_state(user_id: int) -> sqlite3.Row:
    with get_conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
    return row


def set_current_lesson(user_id: int, lesson_number: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET current_lesson = ?, last_seen_at = ? WHERE user_id = ?",
            (lesson_number, datetime.utcnow().isoformat(), user_id),
        )
        conn.commit()


def complete_lesson(user_id: int, lesson_number: int) -> None:
    now = datetime.utcnow().isoformat()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT completed_lessons FROM users WHERE user_id = ?",
            (user_id,),
        ).fetchone()
        completed_lessons = row["completed_lessons"] if row else 0
        if lesson_number > completed_lessons:
            conn.execute(
                """
                UPDATE users
                SET completed_lessons = ?, current_lesson = ?, last_seen_at = ?
                WHERE user_id = ?
                """,
                (lesson_number, min(lesson_number + 1, len(LESSONS)), now, user_id),
            )
        else:
            conn.execute(
                "UPDATE users SET last_seen_at = ? WHERE user_id = ?",
                (now, user_id),
            )
        conn.execute(
            """
            INSERT INTO lesson_events (user_id, lesson_number, event_type, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (user_id, lesson_number, "complete", now),
        )
        conn.commit()


def unlock_bonuses(user_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET bonuses_unlocked = 1, last_seen_at = ? WHERE user_id = ?",
            (datetime.utcnow().isoformat(), user_id),
        )
        conn.commit()


def get_stats() -> dict:
    with get_conn() as conn:
        users_total = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        finished_total = conn.execute(
            "SELECT COUNT(*) AS c FROM users WHERE completed_lessons >= ?",
            (len(LESSONS),),
        ).fetchone()["c"]
        bonuses_total = conn.execute(
            "SELECT COUNT(*) AS c FROM users WHERE bonuses_unlocked = 1"
        ).fetchone()["c"]
    return {
        "users_total": users_total,
        "finished_total": finished_total,
        "bonuses_total": bonuses_total,
    }


# =========================
# ВСПОМОГАТЕЛЬНОЕ
# =========================

def lesson_by_number(lesson_number: int) -> Optional[dict]:
    for lesson in LESSONS:
        if lesson["number"] == lesson_number:
            return lesson
    return None


def main_menu_keyboard(current_lesson: int, completed_lessons: int) -> InlineKeyboardMarkup:
    rows = []

    if current_lesson <= len(LESSONS):
        rows.append(
            [InlineKeyboardButton(f"▶️ Продолжить с урока {current_lesson}", callback_data=f"lesson:{current_lesson}")]
        )

    rows.append([InlineKeyboardButton("📚 Все уроки", callback_data="all_lessons")])

    if completed_lessons >= len(LESSONS):
        rows.append([InlineKeyboardButton("🎁 Получить бонусы", callback_data="check_bonus_access")])

    return InlineKeyboardMarkup(rows)


def lessons_keyboard(unlocked_to: int) -> InlineKeyboardMarkup:
    rows = []
    for lesson in LESSONS:
        num = lesson["number"]
        title = lesson["title"]
        if num <= max(unlocked_to, 1):
            rows.append([InlineKeyboardButton(f"{num}. {title}", callback_data=f"lesson:{num}")])
        else:
            rows.append([InlineKeyboardButton(f"🔒 {num}. {title}", callback_data="locked")])
    rows.append([InlineKeyboardButton("⬅️ В меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


def lesson_keyboard(lesson_number: int, has_text: bool, has_video: bool, is_last: bool) -> InlineKeyboardMarkup:
    rows = []
    lesson = lesson_by_number(lesson_number)

    if has_text:
        rows.append([InlineKeyboardButton("📖 Открыть текст", url=lesson["text_url"])])
    if has_video:
        rows.append([InlineKeyboardButton("🎬 Открыть видео", url=lesson["video_url"])])

    rows.append([InlineKeyboardButton("✅ Отметить урок пройденным", callback_data=f"complete:{lesson_number}")])

    nav_row = []
    if lesson_number > 1:
        nav_row.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"lesson:{lesson_number - 1}"))
    if not is_last:
        nav_row.append(InlineKeyboardButton("➡️ Далее", callback_data=f"lesson:{lesson_number + 1}"))
    if nav_row:
        rows.append(nav_row)

    rows.append([InlineKeyboardButton("📚 Ко всем урокам", callback_data="all_lessons")])
    rows.append([InlineKeyboardButton("⬅️ В меню", callback_data="main_menu")])

    return InlineKeyboardMarkup(rows)


def bonus_access_keyboard() -> InlineKeyboardMarkup:
    rows = []
    join_row = []
    if COMMUNITY_URL:
        join_row.append(InlineKeyboardButton("👥 Вступить в группу", url=COMMUNITY_URL))
    if CHANNEL_URL:
        join_row.append(InlineKeyboardButton("📢 Подписаться на канал", url=CHANNEL_URL))
    if join_row:
        rows.append(join_row)

    rows.append([InlineKeyboardButton("🔄 Проверить доступ", callback_data="check_bonus_access")])
    rows.append([InlineKeyboardButton("⬅️ В меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


def bonus_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for item in BONUS_ITEMS:
        rows.append([InlineKeyboardButton(f"🎁 {item['title']}", url=item["url"])])
    rows.append([InlineKeyboardButton("⬅️ В меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


async def is_member_of_chat(bot, user_id: int, chat_id_raw: str) -> bool:
    if not chat_id_raw:
        return False
    try:
        member = await bot.get_chat_member(chat_id=int(chat_id_raw), user_id=user_id)
        return member.status in {
            ChatMemberStatus.MEMBER,
            ChatMemberStatus.ADMINISTRATOR,
            ChatMemberStatus.OWNER,
        }
    except Exception as exc:
        logger.warning("Membership check failed | chat=%s | user=%s | error=%s", chat_id_raw, user_id, exc)
        return False


async def has_bonus_access(bot, user_id: int) -> bool:
    checks = []
    if BONUS_GROUP_CHAT:
        checks.append(await is_member_of_chat(bot, user_id, BONUS_GROUP_CHAT))
    if BONUS_CHANNEL_CHAT:
        checks.append(await is_member_of_chat(bot, user_id, BONUS_CHANNEL_CHAT))

    if not checks:
        return True
    return all(checks)


# =========================
# ХЕНДЛЕРЫ
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    upsert_user(user.id, user.username, user.first_name)
    state = get_user_state(user.id)

    text = (
        f"{WELCOME_TEXT}\n\n"
        f"Твой прогресс: <b>{state['completed_lessons']}</b> из <b>{len(LESSONS)}</b> уроков."
    )

    if update.message:
        await update.message.reply_html(
            text,
            reply_markup=main_menu_keyboard(
                current_lesson=state["current_lesson"],
                completed_lessons=state["completed_lessons"],
            ),
            disable_web_page_preview=True,
        )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(HELP_TEXT)


async def stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if user.id not in ADMIN_USER_IDS:
        if update.message:
            await update.message.reply_text("У тебя нет доступа к этой команде.")
        return

    stats = get_stats()
    text = (
        "📊 Статистика бота\n\n"
        f"Пользователей: {stats['users_total']}\n"
        f"Завершили все 15 уроков: {stats['finished_total']}\n"
        f"Открыли бонусы: {stats['bonuses_total']}"
    )
    if update.message:
        await update.message.reply_text(text)


async def show_main_menu(query, user_id: int) -> None:
    state = get_user_state(user_id)
    text = (
        f"{WELCOME_TEXT}\n\n"
        f"Твой прогресс: <b>{state['completed_lessons']}</b> из <b>{len(LESSONS)}</b> уроков."
    )
    await query.edit_message_text(
        text=text,
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(
            current_lesson=state["current_lesson"],
            completed_lessons=state["completed_lessons"],
        ),
        disable_web_page_preview=True,
    )


async def show_all_lessons(query, user_id: int) -> None:
    state = get_user_state(user_id)
    unlocked_to = min(max(state["completed_lessons"] + 1, 1), len(LESSONS))
    text = (
        "📚 <b>Все уроки курса</b>\n\n"
        "Открывай уроки по порядку. После завершения всех 15 уроков откроются бонусы."
    )
    await query.edit_message_text(
        text=text,
        parse_mode="HTML",
        reply_markup=lessons_keyboard(unlocked_to),
        disable_web_page_preview=True,
    )


async def show_lesson(query, user_id: int, lesson_number: int) -> None:
    lesson = lesson_by_number(lesson_number)
    if not lesson:
        await query.answer("Урок не найден.", show_alert=True)
        return

    state = get_user_state(user_id)
    unlocked_to = min(max(state["completed_lessons"] + 1, 1), len(LESSONS))
    if lesson_number > unlocked_to:
        await query.answer("Сначала пройди предыдущий урок.", show_alert=True)
        return

    set_current_lesson(user_id, lesson_number)

    has_text = bool(lesson["text_url"])
    has_video = bool(lesson["video_url"])
    text = (
        f"📘 <b>{lesson['title']}</b>\n"
        f"Урок {lesson_number} из {len(LESSONS)}\n\n"
        "Открой текст и видео, а затем отметь урок как пройденный."
    )
    await query.edit_message_text(
        text=text,
        parse_mode="HTML",
        reply_markup=lesson_keyboard(
            lesson_number=lesson_number,
            has_text=has_text,
            has_video=has_video,
            is_last=(lesson_number == len(LESSONS)),
        ),
        disable_web_page_preview=True,
    )


async def show_bonus_gate(query, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = get_user_state(user_id)
    if state["completed_lessons"] < len(LESSONS):
        await query.answer("Сначала пройди все 15 уроков.", show_alert=True)
        return

    allowed = await has_bonus_access(context.bot, user_id)
    if allowed:
        unlock_bonuses(user_id)
        text = (
            "🎁 <b>Бонусы открыты</b>\n\n"
            "Спасибо за прохождение курса. Ниже — все бонусные материалы и тест на сертификат."
        )
        await query.edit_message_text(
            text=text,
            parse_mode="HTML",
            reply_markup=bonus_keyboard(),
            disable_web_page_preview=True,
        )
    else:
        text = (
            "🔒 <b>Бонусы пока недоступны</b>\n\n"
            "Чтобы открыть бонусы, вступи в группу и подпишись на канал.\n"
            "После этого нажми «Проверить доступ»."
        )
        await query.edit_message_text(
            text=text,
            parse_mode="HTML",
            reply_markup=bonus_access_keyboard(),
            disable_web_page_preview=True,
        )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    upsert_user(user.id, user.username, user.first_name)

    await query.answer()
    data = query.data

    if data == "main_menu":
        await show_main_menu(query, user.id)
        return

    if data == "all_lessons":
        await show_all_lessons(query, user.id)
        return

    if data == "locked":
        await query.answer("Сначала пройди предыдущие уроки.", show_alert=True)
        return

    if data == "check_bonus_access":
        await show_bonus_gate(query, user.id, context)
        return

    if data.startswith("lesson:"):
        lesson_number = int(data.split(":")[1])
        await show_lesson(query, user.id, lesson_number)
        return

    if data.startswith("complete:"):
        lesson_number = int(data.split(":")[1])
        complete_lesson(user.id, lesson_number)

        if lesson_number >= len(LESSONS):
            text = (
                "🏁 <b>Ты завершил все 15 уроков курса.</b>\n\n"
                "Теперь можно открыть бонусы. Перед этим бот проверит вступление в группу и канал."
            )
            keyboard = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("🎁 Открыть бонусы", callback_data="check_bonus_access")],
                    [InlineKeyboardButton("⬅️ В меню", callback_data="main_menu")],
                ]
            )
            await query.edit_message_text(text=text, parse_mode="HTML", reply_markup=keyboard)
            return

        next_lesson = lesson_number + 1
        text = (
            f"✅ <b>Урок {lesson_number} отмечен как пройденный.</b>\n\n"
            f"Готов перейти к уроку {next_lesson}?"
        )
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton(f"➡️ Перейти к уроку {next_lesson}", callback_data=f"lesson:{next_lesson}")],
                [InlineKeyboardButton("📚 Ко всем урокам", callback_data="all_lessons")],
            ]
        )
        await query.edit_message_text(text=text, parse_mode="HTML", reply_markup=keyboard)
        return


async def menu_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    upsert_user(user.id, user.username, user.first_name)
    state = get_user_state(user.id)

    if update.message:
        await update.message.reply_html(
            (
                "Используй кнопки ниже для навигации по курсу.\n\n"
                f"Твой прогресс: <b>{state['completed_lessons']}</b> из <b>{len(LESSONS)}</b> уроков."
            ),
            reply_markup=main_menu_keyboard(
                current_lesson=state["current_lesson"],
                completed_lessons=state["completed_lessons"],
            ),
        )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled error: %s", context.error)


# =========================
# ИНИЦИАЛИЗАЦИЯ
# =========================

def build_application() -> Application:
    for lesson in LESSONS:
        logger.info(
            "Lesson %s URLs | text=%s | video=%s",
            lesson["number"],
            "set" if lesson["text_url"] else "empty",
            "set" if lesson["video_url"] else "empty",
        )

    logger.info("Community URL | %s", "set" if COMMUNITY_URL else "empty")
    logger.info("Channel URL | %s", "set" if CHANNEL_URL else "empty")
    logger.info("Bonus group chat for check | %s", BONUS_GROUP_CHAT if BONUS_GROUP_CHAT else "empty")
    logger.info("Bonus channel chat for check | %s", BONUS_CHANNEL_CHAT if BONUS_CHANNEL_CHAT else "empty")
    logger.info("Admin stats enabled | %s", "yes" if ADMIN_USER_IDS else "no")

    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("stats", stats_handler))
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(MessageHandler(filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND, menu_text_handler))
    application.add_error_handler(error_handler)
    return application


async def post_init(application: Application) -> None:
    logger.info("Bot initialized")


def main() -> None:
    init_db()
    app = build_application()
    app.post_init = post_init

    if WEBHOOK_URL:
        webhook_path = f"/{WEBHOOK_PATH}"
        logger.info("Starting bot with webhook on %s%s", WEBHOOK_URL, webhook_path)
        app.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=WEBHOOK_PATH,
            webhook_url=f"{WEBHOOK_URL}{webhook_path}",
            secret_token=WEBHOOK_SECRET or None,
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True,
        )
    else:
        logger.info("Starting bot with polling")
        app.run_polling(
            allowed_updates=["message", "callback_query"],
            drop_pending_updates=True,
        )


if __name__ == "__main__":
    main()
