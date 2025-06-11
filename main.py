import json
import os
import asyncio
import logging
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv
import nest_asyncio
import requests

logging.basicConfig(level=logging.INFO)

# Завантаження змінних
load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
SERVER_URL = os.getenv("SERVER_URL") 
REMINDER_FILE = "reminders.json"

# Нагадування
def load_reminders():
    if os.path.exists(REMINDER_FILE):
        with open(REMINDER_FILE, "r") as f:
            return json.load(f)
    return []

def save_reminders(reminders):
    with open(REMINDER_FILE, "w") as f:
        json.dump(reminders, f, indent=2)

async def remind_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        time_str = context.args[0]
        message = " ".join(context.args[1:])
        hour, minute = map(int, time_str.split(":"))
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
    except:
        await update.message.reply_text("❌ Формат: /remind 14:00 текст")

async def remind_daily_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        time_str = context.args[0]
        message = " ".join(context.args[1:])
        hour, minute = map(int, time_str.split(":"))
        reminders = load_reminders()
        reminders.append({
            "chat_id": update.effective_chat.id,
            "time": time_str,
            "text": message,
            "daily": True
        })
        save_reminders(reminders)
        await update.message.reply_text(f"✅ Щоденне нагадування на {time_str}: {message}")
    except:
        await update.message.reply_text("❌ Формат: /remind_daily 08:00 текст")

async def remind_remove_all(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reminders = load_reminders()
    reminders = [r for r in reminders if not r.get("daily", False)]
    save_reminders(reminders)
    await update.message.reply_text("🗑️ Усі щоденні нагадування видалено.")

async def threshold_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        if not context.args:
            await update.message.reply_text("❌ Вкажи поріг. Наприклад: /threshold 0.3")
            return
        value = float(context.args[0])
        response = requests.post(f"{SERVER_URL}/update_threshold", json={"threshold": value})
        if response.status_code == 200:
            await update.message.reply_text(f"✅ Поріг оновлено до {value:.3f}")
        else:
            await update.message.reply_text(f"❌ Помилка: {response.text}")
    except Exception as e:
        await update.message.reply_text(f"❌ Помилка: {e}")

# Фоновий процес
async def reminder_loop(app):
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

async def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("remind", remind_command))
    app.add_handler(CommandHandler("remind_daily", remind_daily_command))
    app.add_handler(CommandHandler("remind_remove_all", remind_remove_all))
    app.add_handler(CommandHandler("threshold", threshold_command))
    await app.initialize()
    await app.start()
    asyncio.create_task(reminder_loop(app))
    await app.updater.start_polling()

nest_asyncio.apply()
loop = asyncio.get_event_loop()
loop.create_task(main())
loop.run_forever()
