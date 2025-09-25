from telegram import Update
from telegram.ext import ContextTypes
import asyncio
from pathlib import Path
from dispatcher import dispatch_excel

async def handle_excel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    doc = update.message.document
    if not doc:
        return

    file_name = doc.file_name or "unnamed.xlsx"
    file_path = Path("test_documents") / file_name
    await (await context.bot.get_file(doc.file_id)).download_to_drive(str(file_path))

    out_path = await asyncio.get_running_loop().run_in_executor(None, lambda: dispatch_excel(file_path))
    await update.message.reply_document(open(out_path, "rb"))
