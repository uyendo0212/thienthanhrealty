"""Ghi thông tin khách lưu trú vào file Excel.

Có 2 mẫu (profile): "vn" cho khách Việt Nam và "nn" cho khách nước ngoài.
- Nếu file chưa có: tự tạo với các cột mặc định của mẫu.
- Nếu file đã có (mẫu riêng của bạn): tự dò dòng tiêu đề và khớp cột theo tên
  (ví dụ "Họ tên", "Số CCCD", "Số hộ chiếu", "Quốc tịch", "Ngày đến"...), rồi ghi
  vào dòng trống tiếp theo. Cột nào cần ghi mà file chưa có sẽ được thêm vào cuối.
"""

from __future__ import annotations

import os
import unicodedata
from datetime import date, datetime

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

# key nội bộ -> (tiêu đề mặc định, độ rộng, các từ khóa để nhận diện cột trong file có sẵn)
COLUMNS: dict[str, tuple[str, int, list[str]]] = {
    "stt": ("STT", 6, ["stt", "so thu tu", "tt"]),
    "ho_ten": ("Họ và tên", 26, ["ho ten", "ho va ten", "ten khach", "ho ten khach", "ten", "full name", "name"]),
    "ngay_sinh": ("Ngày sinh", 12, ["ngay sinh", "ngay thang nam sinh", "nam sinh", "date of birth", "dob"]),
    "gioi_tinh": ("Giới tính", 9, ["gioi tinh", "gioi", "sex", "gender"]),
    "quoc_tich": ("Quốc tịch", 14, ["quoc tich", "nationality"]),
    "so_cccd": ("Số CCCD", 16, ["so cccd", "cccd", "can cuoc", "so dinh danh", "cmnd"]),
    "so_ho_chieu": ("Số hộ chiếu", 14, ["so ho chieu", "ho chieu", "passport", "passport no"]),
    "loai_giay_to": ("Loại giấy tờ", 13, ["loai giay to", "loai khach", "giay to tuy than"]),
    "so_thi_thuc": ("Số thị thực", 14, ["so thi thuc", "thi thuc", "visa", "visa no"]),
    "han_thi_thuc": ("Thị thực có giá trị đến", 14, ["han thi thuc", "thoi han thi thuc", "thi thuc co gia tri den",
                                                     "gia tri den", "visa expiry"]),
    "dia_chi": ("Địa chỉ", 50, ["dia chi", "thuong tru", "noi cu tru", "noi thuong tru", "cho o"]),
    "ngay_den": ("Ngày đến", 12, ["ngay den", "ngay luu tru", "ngay nhan phong", "tu ngay", "check in", "ngay vao"]),
    "ngay_di": ("Ngày đi", 12, ["ngay di", "ngay tra phong", "den ngay", "check out", "ngay ra",
                                "du kien di"]),
    "phong": ("Phòng", 9, ["phong", "so phong", "can ho"]),
    "ghi_chu": ("Ghi chú", 20, ["ghi chu"]),
    "thoi_gian_nhap": ("Thời gian nhập", 18, ["thoi gian nhap", "ngay nhap"]),
}

# Mẫu cột mặc định khi tạo file mới
PROFILES = {
    "vn": ["stt", "ho_ten", "ngay_sinh", "gioi_tinh", "so_cccd", "loai_giay_to", "dia_chi",
           "ngay_den", "ngay_di", "phong", "ghi_chu", "thoi_gian_nhap"],
    "nn": ["stt", "ho_ten", "ngay_sinh", "gioi_tinh", "quoc_tich", "so_ho_chieu", "loai_giay_to",
           "so_thi_thuc", "han_thi_thuc", "ngay_den", "ngay_di", "phong", "ghi_chu", "thoi_gian_nhap"],
}
# Cột "Số giấy tờ" chung chung: khách VN -> số CCCD, khách nước ngoài -> số hộ chiếu
GENERIC_ID = {"vn": "so_cccd", "nn": "so_ho_chieu"}
GENERIC_ID_KWS = ["so giay to", "giay to", "so giay to tuy than"]
DATE_KEYS = {"ngay_den", "ngay_di"}


def _norm(s) -> str:
    s = str(s or "").strip().lower().replace("đ", "d")
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return " ".join("".join(c if c.isalnum() else " " for c in s).split())


def _keywords(profile: str):
    for key, (_, _, kws) in COLUMNS.items():
        yield key, kws
    yield GENERIC_ID[profile], GENERIC_ID_KWS


def _match_key(header, profile: str) -> str | None:
    h = _norm(header)
    if not h:
        return None
    for key, kws in _keywords(profile):  # khớp chính xác trước
        if h in kws:
            return key
    best = None  # rồi khớp "chứa", ưu tiên từ khóa dài nhất
    for key, kws in _keywords(profile):
        for kw in kws:
            if len(kw) > 3 and kw in h and (best is None or len(kw) > best[1]):
                best = (key, len(kw))
    return best[0] if best else None


_THIN = Side(style="thin", color="999999")
_BORDER = Border(left=_THIN, right=_THIN, top=_THIN, bottom=_THIN)


def _create(path: str, sheet: str, profile: str) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = sheet
    _write_headers(ws, profile)
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    wb.save(path)


def _write_headers(ws, profile: str) -> dict[str, int]:
    color = "1F6F8B" if profile == "vn" else "8B5A1F"
    cols = {}
    for i, key in enumerate(PROFILES[profile], start=1):
        title, width, _ = COLUMNS[key]
        c = ws.cell(row=1, column=i, value=title)
        c.font = Font(bold=True, color="FFFFFF")
        c.fill = PatternFill("solid", fgColor=color)
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = _BORDER
        ws.column_dimensions[c.column_letter].width = width
        cols[key] = i
    ws.freeze_panes = "A2"
    return cols


def _find_header(ws, profile: str) -> tuple[int, dict[str, int]]:
    """Tìm dòng tiêu đề trong 15 dòng đầu: dòng khớp được nhiều cột nhất."""
    best_row, best_map = 0, {}
    for r in range(1, min(ws.max_row, 15) + 1):
        m: dict[str, int] = {}
        for c in range(1, ws.max_column + 1):
            key = _match_key(ws.cell(r, c).value, profile)
            if key and key not in m:
                m[key] = c
        if len(m) > len(best_map):
            best_row, best_map = r, m
    if len(best_map) < 2:  # không phải dòng tiêu đề thật
        return 0, {}
    return best_row, best_map


def _last_data_row(ws, header_row: int, cols: dict[str, int]) -> int:
    check = [cols[k] for k in ("ho_ten", "so_cccd", "so_ho_chieu") if k in cols] or list(cols.values())
    last = header_row
    for r in range(header_row + 1, ws.max_row + 1):
        if any(ws.cell(r, c).value not in (None, "") for c in check):
            last = r
    return last


def _open(path: str, sheet: str, profile: str):
    if not os.path.exists(path):
        _create(path, sheet, profile)
    wb = load_workbook(path)
    if sheet in wb.sheetnames:
        ws = wb[sheet]
    else:  # cùng 1 file nhưng sheet khác (ví dụ tab "Khách nước ngoài")
        ws = wb.create_sheet(sheet)
    header_row, cols = _find_header(ws, profile)
    if header_row == 0:
        if ws.max_row > 1 or ws.cell(1, 1).value not in (None, ""):
            # sheet có dữ liệu nhưng không nhận ra tiêu đề: thêm tiêu đề ở dòng tiếp theo
            header_row = ws.max_row + 2
            for i, key in enumerate(PROFILES[profile], start=1):
                ws.cell(header_row, i, COLUMNS[key][0]).font = Font(bold=True)
                cols[key] = i
        else:
            header_row, cols = 1, _write_headers(ws, profile)
    return wb, ws, header_row, cols


def _to_date(v):
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    s = str(v or "").strip()
    for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return v


def _cell_text(v) -> str:
    if isinstance(v, (date, datetime)):
        return v.strftime("%d/%m/%Y")
    return str(v or "").strip()


def find_duplicate(path: str, sheet: str, rec: dict, profile: str = "vn") -> int | None:
    """Trả về số dòng nếu khách đã có với cùng ngày đến.

    So sánh theo số CCCD / số hộ chiếu nếu có; nếu không thì theo họ tên + ngày sinh.
    """
    if not os.path.exists(path):
        return None
    wb, ws, header_row, cols = _open(path, sheet, profile)
    keys = {}
    for k in ("so_cccd", "so_ho_chieu"):
        if str(rec.get(k) or "").strip() and k in cols:
            keys = {k: str(rec[k]).strip().upper()}
            break
    if not keys:
        keys = {"ho_ten": _norm(rec.get("ho_ten")), "ngay_sinh": str(rec.get("ngay_sinh") or "").strip()}
    if not all(k in cols for k in keys) or not all(keys.values()):
        return None
    nd = _to_date(rec.get("ngay_den"))
    for r in range(header_row + 1, ws.max_row + 1):
        ok = True
        for k, v in keys.items():
            cell = ws.cell(r, cols[k]).value
            cell = _norm(cell) if k == "ho_ten" else _cell_text(cell).upper()
            if cell != (v if k == "ho_ten" else v.upper()):
                ok = False
                break
        if ok and ("ngay_den" not in cols or _to_date(ws.cell(r, cols["ngay_den"]).value) == nd):
            return r
    return None


def _set(ws, row: int, col: int, key: str, val) -> None:
    cell = ws.cell(row, col)
    if key in DATE_KEYS:
        val = _to_date(val)
        if isinstance(val, date):
            cell.number_format = "DD/MM/YYYY"
    cell.value = val
    if key in ("so_cccd", "so_ho_chieu", "so_thi_thuc"):
        cell.number_format = "@"  # giữ số 0 ở đầu
    cell.border = _BORDER
    cell.alignment = Alignment(vertical="center", wrap_text=(key == "dia_chi"))


def append_guest(path: str, record: dict, sheet: str, profile: str = "vn") -> int:
    """Ghi 1 khách vào dòng trống tiếp theo. Trả về số dòng đã ghi."""
    wb, ws, header_row, cols = _open(path, sheet, profile)

    # Thêm cột còn thiếu (chỉ những cột có dữ liệu cần ghi)
    for key, (title, _, _) in COLUMNS.items():
        if key not in cols and key != "stt" and record.get(key) not in (None, ""):
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
        if val not in (None, ""):
            _set(ws, row, col, key, val)

    wb.save(path)
    return row


def read_all(path: str, sheet: str, profile: str = "vn"):
    """Đọc toàn bộ dữ liệu. Trả về (tiêu đề, các dòng, số dòng Excel tương ứng, map cột)."""
    if not os.path.exists(path):
        return [], [], [], {}
    wb = load_workbook(path)
    if sheet not in wb.sheetnames:
        return [], [], [], {}
    wb, ws, header_row, cols = _open(path, sheet, profile)
    headers = [ws.cell(header_row, c).value or "" for c in range(1, ws.max_column + 1)]
    rows, row_nums = [], []
    for r in range(header_row + 1, ws.max_row + 1):
        vals = [ws.cell(r, c).value for c in range(1, ws.max_column + 1)]
        if any(v not in (None, "") for v in vals):
            rows.append(vals)
            row_nums.append(r)
    return headers, rows, row_nums, cols


def update_dates(path: str, sheet: str, changes: dict[int, dict], profile: str = "vn") -> int:
    """Sửa ngày đến / ngày đi của các khách đã lưu.

    changes: {số dòng Excel: {"ngay_den": date|None, "ngay_di": date|None}}
    """
    if not changes:
        return 0
    wb, ws, header_row, cols = _open(path, sheet, profile)
    n = 0
    for row, vals in changes.items():
        for key, val in vals.items():
            if key not in DATE_KEYS:
                continue
            if key not in cols:
                col = ws.max_column + 1
                ws.cell(header_row, col, COLUMNS[key][0]).font = Font(bold=True)
                cols[key] = col
            if val in (None, ""):
                ws.cell(row, cols[key]).value = None
            else:
                _set(ws, row, cols[key], key, val)
            n += 1
    wb.save(path)
    return n
