#проверка свежести кода
import time
print(f"[ENV] loaded {__name__}.py at {time.strftime('%Y-%m-%d %H:%M:%S')}")

import logging
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler, 
    filters, ContextTypes, ConversationHandler
)
import asyncio


from handler_userdata import handle_userdata
from menu_states import SUPPLIER, INGEST
from workers.blob_worker import init_worker as init_blob_worker
from workers.reference_worker import init_worker as init_reference_worker
from workers.excel_worker import init_worker as init_excel_worker
from workers.telegram_notifier import init_worker as init_telegram_notifier
from workers.noprice_collector import init_worker as init_noprice_collector
from utils.logger import setup_logging



import core.graph_loader as gl




# Логирование
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

setup_logging()

#to prevent console prints
from config import TOKEN 


logger = logging.getLogger(__name__)


# /start - personal messages
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return
    # Load graph snapshot into parser memory
    gl.reload_graph_cache()
    print(f"[CACHE] brands={len(gl.BRAND_KEYMAP)} canonicals={len(gl.CANONICAL_NAMES)}")
    print(f"[CACHE] using snapshot from {gl.CACHE_LOADED_AT}")

    context.chat_data["_conv_active"] = True
    context.chat_data["_fsm"] = "SUPPLIER"
    keyboard = [
        [KeyboardButton("Поставщик 1"), KeyboardButton("Поставщик 2")],
        [KeyboardButton("Поставщик 3"), KeyboardButton("Определить по названию файла")],
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Добрый день! Выберите имя поставщика кнопкой или введите клавиатурой.\n"
        "Затем отправьте прайс (Excel/CSV) или вставьте прайс текстом.",
        reply_markup=reply_markup
    )
    return SUPPLIER

#group messages


async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):

    msg = update.message
    chat = update.effective_chat

    supplier = chat.title   # supplier = group name

    # store supplier for downstream ingest logic
    context.chat_data["supplier_choice"] = supplier

    logger.info(
        f"[GROUP INGEST] supplier={supplier} "
        f"chat_id={chat.id} "
        f"text={msg.text!r} "
        f"doc={msg.document.file_name if msg.document else None}"
    )

    # call existing ingest pipeline
    await handle_userdata(update, context)


# выбор поставщика
async def handle_supplier_choice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.chat_data["_conv_active"] = True
    context.chat_data["_fsm"] = "INGEST"

    choice = update.message.text
    logger.info(f"Поставщик выбран: {choice}")

    # фиксированные кнопки
    fixed_choices = ["Поставщик 1", "Поставщик 2", "Поставщик 3", "Определить по названию файла"]

    # проверяем длину текста
    if len(choice) > 20 and choice not in fixed_choices:
        await update.message.reply_text("Число символов превышено, попробуйте заново.")
        return  # ничего не делаем дальше
    
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
    if update.effective_chat.type != "private":
        return
    await update.message.reply_text("Сначала выберите поставщика (/start), затем пришлите прайс (файл или текст).")

# /cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return ConversationHandler.END

    context.chat_data["_conv_active"] = False
    context.chat_data["_fsm"] = "END"
    await update.message.reply_text("Диалог завершён.")
    return ConversationHandler.END

# Заглушка для текстов
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return ConversationHandler.END

    await update.message.reply_text("Используйте /start, чтобы вернуться в меню.")

# Ошибки
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Update {update} caused error {context.error}")

# Фолбэк: если файл прислали вне диалога
async def handle_file_outside_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return ConversationHandler.END

    await update.message.reply_text("Пожалуйста, сначала введите /start и выберите поставщика.")

# Фолбэк: если текст прислали вне диалога
async def handle_text_outside_dialog(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        return ConversationHandler.END

    if context.chat_data.get("_conv_active"):
        return
    await update.message.reply_text("Используйте /start, чтобы начать работу.")

# Запуск
def main():
    print("Бот запускается...")
    print(f"[DEBUG] TOKEN = {repr(TOKEN)}")

    app = (Application.builder().token(TOKEN).concurrent_updates(False).read_timeout(60).write_timeout(60).build())
    
    #будим работников
    init_blob_worker()
    init_reference_worker()
    init_excel_worker()
    init_telegram_notifier(app.bot)
    init_noprice_collector(app.bot)
    logger.info("[BUS] Работники разбужены: blob_worker, reference_worker, excel_worker, telegram_notifier, noprice_collector")


    #group chat
    group_handler = MessageHandler(
        (filters.ChatType.GROUP | filters.ChatType.SUPERGROUP)
        & ~filters.COMMAND
        & (
            filters.Document.FileExtension("xlsx")
            | filters.Document.FileExtension("csv")
            | filters.TEXT
        ),
        handle_group_message
    )

    app.add_handler(group_handler, group=-1)

    # --- Диалог ---
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command, filters=filters.ChatType.PRIVATE)],
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

if __name__ == "__main__":
    main()
