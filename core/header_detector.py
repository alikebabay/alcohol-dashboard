# core/header_detector.py
"""
Plain-text structural header detector.
Works similarly to ExcelFSM header logic:
    HEADER REGION = before the first product line
    DATA REGION   = after the first product

Other modules (AccessAssistant, LocationAssistant, Verifier)
can call detect_headers(lines) to understand where headers end.
"""

from __future__ import annotations
import logging
import re
from typing import List, Tuple

from libraries.distillator import looks_like_product

logger = logging.getLogger(__name__)

# optional: treat email / footer contacts as NOT headers
RX_SIGNATURE = re.compile(
    r"(kind\s+regards|best\s+regards|www\.|@\w+\.\w+|mobile|whatsapp|phone)",
    re.I,
)


def is_signature(line: str) -> bool:
    """Lines that clearly cannot be headers."""
    if not line.strip():
        return False
    return bool(RX_SIGNATURE.search(line))


def is_noise_line(line: str) -> bool:
    """
    Things like:
        "WHISKY STOCK OFFER EX LOENDERSLOOT"
        "SPECIAL PRICE LIST"
        "OFFER EX LOENDERSLOOT"
    We treat them as part of header/preamble.
    """
    s = line.strip().lower()
    if not s:
        return True
    # Long lines without numbers are likely titles
    has_num = bool(re.search(r"\d", s))
    return not has_num


def detect_headers(lines: List[str]) -> Tuple[int, List[str]]:
    """
    Input:
        lines – list[str] raw text split by lines

    Output:
        (header_end_index, header_lines)

    Meaning:
        Header region = lines[0 : header_end_index]
        Data region   = lines[header_end_index : ]

    This allows AccessAssistant to:
        - treat access inside header region as header_hint
        - treat access after header region as footer only
    """

    first_product_idx = None

    for i, raw in enumerate(lines):
        s = raw.strip()
        if not s:
            continue

        # explicit non-header
        if is_signature(s):
            continue

        # detect product
        if looks_like_product(s):
            first_product_idx = i
            logger.debug(f"[HEADER-DETECT] first product at line {i}: {s!r}")
            break

        # Otherwise it's header/intro/noise – continue scanning
        logger.debug(f"[HEADER-DETECT] pre-data line {i}: {s!r}")

    # If no product found → full text is header (rare but valid)
    if first_product_idx is None:
        logger.debug("[HEADER-DETECT] no product lines → whole text is header")
        return len(lines), list(lines)

    header_end = first_product_idx
    header_lines = lines[:header_end]

    logger.debug(
        f"[HEADER-DETECT] header_end={header_end}, total_lines={len(lines)}, "
        f"header_size={len(header_lines)}"
    )

    return header_end, header_lines
