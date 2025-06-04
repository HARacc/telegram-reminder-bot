import json
import os
import asyncio
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv
import nest_asyncio

# --- Налаштування логів ---
logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# --- Завантаження токена ---
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
REMINDER_FILE = "reminders.json"

# --- Збереження та завантаження ---
def load_reminders():
    if os.path.exists(REMINDER_FILE):
        with open(REMINDER_FILE, "r") as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                logging.warning("⚠️ Файл reminders.json порожній або пошкоджений.")
                return []
    return []

def save_reminders(reminders):
    with open(REMINDER_FILE, "w") as f:
        json.dump(reminders, f, indent=2)

# --- Команда /remind ---
async def remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        time_str = context.args[0]
        message = " ".join(context.args[1:])
        reminders = load_reminders()
        reminders.append({
            "chat_id": update.effective_chat.id,
            "time": time_str,
            "text": message,
            "sent": False
        })
        save_reminders(reminders)
        await update.message.reply_text(f"✅ Нагадування встановлено на {time_str}: {message}")
    except Exception as e:
        logging.error(f"❌ Помилка у /remind: {e}")
        await update.message.reply_text("❌ Формат: /remind HH:MM текст")

# --- Цикл перевірки нагадувань ---
async def reminder_loop(app):
    logging.info("📡 Фоновий процес нагадувань запущено")
    while True:
        now = datetime.now().strftime("%H:%M")
        logging.info(f"🕒 Поточний час: {now}")
        reminders = load_reminders()
        updated = False

        for reminder in reminders:
            if reminder["time"] == now and not reminder["sent"]:
                try:
                    await app.bot.send_message(
                        chat_id=reminder["chat_id"],
                        text=f"⏰ Нагадування: {reminder['text']}"
                    )
                    reminder["sent"] = True
                    updated = True
                    logging.info(f"✅ Надіслано нагадування: {reminder['text']} → {reminder['chat_id']}")
                except Exception as e:
                    logging.error(f"❌ Помилка надсилання повідомлення: {e}")

        if updated:
            save_reminders(reminders)
        await asyncio.sleep(60)

# --- Основна функція ---
async def main():
    logging.info("🚀 Запуск бота...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("remind", remind_command))

    await app.initialize()
    await app.start()
    asyncio.create_task(reminder_loop(app))
    logging.info("✅ Бот готовий до роботи!")
    await app.updater.start_polling()

# --- Запуск з Nest Asyncio ---
nest_asyncio.apply()
loop = asyncio.get_event_loop()
loop.create_task(main())
loop.run_forever()
