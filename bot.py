import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# --- Настройки ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
# Render автоматически подставит сюда твой адрес сайта
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL") 

# Путь, по которому Telegram будет присылать сообщения
WEBHOOK_PATH = "/webhook"
# Полный адрес для вебхука
WEBHOOK_URL = f"{RENDER_EXTERNAL_URL}{WEBHOOK_PATH}"

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("Привет! Напиши сюда своё признание, и я отправлю его в канал анонимно.")

@dp.message()
async def confession_handler(message: Message):
    text = message.text
    if not text:
        await message.answer("Пожалуйста, отправь текстовое сообщение.")
        return
    try:
        await message.bot.send_message(chat_id=CHANNEL_ID, text=text)
        await message.answer("✅ Твоё признание отправлено в канал!")
    except Exception as e:
        await message.answer("❌ Ошибка при отправке. Проверь, что бот админ в канале.")
        logging.error(f"Ошибка отправки: {e}")

# Функция, которая сработает при запуске сервера
async def on_startup(bot: Bot):
    # Говорим Telegram, куда присылать сообщения
    await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
    logging.info(f"Вебхук установлен на {WEBHOOK_URL}")

def main():
    # Создаём приложение aiohttp
    app = web.Application()
    
    # Создаём бота и диспетчер
    bot = Bot(token=BOT_TOKEN)
    
    # Регистрируем обработчик вебхука
    webhook_requests_handler = SimpleRequestHandler(
        dispatcher=dp,
        bot=bot,
    )
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    
    # Добавляем действие при запуске (установка вебхука)
    setup_application(app, dp, bot=bot)
    dp.startup.register(on_startup)
    
    # Запускаем веб-сервер
    port = int(os.environ.get("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
