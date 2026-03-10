# workers/telegram_notifier.py

import logging
from workers.event_bus import subscribe

logger = logging.getLogger(__name__)

NO_PRICE_MSG = (
    "Processing is not possible because no price was detected.\n\n"
    "Possible reasons:\n"
    "• the currency is not specified (EUR, USD, etc.), or\n"
    "• the price is not provided together with a currency.\n\n"
    "Please clarify the price and currency and try again."
)


def init_worker(bot):

    async def on_ingest_failed(payload: dict):

        chat_id = payload.get("chat_id")
        reason = payload.get("reason")

        if not chat_id:
            logger.error("[telegram_notifier] missing chat_id in payload")
            return

        # Telegram groups always have negative chat_id
        if chat_id < 0:
            logger.info("[telegram_notifier] silent failure in group")
            return

        if reason == "NO_PRICE":
            await bot.send_message(chat_id=chat_id, text=NO_PRICE_MSG)

    subscribe("ingest.failed", on_ingest_failed)

    logger.info("[telegram_notifier] subscribed to ingest.failed")