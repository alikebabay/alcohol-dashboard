from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
import asyncio
from dispatcher import dispatch_excel
from io import BytesIO
import pandas as pd

import logging
logger = logging.getLogger(__name__)

async def handle_userdata(update: Update, context: ContextTypes.DEFAULT_TYPE):
    supplier_choice = context.chat_data.get("supplier_choice")

    if update.message.document:
        # --- режим файла ---
        doc = update.message.document
        file_name = doc.file_name or "unnamed.xlsx"
        logger.info(f"[handle_userdata] Получен файл: {file_name}, supplier_choice={supplier_choice}")
        await update.message.reply_text("Файл получен. Обработка займёт ~15 секунд")

        file_bytes = await (await context.bot.get_file(doc.file_id)).download_as_bytearray()
        bio = BytesIO(file_bytes)
        df_out = await asyncio.get_running_loop().run_in_executor(
            None, lambda: dispatch_excel(bio, file_name, supplier_choice)
        )

    else:
        # --- режим текста ---
        raw_text = update.message.text
        logger.info(f"[handle_userdata] Получен текст, supplier_choice={supplier_choice}")
        await update.message.reply_text("Текст получен. Обработка займёт несколько секунд")

        df_out = await asyncio.get_running_loop().run_in_executor(
            None, lambda: dispatch_excel(raw_text, "text_input.txt", supplier_choice)
        )

    # общее: результат обратно в Excel
    bio_out = BytesIO()
    df_out.to_excel(bio_out, index=False)
    bio_out.seek(0)

    out_name = f"processed_{file_name}" if update.message.document else "processed_text.xlsx"
    await update.message.reply_document(document=bio_out, filename=out_name)
    await update.message.reply_text("Диалог завершён. Чтобы начать заново, нажмите /start")

    context.chat_data.clear()
    context.user_data.clear()
    context.chat_data["_conv_active"] = False
    context.chat_data["_fsm"] = "END"
    return ConversationHandler.END