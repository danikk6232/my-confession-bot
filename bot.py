import os
import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message

# Берем данные из настроек Render
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

if __name__ == "__main__":
    asyncio.run(main())
