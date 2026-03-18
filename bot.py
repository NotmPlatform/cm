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

# =========================================
# НАСТРОЙКИ
# =========================================

BOT_TOKEN = os.getenv("BOT_TOKEN", "PASTE_BOT_TOKEN_HERE")

# Webhook. Если не указан, бот запустится на polling.
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "webhook")
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")
PORT = int(os.getenv("PORT", "8080"))

# ID админов для /stats
# Пример: ADMIN_USER_IDS=12345,67890
ADMIN_USER_IDS = {
    int(x.strip())
    for x in os.getenv("ADMIN_USER_IDS", "").split(",")
    if x.strip().isdigit()
}

# Ключ доступа к боту — участие в закрытой платной группе.
# ВАЖНО: сюда нужен именно numeric chat_id группы, а не invite-link.
# Пример: PAID_GROUP_CHAT=-1001234567890
PAID_GROUP_CHAT = os.getenv("PAID_GROUP_CHAT", "")

# Ссылка на менеджера, если доступа нет
MANAGER_URL = os.getenv("MANAGER_URL", "https://t.me/+Sr03OD8ZRxwxMDEy")

# Ссылка на бота / тест для получения сертификата
CERT_TEST_BOT_URL = os.getenv("CERT_TEST_BOT_URL", "https://t.me/your_test_bot")

DB_PATH = os.getenv("DB_PATH", "web3_cm_paid_course.db")

logging.basicConfig(
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

COURSE_TITLE = "Курс: Web3 Community Manager"

WELCOME_TEXT = f"""Добро пожаловать в <b>{COURSE_TITLE}</b>.

Ты внутри практического курса, который поможет освоить профессию <b>Web3 Community Manager</b> и собрать сильную базу для входа в индустрию.

Что ты получишь внутри:

📘 <b>15 текстовых уроков</b> — структура, логика роли, реальные задачи и понимание профессии
🎬 <b>15 видеоуроков</b> — быстрый и удобный формат для прохождения материала
🧰 <b>Практические материалы</b> — шаблоны, инструменты и готовые заготовки для работы

После прохождения курса тебе также будут доступны:

🛡 <b>Proof of Competency</b> — подтверждение в базе курса для HR
✅ <b>Verified Certificate of Completion</b> — именной PDF-сертификат о прохождении курса

Проходи уроки шаг за шагом. В конце тебя ждут практические материалы и финальный тест для получения сертификата."""

HELP_TEXT = (
    "Команды:\n"
    "/start — открыть курс\n"
    "/help — помощь\n"
    "/stats — статистика (для администратора)"
)

# =========================================
# УРОКИ
# =========================================

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

# =========================================
# МАТЕРИАЛЫ КУРСА
# =========================================

BONUS_ITEMS = [
    {"key": "negativity", "title": "Шаблоны ответов на негатив", "url": "https://telegra.ph/BONUS-1-SHABLONY-OTVETOV-NA-NEGATIV-03-18"},
    {"key": "faq", "title": "Шаблон FAQ", "url": "https://telegra.ph/SHablon-FAQ-03-18"},
    {"key": "weekly_report", "title": "Шаблон weekly report", "url": "https://telegra.ph/WEEKLY-REPORT-TEMPLATE-03-18"},
    {"key": "community_report", "title": "Шаблон community report", "url": "https://telegra.ph/COMMUNITY-REPORT-TEMPLATE-03-18"},
    {"key": "chat_rules", "title": "Шаблон правил чата", "url": "https://telegra.ph/SHABLON-PRAVIL-CHATA-03-18"},
    {"key": "ama", "title": "Шаблон AMA", "url": "https://telegra.ph/SHABLON-AMA-03-18"},
    {"key": "cv", "title": "CV template", "url": "https://telegra.ph/SHABLON-CV-DLYA-WEB3-COMMUNITY-MANAGER-03-18"},
    {"key": "cert_test", "title": "Тест для получения сертификата", "url": CERT_TEST_BOT_URL},
]

# =========================================
# БАЗА ДАННЫХ
# =========================================

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
                materials_unlocked INTEGER NOT NULL DEFAULT 0
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
        row = conn.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,)).fetchone()
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
        return conn.execute("SELECT * FROM users WHERE user_id = ?", (user_id,)).fetchone()


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


def unlock_materials(user_id: int) -> None:
    with get_conn() as conn:
        conn.execute(
            "UPDATE users SET materials_unlocked = 1, last_seen_at = ? WHERE user_id = ?",
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
        materials_total = conn.execute(
            "SELECT COUNT(*) AS c FROM users WHERE materials_unlocked = 1"
        ).fetchone()["c"]

    return {
        "users_total": users_total,
        "finished_total": finished_total,
        "materials_total": materials_total,
    }


# =========================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =========================================

def lesson_by_number(lesson_number: int) -> Optional[dict]:
    for lesson in LESSONS:
        if lesson["number"] == lesson_number:
            return lesson
    return None


def access_gate_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("🔐 Проверить доступ", callback_data="check_paid_access")],
        ]
    )


def denied_access_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("👤 Обратиться к менеджеру", url=MANAGER_URL)],
            [InlineKeyboardButton("🔄 Проверить доступ ещё раз", callback_data="check_paid_access")],
        ]
    )


def main_menu_keyboard(current_lesson: int, completed_lessons: int) -> InlineKeyboardMarkup:
    rows = []

    if current_lesson <= len(LESSONS):
        rows.append(
            [InlineKeyboardButton(f"▶️ Продолжить с урока {current_lesson}", callback_data=f"lesson:{current_lesson}")]
        )

    rows.append([InlineKeyboardButton("📚 Все уроки", callback_data="all_lessons")])

    if completed_lessons >= len(LESSONS):
        rows.append([InlineKeyboardButton("📂 Открыть материалы курса", callback_data="check_materials_access")])

    return InlineKeyboardMarkup(rows)


def lessons_keyboard(unlocked_to: int) -> InlineKeyboardMarkup:
    rows = []
    for lesson in LESSONS:
        num = lesson["number"]
        title = lesson["title"]
        if num <= unlocked_to:
            rows.append([InlineKeyboardButton(f"{num}. {title}", callback_data=f"lesson:{num}")])
        else:
            rows.append([InlineKeyboardButton(f"🔒 {num}. {title}", callback_data="locked")])

    rows.append([InlineKeyboardButton("⬅️ В меню", callback_data="main_menu")])
    return InlineKeyboardMarkup(rows)


def lesson_keyboard(lesson_number: int, is_last: bool) -> InlineKeyboardMarkup:
    lesson = lesson_by_number(lesson_number)
    rows = []

    if lesson and lesson.get("text_url"):
        rows.append([InlineKeyboardButton("📖 Открыть текст", url=lesson["text_url"])])
    if lesson and lesson.get("video_url"):
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


def materials_keyboard() -> InlineKeyboardMarkup:
    rows = []
    for item in BONUS_ITEMS:
        icon = "🎓" if item["key"] == "cert_test" else "🧰"
        rows.append([InlineKeyboardButton(f"{icon} {item['title']}", url=item["url"])])
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
        logger.warning(
            "Membership check failed | chat=%s | user=%s | error=%s",
            chat_id_raw,
            user_id,
            exc,
        )
        return False


async def has_paid_access(bot, user_id: int) -> bool:
    return await is_member_of_chat(bot, user_id, PAID_GROUP_CHAT)


async def show_denied_access(query) -> None:
    text = (
        "🔒 <b>Доступ к курсу закрыт</b>\n\n"
        "Вы не оплатили урок.\n"
        "Обратитесь к менеджеру канала."
    )
    await query.edit_message_text(
        text=text,
        parse_mode="HTML",
        reply_markup=denied_access_keyboard(),
        disable_web_page_preview=True,
    )


async def ensure_paid_access(query, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if await has_paid_access(context.bot, user_id):
        return True
    await show_denied_access(query)
    return False


# =========================================
# ХЕНДЛЕРЫ
# =========================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    upsert_user(user.id, user.username, user.first_name)

    text = (
        f"<b>{COURSE_TITLE}</b>\n\n"
        "Перед открытием уроков бот должен проверить, есть ли у вас доступ к курсу.\n\n"
        "Нажмите кнопку ниже."
    )

    if update.message:
        await update.message.reply_html(
            text,
            reply_markup=access_gate_keyboard(),
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
        f"Завершили все уроки: {stats['finished_total']}\n"
        f"Открыли материалы курса: {stats['materials_total']}"
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
        "Открывай уроки по порядку. После завершения 15 уроков откроются материалы курса."
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

    text = (
        f"📘 <b>{lesson['title']}</b>\n"
        f"Урок {lesson_number} из {len(LESSONS)}\n\n"
        "Открой текст и видео, а затем отметь урок как пройденный."
    )
    await query.edit_message_text(
        text=text,
        parse_mode="HTML",
        reply_markup=lesson_keyboard(lesson_number, is_last=(lesson_number == len(LESSONS))),
        disable_web_page_preview=True,
    )


async def show_materials_gate(query, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    state = get_user_state(user_id)
    if state["completed_lessons"] < len(LESSONS):
        await query.answer("Сначала пройди все 15 уроков.", show_alert=True)
        return

    if not await has_paid_access(context.bot, user_id):
        await show_denied_access(query)
        return

    unlock_materials(user_id)
    text = (
        "📂 <b>Материалы курса открыты</b>\n\n"
        "Ты завершил обучение и открыл практический блок курса.\n\n"
        "Ниже тебя ждут:\n"
        "🧰 рабочие шаблоны и материалы\n"
        "📑 готовые заготовки для практики\n"
        "🎓 тест для получения сертификата\n\n"
        "После успешного прохождения теста тебе будут доступны:\n"
        "🛡 <b>Proof of Competency</b> — подтверждение в базе курса для HR\n"
        "✅ <b>Verified Certificate of Completion</b> — именной PDF-сертификат"
    )
    await query.edit_message_text(
        text=text,
        parse_mode="HTML",
        reply_markup=materials_keyboard(),
        disable_web_page_preview=True,
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user = update.effective_user
    upsert_user(user.id, user.username, user.first_name)

    await query.answer()
    data = query.data

    if data == "check_paid_access":
        if not await ensure_paid_access(query, user.id, context):
            return

        state = get_user_state(user.id)
        if state["completed_lessons"] == 0:
            await show_lesson(query, user.id, 1)
        else:
            await show_main_menu(query, user.id)
        return

    guarded = {"main_menu", "all_lessons", "check_materials_access"}
    if data in guarded or data.startswith(("lesson:", "complete:")):
        if not await ensure_paid_access(query, user.id, context):
            return

    if data == "main_menu":
        await show_main_menu(query, user.id)
        return

    if data == "all_lessons":
        await show_all_lessons(query, user.id)
        return

    if data == "locked":
        await query.answer("Сначала пройди предыдущие уроки.", show_alert=True)
        return

    if data == "check_materials_access":
        await show_materials_gate(query, user.id, context)
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
                "🏁 <b>Курс завершён</b>\n\n"
                "Ты прошёл все 15 уроков и собрал полную базу по роли <b>Web3 Community Manager</b>.\n\n"
                "Дальше для тебя открываются:\n"
                "📂 практические материалы для работы\n"
                "🧰 готовые шаблоны и рабочие заготовки\n"
                "🎓 тест для получения сертификата\n\n"
                "Нажми ниже, чтобы открыть материалы и перейти к завершающему этапу курса."
            )
            keyboard = InlineKeyboardMarkup(
                [
                    [InlineKeyboardButton("📂 Открыть материалы курса", callback_data="check_materials_access")],
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

    if update.message:
        if await has_paid_access(context.bot, user.id):
            state = get_user_state(user.id)
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
        else:
            await update.message.reply_html(
                "🔒 <b>Доступ к курсу закрыт</b>\n\nВы не оплатили урок.\nОбратитесь к менеджеру канала.",
                reply_markup=denied_access_keyboard(),
                disable_web_page_preview=True,
            )


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Unhandled error: %s", context.error)


# =========================================
# ИНИЦИАЛИЗАЦИЯ
# =========================================

def build_application() -> Application:
    for lesson in LESSONS:
        logger.info(
            "Lesson %s URLs | text=%s | video=%s",
            lesson["number"],
            "set" if lesson["text_url"] else "empty",
            "set" if lesson["video_url"] else "empty",
        )

    logger.info("Paid group chat for access | %s", PAID_GROUP_CHAT if PAID_GROUP_CHAT else "empty")
    logger.info("Manager url | %s", "set" if MANAGER_URL else "empty")
    logger.info("Admin stats enabled | %s", "yes" if ADMIN_USER_IDS else "no")

    application = ApplicationBuilder().token(BOT_TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("stats", stats_handler))
    application.add_handler(CallbackQueryHandler(callback_handler))
    application.add_handler(
        MessageHandler(
            filters.ChatType.PRIVATE & filters.TEXT & ~filters.COMMAND,
            menu_text_handler,
        )
    )
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
