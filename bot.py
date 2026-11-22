import os
import logging
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# --- Настройки ---
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_ID", "").split(",") if x.strip()]
RENDER_EXTERNAL_URL = os.getenv("RENDER_EXTERNAL_URL")

WEBHOOK_PATH = "/webhook"
WEBHOOK_URL = f"{RENDER_EXTERNAL_URL}{WEBHOOK_PATH}"

logging.basicConfig(level=logging.INFO)
dp = Dispatcher()

processed_messages = set()

class AdminReply(StatesGroup):
    waiting_for_reply_text = State()

@dp.message(Command("start"))
async def start_handler(message: Message):
    await message.answer("Привет! Напиши сюда своё признание, и я отправлю его на проверку.")

@dp.message(F.chat.type == "private")
async def confession_handler(message: Message, state: FSMContext):
    if message.from_user.id in ADMIN_IDS:
        return

    text = message.text
    if not text:
        await message.answer("Пожалуйста, отправь текстовое сообщение.")
        return

    msg_unique_id = f"{message.from_user.id}_{message.message_id}"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Опубликовать", callback_data=f"approve_{msg_unique_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_{msg_unique_id}"),
            InlineKeyboardButton(text="💬 Ответить", callback_data=f"reply_{msg_unique_id}")
        ]
    ])

    admin_text = (
        f"📩 **Новое признание!**\n\n"
        f"👤 От: {message.from_user.full_name} (@{message.from_user.username})\n"
        f"🆔 ID: `{message.from_user.id}`\n\n"
        f"Текст:\n{text}"
    )

    # Безопасная рассылка всем админам
    for admin_id in ADMIN_IDS:
        try:
            await message.bot.send_message(
                chat_id=admin_id,
                text=admin_text,
                reply_markup=keyboard,
                parse_mode="Markdown"
            )
            logging.info(f"Сообщение успешно отправлено админу {admin_id}")
        except Exception as e:
            logging.error(f"ОШИБКА: Не удалось отправить админу {admin_id}. Причина: {e}")

    await message.answer("✅ Твоё сообщение отправлено на проверку!")

@dp.callback_query(F.data.startswith(("approve_", "reject_", "reply_")))
async def process_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("У вас нет прав.", show_alert=True)
        return

    if callback.data in processed_messages:
        await callback.answer("Слишком поздно! Это сообщение уже обработал другой админ.", show_alert=True)
        return
    
    processed_messages.add(callback.data)

    action, unique_id = callback.data.split("_", 1)
    target_user_id = int(unique_id.split("_")[0])
    
    full_text = callback.message.text
    if "Текст:\n" in full_text:
        original_text = full_text.split("Текст:\n", 1)[1]
    else:
        original_text = full_text

    if action == "approve":
        try:
            quoted_text = f"<blockquote>{original_text}</blockquote>"
            await callback.bot.send_message(chat_id=CHANNEL_ID, text=quoted_text, parse_mode="HTML")
            new_text = f"{full_text}\n\n✅ **ОПУБЛИКОВАНО**"
        except Exception as e:
            new_text = f"{full_text}\n\n❌ **Ошибка:** {e}"
    elif action == "reject":
        new_text = f"{full_text}\n\n❌ **ОТКЛОНЕНО**"
    elif action == "reply":
        await state.set_state(AdminReply.waiting_for_reply_text)
        await state.update_data(target_user_id=target_user_id, original_message_text=original_text)
        await callback.message.answer("✍️ Введите текст ответа для автора:")
        await callback.answer()
        return

    await callback.message.edit_text(new_text, parse_mode="Markdown")
    await callback.answer()

    for admin_id in ADMIN_IDS:
        if admin_id != callback.from_user.id:
            try:
                await callback.bot.send_message(
                    chat_id=admin_id,
                    text=f"⚠️ Сообщение уже обработано другим админом.\n\n{new_text}",
                    parse_mode="Markdown"
                )
            except Exception as e:
                logging.error(f"Не удалось уведомить админа {admin_id}: {e}")

@dp.message(AdminReply.waiting_for_reply_text, F.text)
async def send_reply_to_user(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    data = await state.get_data()
    target_user_id = data.get("target_user_id")
    original_text = data.get("original_message_text")

    if not target_user_id:
        await message.answer("Ошибка: не удалось найти получателя.")
        await state.clear()
        return

    try:
        logging.info(f"Попытка отправить ответ пользователю {target_user_id}")
        reply_text = (
            f"💌 **Ответ на ваше сообщение:**\n\n"
            f"Ваше сообщение:\n> {original_text}\n\n"
            f"Ответ:\n{message.text}"
        )
        await message.bot.send_message(chat_id=target_user_id, text=reply_text, parse_mode="Markdown")
        await message.answer("✅ Ответ успешно отправлен автору!")
        logging.info(f"Ответ успешно отправлен {target_user_id}")
    except Exception as e:
        await message.answer(f"❌ Не удалось отправить ответ: {e}")
        logging.error(f"Ошибка отправки ответа: {e}")

    await state.clear()

async def healthcheck(request):
    return web.Response(text="Bot is running")

async def on_startup(bot: Bot):
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL, allowed_updates=["message", "callback_query"])
    logging.info(f"Вебхук установлен на {WEBHOOK_URL}")

def main():
    app = web.Application()
    bot = Bot(token=BOT_TOKEN)

    app.router.add_get('/', healthcheck)
    webhook_requests_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_requests_handler.register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    dp.startup.register(on_startup)

    port = int(os.environ.get("PORT", 10000))
    web.run_app(app, host="0.0.0.0", port=port)

if __name__ == "__main__":
    main()
