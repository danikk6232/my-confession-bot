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
ADMIN_ID = int(os.getenv("ADMIN_ID"))
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL") 

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{RENDER_EXTERNAL_URL}{WEBHOOK_PATH}"

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("Привет! Напиши сюда своё признание, и я отправлю его на проверку.")

@dp.message(F.chat.type == "private")
async def confession_handler(message: Message):
    if message.from_user.id == ADMIN_ID:
        return

    text = message.text
    if not text:
        await message.answer("Пожалуйста, отправь текстовое сообщение.")
        return

    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Опубликовать", callback_data="approve"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data="reject")
        ]
    ])

    admin_text = (
        f"📩 **Новое признание!**\n\n"
        f"👤 От: {message.from_user.full_name} (@{message.from_user.username})\n"
        f"🆔 ID: `{message.from_user.id}`\n\n"
        f"Текст:\n{text}"
    )

    await message.bot.send_message(
        chat_id=ADMIN_ID, 
        text=admin_text, 
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await message.answer("✅ Твоё сообщение отправлено на проверку!")

@dp.callback_query(F.data.in_({"approve", "reject"}))
async def process_callback(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("У вас нет прав.", show_alert=True)
        return

    full_text = callback.message.text
    if "Текст:\n" in full_text:
        original_text = full_text.split("Текст:\n", 1)[1]
    else:
        original_text = full_text

    if callback.data == "approve":
        try:
            await callback.bot.send_message(chat_id=CHANNEL_ID, text=original_text)
            await callback.message.edit_text(f"{full_text}\n\n✅ **ОПУБЛИКОВАНО**", parse_mode="Markdown")
        except Exception as e:
            await callback.message.edit_text(f"{full_text}\n\n❌ **Ошибка:** {e}", parse_mode="Markdown")
    else:
        await callback.message.edit_text(f"{full_text}\n\n❌ **ОТКЛОНЕНО**", parse_mode="Markdown")
    
    await callback.answer()

# --- Заглушка для проверки сервера (чтобы Render не ругался) ---
async def healthcheck(request):
    return web.Response(text="Bot is running")

async def on_startup(bot: Bot):
    # ВАЖНО: удаляем старый вебхук и ставим новый, чтобы Telegram точно знал, куда стучаться
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    logging.info(f"Вебхук установлен на {WEBHOOK_URL}")

def main():
    app = web.Application()
    bot = Bot(token=BOT_TOKEN)
    
    # Регистрируем заглушку
    app.router.add_get('/', healthcheck)
    
    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    
    setup_application(app, dp, bot=bot)
    dp.startup.register(on_startup)
    
    port = int(os.environ.get("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
