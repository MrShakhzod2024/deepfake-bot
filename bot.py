import os
import logging
import httpx
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.environ.get("ANTHROPIC_API_KEY")

SYSTEM_PROMPT = """Ты образовательный бот DeepfakeGuard по теме Deepfake и кибербезопасности.
Отвечай только по теме: дипфейки, GAN-сети, BEC-атаки, социальная инженерия, защита компании, клонирование голоса, Phishing Simulations, Zero Trust.
Ключевые знания:
- GAN: Генератор создаёт синтетику, Дискриминатор выявляет фейки
- Клонирование голоса: достаточно менее 5 секунд записи
- BEC-атаки: OSINT, модель, контакт, звонок с дипфейком
- Признаки дипфейка: артефакты при повороте более 30 градусов, аномалии моргания, стерильный голос
- Защита: внеканальная верификация, Zero Trust, контрольные фразы, Phishing Simulations
Отвечай на русском или узбекском языке. Используй эмодзи. Ответы до 400 слов."""

user_histories = {}

QUICK_TOPICS = [
    ("🤖 Что такое Deepfake?", "Что такое Deepfake?"),
    ("⚙️ Как работают GAN?", "Как работают GAN-сети?"),
    ("💼 BEC-атаки", "Что такое BEC-атаки с дипфейками?"),
    ("🔍 Как распознать?", "Как распознать дипфейк?"),
    ("🛡 Защита компании", "Как защитить компанию от дипфейков?"),
    ("🎙 Клонирование голоса", "Что такое клонирование голоса?"),
    ("🎓 Phishing Simulations", "Что такое Phishing Simulations?"),
    ("⚠️ Zero Trust", "Что такое Zero Trust?"),
]

async def ask_openrouter(messages):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "mistralai/mistral-7b-instruct:free",
                "messages": messages,
            },
            timeout=30
        )
        data = response.json()
        logger.info(f"OpenRouter response: {data}")
        return data["choices"][0]["message"]["content"]

def get_main_keyboard():
    keyboard = []
    for i in range(0, len(QUICK_TOPICS), 2):
        row = [InlineKeyboardButton(QUICK_TOPICS[i][0], callback_data=f"topic_{i}")]
        if i + 1 < len(QUICK_TOPICS):
            row.append(InlineKeyboardButton(QUICK_TOPICS[i+1][0], callback_data=f"topic_{i+1}"))
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton("🗑 Очистить историю", callback_data="clear")])
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_histories[user_id] = []
    await update.message.reply_text(
        "👋 *Привет! Я DeepfakeGuard* — образовательный бот по кибербезопасности.\n\n"
        "Помогу разобраться в:\n"
        "• Технологиях Deepfake и GAN\n"
        "• BEC-атаках нового поколения\n"
        "• Методах распознавания синтетического контента\n"
        "• Защите сотрудников и компании\n\n"
        "Выберите тему или задайте вопрос 👇",
        parse_mode="Markdown",
        reply_markup=get_main_keyboard()
    )

async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_histories[user_id] = []
    await update.message.reply_text("🗑 История очищена!", reply_markup=get_main_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if query.data == "clear":
        user_histories[user_id] = []
        await query.message.reply_text("🗑 История очищена!", reply_markup=get_main_keyboard())
        return
    if query.data.startswith("topic_"):
        idx = int(query.data.split("_")[1])
        question = QUICK_TOPICS[idx][1]
        await process_question(query.message, user_id, question)

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    await process_question(update.message, user_id, update.message.text.strip())

async def process_question(message, user_id, question):
    if user_id not in user_histories:
        user_histories[user_id] = []
    try:
        await message.chat.send_action("typing")
        user_histories[user_id].append({"role": "user", "content": question})
        messages = [{"role": "system", "content": SYSTEM_PROMPT}] + user_histories[user_id][-10:]
        answer = await ask_openrouter(messages)
        user_histories[user_id].append({"role": "assistant", "content": answer})
        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton("📋 Все темы", callback_data="topic_0"),
            InlineKeyboardButton("🗑 Очистить", callback_data="clear")
        ]])
        await message.reply_text(answer, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error: {e}")
        await message.reply_text("⚠️ Ошибка. Попробуйте ещё раз.", reply_markup=get_main_keyboard())

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    logger.info("DeepfakeGuard bot started!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()




