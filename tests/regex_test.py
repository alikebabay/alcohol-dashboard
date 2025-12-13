import re
from libraries.patterns import RX_FLOOR

POSITIVE = [
    "ON THE FLOOR",
    "on the floor",
    "T2 / ON THE FLOOR",
    "on-the-floor",
    "on_the_floor",
    "stocked and on floor",
    "item is on floor now",
    "available ON FLOOR",
]

NEGATIVE = [
    "delivery on floor 3",
    "on floor 20",
    "the pallets are on floor 2",
    "container floor 3",
    "storage floor racks",
]

def test_floor_positive():
    for text in POSITIVE:
        assert RX_FLOOR.search(text), f"Should match: {text!r}"

def test_floor_negative():
    for text in NEGATIVE:
        assert not RX_FLOOR.search(text), f"False positive: {text!r}"
