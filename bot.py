import os
import asyncio
import logging
from threading import Thread
from flask import Flask
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

# --- Веб-сервер для Render ---
app = Flask(__name__)

@app.route('/')
def index():
    return "Bot is running"

# --- Логика бота ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("Привет! Напиши сюда своё признание, и я отправлю его в канал анонимно.")

@dp.message()
async def confession_handler(message: Message, bot: Bot):
    text = message.text
    if not text:
        await message.answer("Пожалуйста, отправь текстовое сообщение.")
        return
    try:
        await bot.send_message(chat_id=CHANNEL_ID, text=text)
        await message.answer("✅ Твоё признание отправлено в канал!")
    except Exception as e:
        await message.answer("❌ Ошибка при отправке. Проверь, что бот админ в канале.")
        logging.error(f"Ошибка отправки: {e}")

async def main():
    bot = Bot(token=BOT_TOKEN)
    await dp.start_polling(bot)

def run_bot():
    asyncio.run(main())

if __name__ == "__main__":
    # Запускаем бота в отдельном потоке
    bot_thread = Thread(target=run_bot)
    bot_thread.start()
    
    # Запускаем веб-сервер, чтобы Render видел порт
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
