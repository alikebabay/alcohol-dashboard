from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
import asyncio
from dispatcher import dispatch_excel
from io import BytesIO
import pandas as pd

from menu_states import SUPPLIER, INGEST

import logging
logger = logging.getLogger(__name__)

async def handle_userdata(update: Update, context: ContextTypes.DEFAULT_TYPE):   

    supplier_choice = context.chat_data.get("supplier_choice")
    chat_type = update.effective_chat.type
    is_group = chat_type in ("group", "supergroup")

    logger.info(f"[handle_userdata] Получен ввод, supplier_choice={supplier_choice}")
    logger.info(f"[handle_userdata] supplier={supplier_choice} chat_type={chat_type}")


    # ───────────────────────────────────────────────
    # 🧩 Проверка: если пользователь случайно прислал короткий текст
    # ───────────────────────────────────────────────
    if update.message.text:
        text = update.message.text.strip()
        if len(text) < 60 and not update.message.document:
            logger.info(
                f"[handle_userdata] Ignored short message ({len(text)}) in group={is_group}"
            )
            if not is_group:
                await update.message.reply_text(
                    "Наверное, вы отправили текст по ошибке. "
                    "Оффер поставщика обычно превышает по длине 100 символов.\n\n"
                    "Пожалуйста, отправьте Excel-файл или полный текст оффера."
                )
                logger.info(f"[handle_userdata] Игнорировано короткое сообщение ({len(text)} символов)")
            return INGEST # возвращаемся к состоянию ожидания ввода
        # ───────────────────────────────────────────────

    # ───────────────────────────────────────────────
    # Notify user only in private chat
    # ───────────────────────────────────────────────
    if not is_group:
        await update.message.reply_text("Данные получены. Обработка займёт несколько секунд")
        
    df_out = await dispatch_excel(update, context, supplier_choice)
    #оповещаем об отсутствии колонок с ценами
    if df_out is None:
        return INGEST
    # groups: stop here (silent ingest)
    if is_group:
        logger.info("[GROUP INGEST] completed silently")
        return
    # запись результата обратно в Excel - for dialoges
    bio_out = BytesIO()
    with pd.ExcelWriter(bio_out, engine="xlsxwriter") as writer:
        df_out.to_excel(writer, index=False)
    bio_out.seek(0)

    out_name = f"Цены поставщика {supplier_choice}.xlsx"
    await update.message.reply_document(document=bio_out, filename=out_name)
    await update.message.reply_text("Диалог завершён. Чтобы начать заново, нажмите /start")

    context.chat_data.clear()
    context.chat_data["_conv_active"] = False
    context.chat_data["_fsm"] = "END"
    return ConversationHandler.END