# workers/noprice_collector.py

from workers.event_bus import subscribe
import logging

logger = logging.getLogger(__name__)


def init_worker(bot):

    async def on_parse_finished(payload: dict):

        logger.debug(
            "[noprice_collector] payload keys=%s mapping=%r",
            list(payload.keys()),
            payload.get("mapping"),
        )

        chat_id = payload.get("chat_id")
        mapping = payload.get("mapping", {})

        if not chat_id:
            logger.error("[noprice_collector] missing chat_id")
            return

        # 🔇 silence supplier groups
        if chat_id < 0:
            logger.debug("[noprice_collector] group chat → silent")
            return

        noprice = mapping.get("noprice_lines") or []

        if not noprice:
            logger.debug("[noprice_collector] no noprice lines")
            return

        # dedupe + cap (safety)
        unique = list(dict.fromkeys(noprice))[:20]

        msg_lines = [
            "⚠️ *Some product lines look valid but no reliable price was detected:*",
            "",
        ]

        for line in unique:
            msg_lines.append(f"• `{line}`")

        msg_lines.append("")
        msg_lines.append(
            "Please clarify the price (with currency) for these lines."
        )

        text = "\n".join(msg_lines)

        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode="Markdown",
        )

        logger.info(
            "[noprice_collector] sent %d noprice lines to chat_id=%s",
            len(unique), chat_id
        )

    subscribe("parse_finished", on_parse_finished)

    logger.info("[noprice_collector] subscribed to parse_finished")