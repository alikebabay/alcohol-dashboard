import asyncio
from workers.noprice_collector import init_worker

class FakeBot:
    async def send_message(self, chat_id, text, parse_mode=None):
        print("SEND_MESSAGE CALLED")
        print("chat_id:", chat_id)
        print(text)

async def test():
    bot = FakeBot()
    init_worker(bot)

    # import your event bus publish
    from workers.event_bus import publish

    payload = {
        "chat_id": 123,
        "mapping": {
            "noprice_lines": [
                "MOET 0.75L",
                "JACK DANIELS 1L"
            ]
        }
    }

    await publish("parse_finished", payload)

asyncio.run(test())
