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
from handler_userdata import handle_userdata


# Логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния диалога
SUPPLIER, INGEST = range(2)

# /start
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.chat_data["_conv_active"] = True
    context.chat_data["_fsm"] = "SUPPLIER"
    keyboard = [
        [KeyboardButton("Поставщик 1"), KeyboardButton("Поставщик 2")],
        [KeyboardButton("Поставщик 3"), KeyboardButton("По названию файла")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Добрый день! Сначала выберите поставщика кнопкой или введите его название.\n"
        "Затем отправьте прайс (Excel/CSV) или вставьте прайс текстом.",
        reply_markup=reply_markup
    )
    return SUPPLIER

# выбор поставщика
async def handle_supplier_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.chat_data["_conv_active"] = True
    context.chat_data["_fsm"] = "INGEST"

    choice = update.message.text
    logger.info(f"Поставщик выбран: {choice}")

    # фиксированные кнопки
    fixed_choices = ["Поставщик 1", "Поставщик 2", "Поставщик 3", "По названию файла"]
    if choice in fixed_choices:
        context.chat_data["supplier_choice"] = choice
        await update.message.reply_text(
            f"Вы выбрали: {choice}. Теперь отправьте прайс Excel/CSV или пришлите текстовый прайс."
        )
        return INGEST
    
    # если не кнопка → трактуем как ручной ввод
    context.chat_data["supplier_choice"] = choice
    await update.message.reply_text(
        f"Принято: {choice}. Теперь отправьте прайс Excel/CSV или пришлите текстовый прайс."
    )
    return INGEST


# Если прислали файл до выбора поставщика
async def handle_wrong_before_supplier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Сначала выберите поставщика (/start), затем пришлите прайс (файл или текст).")

# /cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.chat_data["_conv_active"] = False
    context.chat_data["_fsm"] = "END"
    await update.message.reply_text("Диалог завершён.")
    return ConversationHandler.END

# Заглушка для текстов
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Используйте /start, чтобы вернуться в меню.")

# Ошибки
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")

# Фолбэк: если файл прислали вне диалога
async def handle_file_outside_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Пожалуйста, сначала введите /start и выберите поставщика.")

# Фолбэк: если текст прислали вне диалога
async def handle_text_outside_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.chat_data.get("_conv_active"):
        return
    await update.message.reply_text("Используйте /start, чтобы начать работу.")

# Запуск
def main():
    print("Бот запускается...")

    app = (Application.builder().token(TOKEN).concurrent_updates(False).read_timeout(60).write_timeout(60).build())

    # --- Диалог ---
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            # Этап 1: выбираем поставщика
            SUPPLIER: [
                # кнопки или ручной ввод названия поставщика
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_supplier_choice),
                # если прилетел файл раньше времени — вежливо просим выбрать поставщика
                MessageHandler(filters.Document.FileExtension("xlsx") | filters.Document.FileExtension("csv"),
                               handle_wrong_before_supplier),
            ],
            # Этап 2: принимаем прайс (файл или текст)
            INGEST: [
                MessageHandler(
                    (filters.Document.FileExtension("xlsx") | filters.Document.FileExtension("csv")),
                    handle_userdata
                ),
                MessageHandler(
                    (filters.TEXT & ~filters.COMMAND),
                    handle_userdata
                ),
            ],
        },
         # ВАЖНО: fallbacks здесь работают только КОГДА диалог активен.
        fallbacks=[CommandHandler("cancel", cancel)],
        allow_reentry=True
    )

    app.add_handler(conv_handler, group=0)

    
    # --- Вне диалога (глобальные фолбэки) ---
    # Сработают, только если conv_handler НЕ перехватил апдейт
    app.add_handler(
        MessageHandler(
            filters.Document.FileExtension("xlsx") | filters.Document.FileExtension("csv"),
            handle_file_outside_dialog
        ),
        group=1
    )
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_outside_dialog),
        group=1
    )

    # Ошибки
    app.add_error_handler(error)

    print("Опрашиваем...")
    app.run_polling(poll_interval=1)

if __name__ == "__main__":
    main()
