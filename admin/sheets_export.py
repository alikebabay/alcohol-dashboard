# admin/sheets_export.py
import logging
from integrations.graph_to_sheets import get_all_offers, make_master_sheet, upload_to_gsheets

logger = logging.getLogger(__name__)

def rebuild_master_sheet(max_pairs: int = 12) -> dict:
    df_all = get_all_offers()
    master = make_master_sheet(df_all, max_pairs=max_pairs)
    upload_to_gsheets(master)

    return {
        "ok": True,
        "rows": int(len(master)),
        "max_pairs": int(max_pairs),
    }
