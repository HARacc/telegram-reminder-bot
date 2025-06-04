import json
import os
import asyncio
import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv
import nest_asyncio

# --- Налаштування логів ---
logging.basicConfig(level=logging.INFO)
print("⏳ Запуск бота...")

# --- Завантаження змінних середовища ---
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
REMINDER_FILE = "reminders.json"

# --- Зчитування/збереження нагадувань ---
def load_reminders():
    if os.path.exists(REMINDER_FILE):
        with open(REMINDER_FILE, "r") as f:
            return json.load(f)
    return []

def save_reminders(reminders):
    with open(REMINDER_FILE, "w") as f:
        json.dump(reminders, f, indent=2)

# --- Команда /remind ---
async def remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        time_str = context.args[0]
        message = " ".join(context.args[1:])

        # Перевірка формату часу
        try:
            hour, minute = map(int, time_str.split(":"))
            if not (0 <= hour < 24 and 0 <= minute < 60):
                raise ValueError
        except Exception:
            await update.message.reply_text("❌ Неправильний формат часу. Використовуйте HH:MM (наприклад, 14:30)")
            return

        reminders = load_reminders()
        reminders.append({
            "chat_id": update.effective_chat.id,
            "time": time_str,
            "text": message,
            "sent": False,
            "daily": False
        })
        save_reminders(reminders)
        await update.message.reply_text(f"✅ Одноразове нагадування на {time_str}: {message}")
    except Exception as e:
        logging.error(f"Помилка у /remind: {e}")
        await update.message.reply_text("❌ Формат: /remind 14:00 текст")

# --- Команда /remind_daily ---
async def remind_daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        time_str = context.args[0]
        message = " ".join(context.args[1:])

        try:
            hour, minute = map(int, time_str.split(":"))
            if not (0 <= hour < 24 and 0 <= minute < 60):
                raise ValueError
        except Exception:
            await update.message.reply_text("❌ Неправильний формат часу. Використовуйте HH:MM (наприклад, 08:15)")
            return

        reminders = load_reminders()
        reminders.append({
            "chat_id": update.effective_chat.id,
            "time": time_str,
            "text": message,
            "daily": True
        })
        save_reminders(reminders)
        await update.message.reply_text(f"✅ Щоденне нагадування на {time_str}: {message}")
    except Exception as e:
        logging.error(f"Помилка у /remind_daily: {e}")
        await update.message.reply_text("❌ Формат: /remind_daily 08:15 текст")

# --- Команда для очищення щоденних ---
async def remind_remove_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reminders = load_reminders()
    reminders = [r for r in reminders if not r.get("daily", False)]
    save_reminders(reminders)
    await update.message.reply_text("🗑️ Усі щоденні нагадування видалено.")

# --- Фоновий цикл ---
async def reminder_loop(app):
    logging.info("📡 Фоновий процес нагадувань запущено")
    while True:
        now = (datetime.now() + timedelta(hours=3)).strftime("%H:%M")
        reminders = load_reminders()
        changed = False
        for reminder in reminders:
            if reminder["time"] == now:
                if reminder.get("daily", False):
                    await app.bot.send_message(chat_id=reminder["chat_id"], text=f"📅 Щоденне: {reminder['text']}")
                    changed = True
                elif not reminder.get("sent", False):
                    await app.bot.send_message(chat_id=reminder["chat_id"], text=f"⏰ Нагадування: {reminder['text']}")
                    reminder["sent"] = True
                    changed = True
        if changed:
            save_reminders(reminders)
        await asyncio.sleep(60)

# --- Запуск ---
async def main():
    logging.info("🚀 Ініціалізація бота...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("remind", remind_command))
    app.add_handler(CommandHandler("remind_daily", remind_daily_command))
    app.add_handler(CommandHandler("remind_remove_all", remind_remove_all))

    await app.initialize()
    await app.start()
    asyncio.create_task(reminder_loop(app))
    logging.info("✅ Бот запущено. Очікування команд...")
    await app.updater.start_polling()

# --- Nest_asyncio запуск ---
nest_asyncio.apply()
loop = asyncio.get_event_loop()
loop.create_task(main())
loop.run_forever()
