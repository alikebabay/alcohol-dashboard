from io import BytesIO

async def load(update, context):
    """
    Унифицирует вход от Telegram:
    - если текст → вернёт (str, "text_input.txt")
    - если документ → вернёт (BytesIO, file_name)
    """
    if update.message.text:
        return update.message.text, "text_input.txt"

    elif update.message.document:
        doc = update.message.document
        file_name = doc.file_name or "unnamed.xlsx"
        file_bytes = await (await context.bot.get_file(doc.file_id)).download_as_bytearray()
        return BytesIO(file_bytes), file_name

    else:
        raise ValueError("Unsupported input type")
