#проверка свежести кода
import time
print(f"[ENV] loaded {__name__}.py at {time.strftime('%Y-%m-%d %H:%M:%S')}")

import logging
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    filters, ContextTypes, ConversationHandler
)
from config import TOKEN 
from handler_excel import handle_excel


# Логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния
MENU = 0

# /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("Local")],
        [KeyboardButton("Europe")],
        [KeyboardButton("Asia")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Добрый день! Отправьте прайс от поставщика в формате Excel или CSV для обработки.\n",
        reply_markup=reply_markup
    )
    return MENU

# Выбор района
async def handle_district_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_input = update.message.text.lower()
    if "медеуский" in user_input:
        await update.message.reply_text("Не понял ввод. Пожалуйста, отправьте прайс в формате Excel или CSV.")
    else:
        await update.message.reply_text("Пока поддерживается только отправка файла. Нажмите /start.")
    return MENU

# /cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Диалог завершён.")
    return ConversationHandler.END

# Заглушка для текстов
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Используйте /start, чтобы вернуться в меню.")

# Ошибки
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")

# Запуск
def main():
    print("Бот запускается...")

    app = (Application.builder().token(TOKEN).concurrent_updates(False).read_timeout(60).write_timeout(60).build())

    # Диалог
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={MENU: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_district_choice)]},
        fallbacks=[CommandHandler("cancel", cancel)],
        per_message=True,   # перезапуск диалога на каждое сообщение
    )
    app.add_handler(conv_handler)

    # Обработка Excel/CSV файлов
    
    app.add_handler(MessageHandler(filters.Document.FileExtension("xlsx") | filters.Document.FileExtension("csv"), handle_excel))
    print("[DEBUG main] Handler для Excel/CSV добавлен")


    # Общие ответы
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Ошибки
    app.add_error_handler(error)

    print("Опрашиваем...")
    app.run_polling(poll_interval=20)

if __name__ == "__main__":
    main()
