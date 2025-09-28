from telegram import Update
from telegram.ext import ContextTypes
import asyncio
from dispatcher import dispatch_excel
from io import BytesIO


async def handle_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc:
        return

    file_name = doc.file_name or "unnamed.xlsx"
    # 1. качаем байты в память
    file_bytes = await (await context.bot.get_file(doc.file_id)).download_as_bytearray()
    bio = BytesIO(file_bytes)

    # 2. Передаём BytesIO и имя файла в диспетчер
    out_path = await asyncio.get_running_loop().run_in_executor(
        None, lambda: dispatch_excel(bio, file_name)
    )

    # 3. Отправляем результат как раньше
    await update.message.reply_document(open(out_path, "rb"))
