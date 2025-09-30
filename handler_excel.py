from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
import asyncio
from dispatcher import dispatch_excel
from io import BytesIO
import pandas as pd

import logging
logger = logging.getLogger(__name__)

async def handle_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    
    doc = update.message.document
    if not doc:
        return

    # 1. определяем имя файла и поставщика
    supplier_choice = context.chat_data.get("supplier_choice")
    file_name = doc.file_name or "unnamed.xlsx"    

    logger.info(f"[handle_excel] Получен файл: {file_name}, supplier_choice={supplier_choice}")

    await update.message.reply_text("Файл получен. Обработка займёт ~15 секунд")

    # 2. качаем байты в память
    file_bytes = await (await context.bot.get_file(doc.file_id)).download_as_bytearray()
    bio = BytesIO(file_bytes)

    # 3. Передаём BytesIO и имя файла в диспетчер
    df_out = await asyncio.get_running_loop().run_in_executor(
        None, lambda: dispatch_excel(bio, file_name, supplier_choice)
    )

    # 4. Конвертируем DataFrame обратно в Excel и отправляем пользователю
    bio_out = BytesIO()
    df_out.to_excel(bio_out, index=False)
    bio_out.seek(0)

    await update.message.reply_document(document=bio_out, filename=f"processed_{file_name}")

    # 5. Сообщение о завершении диалога
    await update.message.reply_text("Диалог завершён. Чтобы начать заново, нажмите /start")
    # --- сбрасываем данные ---
    context.chat_data.clear()
    context.user_data.clear()
    return ConversationHandler.END