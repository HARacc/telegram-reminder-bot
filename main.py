import json
import os
import asyncio
import logging
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
from dotenv import load_dotenv
import nest_asyncio

logging.basicConfig(level=logging.INFO)
print("⏳ Запуск бота...")

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
REMINDER_FILE = "reminders.json"

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
        text = " ".join(context.args[1:])
        daily = False

        if "щодня" in text.lower():
            text = text.replace("щодня", "").strip()
            daily = True

        reminders = load_reminders()
        reminders.append({
            "chat_id": update.effective_chat.id,
            "time": time_str,
            "text": text,
            "sent": False,
            "daily": daily
        })
        save_reminders(reminders)

        repeat_note = " (щодня)" if daily else ""
        await update.message.reply_text(f"✅ Нагадування встановлено на {time_str}{repeat_note}: {text}")
    except Exception as e:
        logging.error(f"Помилка у /remind: {e}")
        await update.message.reply_text("❌ Формат: /remind 14:00 [щодня] випий ліки")

async def cancelall_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    reminders = load_reminders()
    reminders = [r for r in reminders if not (r["chat_id"] == chat_id and r.get("daily", False))]
    save_reminders(reminders)
    await update.message.reply_text("🗑️ Всі щоденні нагадування видалено.")

async def reminder_loop(app):
    logging.info("📡 Фоновий процес нагадувань запущено")
    while True:
        now = datetime.now().strftime("%H:%M")
        reminders = load_reminders()
        for reminder in reminders:
            if reminder["time"] == now and (not reminder["sent"] or reminder.get("daily", False)):
                await app.bot.send_message(chat_id=reminder["chat_id"], text=f"⏰ Нагадування: {reminder['text']}")
                if not reminder.get("daily", False):
                    reminder["sent"] = True
        save_reminders(reminders)
        await asyncio.sleep(60)

async def main():
    logging.info("🚀 Ініціалізація бота...")
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("remind", remind_command))
    app.add_handler(CommandHandler("cancelall", cancelall_command))
    await app.initialize()
    await app.start()
    asyncio.create_task(reminder_loop(app))
    logging.info("✅ Бот запущено. Очікування команд...")
    await app.updater.start_polling()

nest_asyncio.apply()
loop = asyncio.get_event_loop()
loop.create_task(main())
loop.run_forever()
