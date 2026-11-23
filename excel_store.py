"""Ghi thông tin khách lưu trú vào file Excel.

- Nếu file chưa có: tự tạo với các cột mặc định.
- Nếu file đã có (mẫu riêng của bạn): tự dò dòng tiêu đề và khớp cột theo tên
  (ví dụ "Họ tên", "Họ và tên khách", "Số CCCD", "Ngày đến"...), rồi ghi vào
  dòng trống tiếp theo. Cột nào không khớp được sẽ được thêm vào cuối.
"""

from __future__ import annotations

import os
import unicodedata
from datetime import date, datetime

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

# key nội bộ -> (tiêu đề mặc định, các từ khóa để nhận diện cột trong file có sẵn)
COLUMNS: list[tuple[str, str, list[str]]] = [
    ("stt", "STT", ["stt", "so thu tu", "tt"]),
    ("ho_ten", "Họ và tên", ["ho ten", "ho va ten", "ten khach", "ho ten khach", "ten"]),
    ("ngay_sinh", "Ngày sinh", ["ngay sinh", "ngay thang nam sinh", "nam sinh"]),
    ("gioi_tinh", "Giới tính", ["gioi tinh", "gioi"]),
    ("so_cccd", "Số CCCD", ["so cccd", "cccd", "can cuoc", "so dinh danh", "cmnd", "so giay to", "giay to"]),
    ("loai_giay_to", "Loại giấy tờ", ["loai giay to", "loai khach", "giay to tuy than"]),
    ("dia_chi", "Địa chỉ", ["dia chi", "thuong tru", "noi cu tru", "noi thuong tru", "cho o"]),
    ("ngay_den", "Ngày đến", ["ngay den", "ngay luu tru", "ngay nhan phong", "tu ngay", "check in", "ngay vao"]),
    ("ngay_di", "Ngày đi", ["ngay di", "ngay tra phong", "den ngay", "check out", "ngay ra"]),
    ("phong", "Phòng", ["phong", "so phong", "can ho"]),
    ("ghi_chu", "Ghi chú", ["ghi chu"]),
    ("thoi_gian_nhap", "Thời gian nhập", ["thoi gian nhap", "ngay nhap"]),
]
DATE_KEYS = {"ngay_den", "ngay_di"}


def _norm(s) -> str:
    s = str(s or "").strip().lower().replace("đ", "d")
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return " ".join("".join(c if c.isalnum() else " " for c in s).split())


def _match_key(header) -> str | None:
    h = _norm(header)
    if not h:
        return None
    # khớp chính xác trước, rồi mới khớp "chứa", ưu tiên từ khóa dài
    for key, _, kws in COLUMNS:
        if h in kws:
            return key
    best = None
    for key, _, kws in COLUMNS:
        for kw in kws:
            if len(kw) > 3 and kw in h and (best is None or len(kw) > best[1]):
                best = (key, len(kw))
    return best[0] if best else None


_THIN = Side(style="thin", color="999999")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)


def _create(path: str, sheet: str) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = sheet
    widths = {"stt": 6, "ho_ten": 26, "ngay_sinh": 12, "gioi_tinh": 9, "so_cccd": 16, "loai_giay_to": 13, "dia_chi": 50,
              "ngay_den": 12, "ngay_di": 12, "phong": 9, "ghi_chu": 20, "thoi_gian_nhap": 18}
    for i, (key, title, _) in enumerate(COLUMNS, start=1):
        c = ws.cell(row=1, column=i, value=title)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor="1F6F8B")
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = _BORDER
        ws.column_dimensions[c.column_letter].width = widths.get(key, 14)
    ws.freeze_panes = "A2"
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    wb.save(path)


def _find_header(ws) -> tuple[int, dict[str, int]]:
    """Tìm dòng tiêu đề trong 15 dòng đầu: dòng khớp được nhiều cột nhất."""
    best_row, best_map = 0, {}
    for r in range(1, min(ws.max_row, 15) + 1):
        m: dict[str, int] = {}
        for c in range(1, ws.max_column + 1):
            key = _match_key(ws.cell(r, c).value)
            if key and key not in m:
                m[key] = c
        if len(m) > len(best_map):
            best_row, best_map = r, m
    return best_row, best_map


def _last_data_row(ws, header_row: int, cols: dict[str, int]) -> int:
    check = [cols[k] for k in ("ho_ten", "so_cccd") if k in cols] or list(cols.values())
    last = header_row
    for r in range(header_row + 1, ws.max_row + 1):
        if any(ws.cell(r, c).value not in (None, "") for c in check):
            last = r
    return last


def _open(path: str, sheet: str):
    if not os.path.exists(path):
        _create(path, sheet)
    wb = load_workbook(path)
    ws = wb[sheet] if sheet in wb.sheetnames else wb.active
    header_row, cols = _find_header(ws)
    if header_row == 0:  # sheet trống
        header_row = 1
        for i, (key, title, _) in enumerate(COLUMNS, start=1):
            ws.cell(1, i, title).font = Font(bold=True)
            cols[key] = i
    return wb, ws, header_row, cols


def _to_date(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    try:
        return datetime.strptime(str(v).strip(), "%d/%m/%Y").date()
    except ValueError:
        return v


def find_duplicate(path: str, sheet: str, rec: dict) -> int | None:
    """Trả về số dòng nếu khách đã có với cùng ngày đến.

    So sánh theo số CCCD nếu có; nếu không (trẻ em, bằng lái xe) thì theo họ tên + ngày sinh.
    """
    if not os.path.exists(path):
        return None
    wb, ws, header_row, cols = _open(path, sheet)
    so_cccd = str(rec.get("so_cccd") or "").strip()
    if so_cccd:
        keys = {"so_cccd": so_cccd}
    else:
        keys = {"ho_ten": _norm(rec.get("ho_ten")), "ngay_sinh": str(rec.get("ngay_sinh") or "").strip()}
    if not all(k in cols for k in keys) or not all(keys.values()):
        return None
    nd = _to_date(rec.get("ngay_den"))
    for r in range(header_row + 1, ws.max_row + 1):
        ok = True
        for k, v in keys.items():
            cell = ws.cell(r, cols[k]).value
            cell = _norm(cell) if k == "ho_ten" else (
                cell.strftime("%d/%m/%Y") if isinstance(cell, (date, datetime)) else str(cell or "").strip())
            if cell != v:
                ok = False
                break
        if ok and ("ngay_den" not in cols or _to_date(ws.cell(r, cols["ngay_den"]).value) == nd):
            return r
    return None


def append_guest(path: str, record: dict, sheet: str = "Khach luu tru") -> int:
    """Ghi 1 khách vào dòng trống tiếp theo. Trả về số dòng đã ghi."""
    wb, ws, header_row, cols = _open(path, sheet)

    # Thêm cột còn thiếu (chỉ những cột có dữ liệu cần ghi)
    for key, title, _ in COLUMNS:
        if key not in cols and record.get(key) not in (None, "") and key != "stt":
            col = ws.max_column + 1
            ws.cell(header_row, col, title).font = Font(bold=True)
            cols[key] = col

    row = _last_data_row(ws, header_row, cols) + 1
    record = dict(record)
    record.setdefault("thoi_gian_nhap", datetime.now().strftime("%d/%m/%Y %H:%M"))
    if "stt" in cols:
        record["stt"] = row - header_row

    for key, col in cols.items():
        val = record.get(key)
        if val in (None, ""):
            continue
        cell = ws.cell(row, col)
        if key in DATE_KEYS:
            val = _to_date(val)
            if isinstance(val, date):
                cell.number_format = "DD/MM/YYYY"
        cell.value = val
        if key == "so_cccd":
            cell.number_format = "@"  # giữ số 0 ở đầu
        cell.border = _BORDER
        cell.alignment = Alignment(vertical="center", wrap_text=(key == "dia_chi"))

    wb.save(path)
    return row


def read_all(path: str, sheet: str = "Khach luu tru"):
    """Đọc toàn bộ dữ liệu (để hiển thị trong ứng dụng)."""
    if not os.path.exists(path):
        return [], []
    wb, ws, header_row, _ = _open(path, sheet)
    headers = [ws.cell(header_row, c).value or "" for c in range(1, ws.max_column + 1)]
    rows = []
    for r in range(header_row + 1, ws.max_row + 1):
        vals = [ws.cell(r, c).value for c in range(1, ws.max_column + 1)]
        if any(v not in (None, "") for v in vals):
            rows.append([v.strftime("%d/%m/%Y") if isinstance(v, (date, datetime)) else v for v in vals])
    return headers, rows
