"""
Export care locations to CSV, JSON, and Excel.
"""

import csv
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List

from models import CareLocation
from config.settings import OUTPUT_DIR

logger = logging.getLogger(__name__)


def _ensure_dir():
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)


def _timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M")


def to_csv(locations: List[CareLocation], filename: str = None) -> str:
    _ensure_dir()
    if not filename:
        filename = os.path.join(OUTPUT_DIR, f"zorg_locaties_{_timestamp()}.csv")

    if not locations:
        logger.warning("Geen locaties om te exporteren naar CSV.")
        return filename

    fieldnames = list(locations[0].to_dict().keys())
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for loc in locations:
            writer.writerow(loc.to_dict())

    logger.info("CSV opgeslagen: %s (%d rijen)", filename, len(locations))
    return filename


def to_json(locations: List[CareLocation], filename: str = None) -> str:
    _ensure_dir()
    if not filename:
        filename = os.path.join(OUTPUT_DIR, f"zorg_locaties_{_timestamp()}.json")

    data = [loc.to_dict() for loc in locations]
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    logger.info("JSON opgeslagen: %s (%d items)", filename, len(data))
    return filename


def to_excel(locations: List[CareLocation], filename: str = None) -> str:
    """Export to Excel. Requires openpyxl."""
    try:
        import openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.utils import get_column_letter
    except ImportError:
        logger.warning("openpyxl niet geïnstalleerd; Excel export overgeslagen.")
        return ""

    _ensure_dir()
    if not filename:
        filename = os.path.join(OUTPUT_DIR, f"zorg_locaties_{_timestamp()}.xlsx")

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Zorg Locaties"

    if not locations:
        wb.save(filename)
        return filename

    headers = list(locations[0].to_dict().keys())
    header_font  = Font(bold=True, color="FFFFFF")
    header_fill  = PatternFill("solid", fgColor="1F4E79")
    alt_fill     = PatternFill("solid", fgColor="D9E1F2")

    for col_idx, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col_idx, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")

    for row_idx, loc in enumerate(locations, 2):
        row_data = list(loc.to_dict().values())
        fill = alt_fill if row_idx % 2 == 0 else None
        for col_idx, value in enumerate(row_data, 1):
            cell = ws.cell(row=row_idx, column=col_idx, value=value)
            if fill:
                cell.fill = fill

    # Auto-size columns
    for col_idx, _ in enumerate(headers, 1):
        col_letter = get_column_letter(col_idx)
        ws.column_dimensions[col_letter].auto_size = True

    ws.freeze_panes = "A2"
    wb.save(filename)
    logger.info("Excel opgeslagen: %s (%d rijen)", filename, len(locations))
    return filename


def export_all(locations: List[CareLocation]) -> dict:
    """Export to all formats; returns dict of {format: filepath}."""
    ts = _timestamp()
    base = os.path.join(OUTPUT_DIR, f"zorg_locaties_{ts}")
    return {
        "csv":   to_csv(locations,   base + ".csv"),
        "json":  to_json(locations,  base + ".json"),
        "excel": to_excel(locations, base + ".xlsx"),
    }
