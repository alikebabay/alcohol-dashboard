# event_bus.py
import asyncio

# хранилище подписчиков
_subscribers = {}

def subscribe(event_type: str, callback):
    """Регистрирует обработчик для события"""
    if event_type not in _subscribers:
        _subscribers[event_type] = []
    _subscribers[event_type].append(callback)
    print(f"[BUS] подписан {callback.__name__} на '{event_type}'")

async def publish(event_type: str, payload: dict):
    """Рассылает событие всем подписанным колбэкам"""
    if event_type not in _subscribers:
        print(f"[BUS] нет подписчиков для {event_type}")
        return

    for cb in _subscribers[event_type]:
        asyncio.create_task(cb(payload))  # не ждём — асинхронно
    print(f"[BUS] событие {event_type} опубликовано для {_subscribers[event_type]}")
