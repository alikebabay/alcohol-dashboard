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

    logger.info(f"[handle_userdata] Получен ввод, supplier_choice={supplier_choice}")
    await update.message.reply_text("Данные получены. Обработка займёт несколько секунд")
        
    df_out = await dispatch_excel(update, context, supplier_choice)

    # общее: результат обратно в Excel
    bio_out = BytesIO()
    df_out.to_excel(bio_out, index=False)
    bio_out.seek(0)

    out_name = f"Цены поставщика {supplier_choice}.xlsx"
    await update.message.reply_document(document=bio_out, filename=out_name)
    await update.message.reply_text("Диалог завершён. Чтобы начать заново, нажмите /start")

    context.chat_data.clear()
    context.user_data.clear()
    context.chat_data["_conv_active"] = False
    context.chat_data["_fsm"] = "END"
    return ConversationHandler.END