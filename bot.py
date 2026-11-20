import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

# --- Настройки ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
ADMIN_ID = int(os.getenv("ADMIN_ID")) # Ваш личный ID
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL") 

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{RENDER_EXTERNAL_URL}{WEBHOOK_PATH}"

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()

# --- Обработка команды /start ---
@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("Привет! Напиши сюда своё признание, и я отправлю его на проверку администратору.")

# --- Обработка сообщений от пользователей ---
@dp.message()
async def confession_handler(message: Message):
    # Если пишет сам админ, игнорируем (или можно сделать отдельную логику)
    if message.from_user.id == ADMIN_ID:
        return

    text = message.text
    if not text:
        await message.answer("Пожалуйста, отправь текстовое сообщение.")
        return

    # Создаем кнопки
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Опубликовать", callback_data="approve"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data="reject")
        ]
    ])

    # Формируем сообщение для вас (с именем отправителя, но в канал это не уйдет)
    admin_text = (
        f"📩 **Новое признание!**\n\n"
        f"👤 От: {message.from_user.full_name} (@{message.from_user.username})\n"
        f"🆔 ID: `{message.from_user.id}`\n\n"
        f"Текст:\n{text}"
    )

    # Отправляем вам на модерацию
    await message.bot.send_message(
        chat_id=ADMIN_ID, 
        text=admin_text, 
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    
    # Говорим пользователю, что сообщение ушло на проверку
    await message.answer("✅ Твоё сообщение отправлено на проверку администратору!")

# --- Обработка нажатий на кнопки (Только для админа) ---
@dp.callback_query(F.data.in_({"approve", "reject"}))
async def process_callback(callback: CallbackQuery):
    # Проверяем, что нажал именно админ
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет прав на это действие.", show_alert=True)
        return

    # Извлекаем исходный текст из сообщения (отрезаем шапку)
    # Текст у нас начинается после "Текст:\n"
    full_text = callback.message.text
    try:
        original_text = full_text.split("Текст:\n", 1)[1]
    except IndexError:
        original_text = "Ошибка: текст не найден"

    if callback.data == "approve":
        try:
            # Отправляем в канал (только чистый текст!)
            await callback.bot.send_message(chat_id=CHANNEL_ID, text=original_text)
            await callback.message.edit_text(f"{callback.message.text}\n\n✅ **ОПУБЛИКОВАНО**")
        except Exception as e:
            await callback.message.edit_text(f"{callback.message.text}\n\n❌ **Ошибка публикации:** {e}")
    else:
        # Если отклонили
        await callback.message.edit_text(f"{callback.message.text}\n\n❌ **ОТКЛОНЕНО**")
    
    await callback.answer() # Убираем часики на кнопке

# --- Запуск (для Render) ---
async def on_startup(bot: Bot):
    await bot.set_webhook(WEBHOOK_URL, drop_pending_updates=True)
    logging.info(f"Вебхук установлен на {WEBHOOK_URL}")

def main():
    app = web.Application()
    bot = Bot(token=BOT_TOKEN)
    
    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    dp.startup.register(on_startup)
    
    port = int(os.environ.get("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
