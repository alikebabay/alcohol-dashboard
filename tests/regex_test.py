import re
import pytest
from libraries.regular_expressions import RX_GBX_MARKER, RX_GBX_NEGATIVE

@pytest.mark.parametrize("text", [
    # --- neutral words using 'box' in non-gift sense ---
    "Box of 6 bottles",
    "24x200ml box",
    "12x75cl carton box",
    "Case box of 12",
    "Cardboard box 6 bottles",
    "Boxed wine 3L",
    "Shipping box 500ml",
    "Giftbox dimensions: 30x40cm",   # not product name
    "BOX OF CASES",
    "Wooden box packaging",           # descriptive, not GB
    "Display box of 24 minis",
    "Box (not GB)",
    "NonGBX version",
    "NGBX sample text",
    "No box included",
    "per box",
    "Without box packaging",
])
def test_gbx_contamination(text):
    """Ensure RX_GBX_MARKER does NOT fire on unrelated 'box' contexts."""
    has_neg = bool(RX_GBX_NEGATIVE.search(text))
    has_pos = bool(RX_GBX_MARKER.search(text))
    contamination = has_pos and not has_neg
    assert not contamination, f"False positive contamination: {text!r}"
