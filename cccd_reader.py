"""Đọc thông tin khách từ ảnh giấy tờ: CCCD, bằng lái xe, hộ chiếu, thị thực.

Cách đọc, theo thứ tự ưu tiên:
1. CCCD: quét mã QR in trên thẻ (offline, miễn phí, chính xác khi quét được).
   Nội dung QR: SoCCCD|SoCMNDcu|HoTen|NgaySinh(ddmmyyyy)|GioiTinh|DiaChi|NgayCap
2. Các trường hợp khác (bằng lái, hộ chiếu, thị thực, CCCD không quét được QR):
   gửi ảnh cho Claude (AI) đọc. Cần biến môi trường ANTHROPIC_API_KEY.
   Với hộ chiếu / thị thực, AI chép lại 2 dòng mã MRZ ở cuối trang; phần mềm
   tự giải mã MRZ và kiểm tra số kiểm tra (check digit) để xác nhận quốc tịch,
   số hộ chiếu, ngày sinh.
"""

from __future__ import annotations

import base64
import io
import os
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date

import numpy as np
from PIL import Image, ImageOps

try:
    import zxingcpp  # bộ quét QR tốt nhất, ưu tiên dùng
except ImportError:  # pragma: no cover
    zxingcpp = None

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None


# --------------------------------------------------------------------------- #
# Loại khách / giấy tờ và các trường bắt buộc tương ứng
# --------------------------------------------------------------------------- #
LOAI_CCCD = "CCCD"
LOAI_BLX = "Bằng lái xe"
LOAI_HC = "Hộ chiếu"
LOAI_TRE_EM = "Trẻ em"
LOAI_LIST = [LOAI_CCCD, LOAI_BLX, LOAI_HC, LOAI_TRE_EM]
LOAI_HIEN_THI = {LOAI_CCCD: "🪪 CCCD", LOAI_BLX: "🚗 Bằng lái xe",
                 LOAI_HC: "🛂 Hộ chiếu / Thị thực", LOAI_TRE_EM: "🧒 Trẻ em"}

TEN_TRUONG = {"ho_ten": "Họ tên", "ngay_sinh": "Ngày sinh", "so_cccd": "Số CCCD", "dia_chi": "Địa chỉ",
              "quoc_tich": "Quốc tịch", "so_ho_chieu": "Số hộ chiếu", "ngay_den": "Ngày đến"}
BAT_BUOC = {
    LOAI_CCCD: ["ho_ten", "ngay_sinh", "so_cccd", "dia_chi", "ngay_den"],
    LOAI_BLX: ["ho_ten", "ngay_sinh", "dia_chi", "ngay_den"],
    LOAI_HC: ["ho_ten", "ngay_sinh", "quoc_tich", "so_ho_chieu", "ngay_den"],
    LOAI_TRE_EM: ["ho_ten", "ngay_sinh", "ngay_den"],
}


def thieu_truong(loai: str, rec: dict) -> list[str]:
    """Trả về tên các trường bắt buộc còn trống theo loại khách."""
    out = []
    for k in BAT_BUOC.get(loai, BAT_BUOC[LOAI_CCCD]):
        v = rec.get(k)
        if v is None or (isinstance(v, str) and not v.strip()):
            out.append(TEN_TRUONG[k])
    return out


# --------------------------------------------------------------------------- #
# Quốc tịch
# --------------------------------------------------------------------------- #
QUOC_GIA = {  # mã ISO 3 chữ (dùng trong hộ chiếu) -> tên tiếng Việt
    "VNM": "Việt Nam", "CHN": "Trung Quốc", "TWN": "Đài Loan", "HKG": "Hồng Kông", "MAC": "Ma Cao",
    "KOR": "Hàn Quốc", "PRK": "Triều Tiên", "JPN": "Nhật Bản", "USA": "Hoa Kỳ", "CAN": "Canada",
    "GBR": "Anh", "FRA": "Pháp", "DEU": "Đức", "D": "Đức", "ITA": "Ý", "ESP": "Tây Ban Nha",
    "PRT": "Bồ Đào Nha", "NLD": "Hà Lan", "BEL": "Bỉ", "CHE": "Thụy Sĩ", "AUT": "Áo", "SWE": "Thụy Điển",
    "NOR": "Na Uy", "DNK": "Đan Mạch", "FIN": "Phần Lan", "POL": "Ba Lan", "CZE": "Séc", "HUN": "Hungary",
    "RUS": "Nga", "UKR": "Ukraina", "BLR": "Belarus", "KAZ": "Kazakhstan", "TUR": "Thổ Nhĩ Kỳ",
    "IRL": "Ireland", "GRC": "Hy Lạp", "ISR": "Israel", "ARE": "UAE", "SAU": "Ả Rập Xê Út",
    "IND": "Ấn Độ", "PAK": "Pakistan", "BGD": "Bangladesh", "LKA": "Sri Lanka", "NPL": "Nepal",
    "THA": "Thái Lan", "LAO": "Lào", "KHM": "Campuchia", "MMR": "Myanmar", "MYS": "Malaysia",
    "SGP": "Singapore", "IDN": "Indonesia", "PHL": "Philippines", "BRN": "Brunei", "TLS": "Đông Timor",
    "MNG": "Mông Cổ", "AUS": "Úc", "NZL": "New Zealand", "BRA": "Brazil", "ARG": "Argentina",
    "MEX": "Mexico", "CHL": "Chile", "COL": "Colombia", "PER": "Peru", "ZAF": "Nam Phi",
    "EGY": "Ai Cập", "NGA": "Nigeria", "KEN": "Kenya", "MAR": "Ma Rốc", "IRN": "Iran",
}


def _bo_dau(s: str) -> str:
    s = (s or "").strip().lower().replace("đ", "d")
    s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
    return " ".join(re.sub(r"[^a-z0-9]", " ", s).split())


def ten_quoc_gia(ma: str) -> str:
    return QUOC_GIA.get((ma or "").upper().replace("<", ""), "")


def la_nguoi_nuoc_ngoai(quoc_tich: str) -> bool:
    """Quốc tịch trống hoặc là Việt Nam -> khách Việt Nam; còn lại là người nước ngoài."""
    q = _bo_dau(quoc_tich)
    return bool(q) and q not in ("viet nam", "vietnam", "vn", "vnm", "viet nam vnm", "vietnamese")


# --------------------------------------------------------------------------- #
# Dữ liệu khách
# --------------------------------------------------------------------------- #
FIELDS = ("ho_ten", "ngay_sinh", "gioi_tinh", "so_cccd", "dia_chi", "quoc_tich",
          "so_ho_chieu", "so_thi_thuc", "han_thi_thuc", "loai")


@dataclass
class GuestInfo:
    ho_ten: str = ""
    ngay_sinh: str = ""  # dd/mm/yyyy
    gioi_tinh: str = ""
    so_cccd: str = ""
    dia_chi: str = ""
    quoc_tich: str = ""
    so_ho_chieu: str = ""
    so_thi_thuc: str = ""
    han_thi_thuc: str = ""  # dd/mm/yyyy
    loai: str = ""  # loại giấy tờ do phần mềm nhận diện
    nguon: str = ""  # "QR", "AI", "MRZ"
    canh_bao: list[str] = field(default_factory=list)

    def merge(self, other: "GuestInfo", ghi_de: bool = False) -> "GuestInfo":
        """Điền các trường còn trống (hoặc ghi đè nếu ghi_de) bằng dữ liệu từ `other`."""
        for f in FIELDS:
            if getattr(other, f) and (ghi_de or not getattr(self, f)):
                setattr(self, f, getattr(other, f))
        if other.nguon and other.nguon not in self.nguon:
            self.nguon = "+".join(x for x in (self.nguon, other.nguon) if x)
        self.canh_bao.extend(other.canh_bao)
        return self


# --------------------------------------------------------------------------- #
# Tiện ích
# --------------------------------------------------------------------------- #
def _fmt_date(raw: str) -> str:
    """'01011990' -> '01/01/1990'; '1-2-1990' -> '01/02/1990'."""
    raw = (raw or "").strip()
    if re.fullmatch(r"\d{8}", raw):
        return f"{raw[:2]}/{raw[2:4]}/{raw[4:]}"
    m = re.fullmatch(r"(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})", raw)
    if m:
        return f"{int(m[1]):02d}/{int(m[2]):02d}/{m[3]}"
    return raw


def load_image(data: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(data))
    img = ImageOps.exif_transpose(img)  # xoay đúng chiều ảnh chụp điện thoại
    return img.convert("RGB")


# --------------------------------------------------------------------------- #
# 1. Quét QR (CCCD)
# --------------------------------------------------------------------------- #
def parse_qr_text(text: str) -> GuestInfo | None:
    parts = [p.strip() for p in text.strip().split("|")]
    if len(parts) < 6 or not re.fullmatch(r"\d{9,12}", parts[0]):
        return None
    return GuestInfo(
        so_cccd=parts[0],
        ho_ten=parts[2],
        ngay_sinh=_fmt_date(parts[3]),
        gioi_tinh=parts[4],
        dia_chi=parts[5],
        quoc_tich="Việt Nam",
        loai=LOAI_CCCD,
        nguon="QR",
    )


def _qr_candidates(img: Image.Image):
    """Sinh ra các biến thể ảnh (thu phóng, tăng tương phản) để dễ quét."""
    gray = ImageOps.grayscale(img)
    w, h = gray.size
    for scale in (1.0, 0.5, 1.5, 2.0, 0.3):
        if scale != 1.0:
            nw, nh = int(w * scale), int(h * scale)
            if nw < 200 or nw > 5000:
                continue
            g = gray.resize((nw, nh), Image.LANCZOS)
        else:
            g = gray
        yield g
        yield ImageOps.autocontrast(g, cutoff=2)


def read_qr(img: Image.Image) -> GuestInfo | None:
    for cand in _qr_candidates(img):
        texts: list[str] = []
        if zxingcpp is not None:
            try:
                texts = [r.text for r in zxingcpp.read_barcodes(cand)]
            except Exception:
                texts = []
        if not texts and cv2 is not None:
            try:
                ok, decoded, _, _ = cv2.QRCodeDetector().detectAndDecodeMulti(np.array(cand))
                if ok:
                    texts = [t for t in decoded if t]
            except Exception:
                pass
        for t in texts:
            info = parse_qr_text(t)
            if info:
                return info
    return None


# --------------------------------------------------------------------------- #
# 2. Giải mã MRZ (hộ chiếu, thị thực) theo chuẩn ICAO 9303
# --------------------------------------------------------------------------- #
def _check_digit(s: str) -> str:
    total = 0
    for i, ch in enumerate(s):
        if ch.isdigit():
            v = int(ch)
        elif ch.isalpha():
            v = ord(ch.upper()) - 55
        else:
            v = 0
        total += v * (7, 3, 1)[i % 3]
    return str(total % 10)


def _mrz_date(yymmdd: str, tuong_lai: bool) -> str:
    if not re.fullmatch(r"\d{6}", yymmdd):
        return ""
    yy, mm, dd = int(yymmdd[:2]), yymmdd[2:4], yymmdd[4:]
    nay = date.today().year % 100
    if tuong_lai:  # ngày hết hạn: luôn thế kỷ 21
        year = 2000 + yy
    else:  # ngày sinh: không thể ở tương lai
        year = 2000 + yy if yy <= nay else 1900 + yy
    return f"{dd}/{mm}/{year}"


def parse_mrz(lines: list[str]) -> GuestInfo | None:
    """Giải mã 2 dòng MRZ của hộ chiếu (TD3, 44 ký tự) hoặc thị thực (MRV-A 44 / MRV-B 36 ký tự)."""
    ls = [re.sub(r"\s", "", l).upper().replace("«", "<") for l in lines if l and l.strip()]
    ls = [l for l in ls if len(l) >= 30]
    if len(ls) < 2:
        return None
    l1, l2 = ls[-2], ls[-1]
    if l1[0] not in "PV":
        return None
    la_thi_thuc = l1[0] == "V"

    ten = l1[5:].split("<<", 1)
    ho = ten[0].replace("<", " ").strip()
    ten_dem = ten[1].replace("<", " ").strip() if len(ten) > 1 else ""
    ho_ten = " ".join(x for x in (ho, ten_dem) if x)

    so = l2[0:9]
    ok_so = _check_digit(so) == l2[9:10]
    quoc = l2[10:13].replace("<", "")
    ok_sinh = _check_digit(l2[13:19]) == l2[19:20]
    gt = {"M": "Nam", "F": "Nữ"}.get(l2[20:21], "")
    ok_han = _check_digit(l2[21:27]) == l2[27:28]

    info = GuestInfo(ho_ten=ho_ten, quoc_tich=ten_quoc_gia(quoc) or quoc, gioi_tinh=gt, nguon="MRZ",
                     loai=LOAI_HC)
    if ok_sinh:
        info.ngay_sinh = _mrz_date(l2[13:19], tuong_lai=False)
    if la_thi_thuc:
        if ok_so:
            info.so_thi_thuc = so.replace("<", "")
        if ok_han:
            info.han_thi_thuc = _mrz_date(l2[21:27], tuong_lai=True)
    elif ok_so:
        info.so_ho_chieu = so.replace("<", "")
    if not (ok_so and ok_sinh):
        info.canh_bao.append("Mã MRZ đọc được không khớp số kiểm tra — hãy đối chiếu lại số hộ chiếu, ngày sinh.")
    return info


# --------------------------------------------------------------------------- #
# 3. Đọc bằng Claude (AI)
# --------------------------------------------------------------------------- #
MODEL = os.environ.get("CCCD_MODEL", "claude-opus-5-5")

_PROMPT = """Đây là ảnh chụp giấy tờ tùy thân của khách lưu trú: căn cước công dân / thẻ căn cước Việt Nam,
giấy phép lái xe (bằng lái xe) Việt Nam, hộ chiếu (passport), hoặc thị thực (visa). Có thể có nhiều ảnh của cùng
một người (ví dụ trang hộ chiếu và trang thị thực). Hãy đọc chính xác, giữ nguyên dấu tiếng Việt:
- loai_giay_to: "CCCD", "Bằng lái xe", "Hộ chiếu", "Thị thực" (nếu chỉ có thị thực), hoặc "Khác".
- ho_ten: Họ và tên như trên giấy tờ (hộ chiếu nước ngoài: viết HỌ trước rồi TÊN, chữ Latin như trên trang thông tin).
- ngay_sinh: Ngày sinh, định dạng dd/mm/yyyy
- gioi_tinh: "Nam" hoặc "Nữ", để trống nếu không ghi
- quoc_tich: Quốc tịch, viết bằng tiếng Việt (ví dụ "Việt Nam", "Hàn Quốc", "Hoa Kỳ"). CCCD/bằng lái Việt Nam: "Việt Nam".
- ma_quoc_tich: Mã quốc tịch 3 chữ cái theo hộ chiếu (ví dụ VNM, KOR, USA), để trống nếu không có.
- so_cccd: CHỈ với CCCD: số định danh 12 chữ số. Các loại khác để trống.
- so_ho_chieu: Số hộ chiếu (Passport No.), nếu có.
- so_thi_thuc: Số thị thực (visa number), nếu có ảnh thị thực.
- han_thi_thuc: Thị thực có giá trị đến ngày (dd/mm/yyyy), nếu có.
- dia_chi: CCCD cũ: "Nơi thường trú"; thẻ căn cước mới / bằng lái xe: "Nơi cư trú". Hộ chiếu/thị thực: để trống.
  KHÔNG dùng "Quê quán" / "Nơi đăng ký khai sinh" / "Nơi sinh".
- mrz: Nếu có vùng mã MRZ (các dòng ký tự như P<KOR... ở cuối trang hộ chiếu hoặc V<... trên thị thực),
  chép lại CHÍNH XÁC từng dòng, giữ nguyên ký tự '<'. Có nhiều vùng MRZ thì chép tất cả, mỗi dòng một phần tử.
Trường nào không có trong ảnh hoặc không đọc được thì để chuỗi rỗng. Không đoán."""


def _get_schema():
    from typing import Literal

    from pydantic import BaseModel

    class DocFields(BaseModel):
        loai_giay_to: Literal["CCCD", "Bằng lái xe", "Hộ chiếu", "Thị thực", "Khác"]
        ho_ten: str
        ngay_sinh: str
        gioi_tinh: str
        quoc_tich: str
        ma_quoc_tich: str
        so_cccd: str
        so_ho_chieu: str
        so_thi_thuc: str
        han_thi_thuc: str
        dia_chi: str
        mrz: list[str]

    return DocFields


def _to_jpeg_b64(img: Image.Image, max_side: int = 2000) -> str:
    img = img.copy()
    img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return base64.standard_b64encode(buf.getvalue()).decode()


def ai_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def _tach_mrz(lines: list[str]) -> list[list[str]]:
    """Nhóm các dòng MRZ thành từng cặp (mỗi cặp bắt đầu bằng P hoặc V)."""
    ls = [re.sub(r"\s", "", l).upper() for l in lines if l and l.strip()]
    nhom = []
    for i, l in enumerate(ls):
        if l[:1] in "PV" and "<<" in l and i + 1 < len(ls) and re.fullmatch(r"\d{6}", ls[i + 1][13:19]):
            nhom.append([l, ls[i + 1]])
    return nhom


def read_with_ai(images: list[Image.Image]) -> GuestInfo:
    import anthropic

    client = anthropic.Anthropic()
    content = [
        {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": _to_jpeg_b64(im)}}
        for im in images
    ]
    content.append({"type": "text", "text": _PROMPT})

    resp = client.beta.messages.parse(
        model=MODEL,
        max_tokens=4000,
        output_config={"effort": "low"},
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
        output_format=_get_schema(),
        messages=[{"role": "user", "content": content}],
    )
    if resp.stop_reason == "refusal" or resp.parsed_output is None:
        return GuestInfo(nguon="AI", canh_bao=["AI không đọc được ảnh này, vui lòng nhập tay."])

    d = resp.parsed_output
    loai = {"CCCD": LOAI_CCCD, "Bằng lái xe": LOAI_BLX, "Hộ chiếu": LOAI_HC, "Thị thực": LOAI_HC}.get(
        d.loai_giay_to, "")
    quoc_tich = ten_quoc_gia(d.ma_quoc_tich) or d.quoc_tich.strip()
    if loai in (LOAI_CCCD, LOAI_BLX) and not quoc_tich:
        quoc_tich = "Việt Nam"
    info = GuestInfo(
        ho_ten=d.ho_ten.strip(),
        ngay_sinh=_fmt_date(d.ngay_sinh),
        gioi_tinh=d.gioi_tinh.strip(),
        quoc_tich=quoc_tich,
        so_cccd=re.sub(r"\D", "", d.so_cccd) if loai == LOAI_CCCD else "",
        so_ho_chieu=d.so_ho_chieu.strip().upper().replace(" ", ""),
        so_thi_thuc=d.so_thi_thuc.strip().upper().replace(" ", ""),
        han_thi_thuc=_fmt_date(d.han_thi_thuc),
        dia_chi=d.dia_chi.strip() if loai != LOAI_HC else "",
        loai=loai,
        nguon="AI",
    )

    # Xác nhận lại bằng MRZ (có số kiểm tra) — đáng tin hơn đọc chữ thường
    for cap in _tach_mrz(d.mrz):
        mrz = parse_mrz(cap)
        if not mrz:
            continue
        info.ho_ten = info.ho_ten or mrz.ho_ten
        for f in ("quoc_tich", "ngay_sinh", "gioi_tinh", "so_ho_chieu", "so_thi_thuc", "han_thi_thuc"):
            if getattr(mrz, f):
                setattr(info, f, getattr(mrz, f))
        info.canh_bao.extend(mrz.canh_bao)
        if "MRZ" not in info.nguon:
            info.nguon += "+MRZ"

    if d.loai_giay_to == "Khác":
        info.canh_bao.append("Ảnh có vẻ không phải CCCD, bằng lái xe, hộ chiếu hay thị thực — hãy kiểm tra lại.")
    if info.so_cccd and len(info.so_cccd) != 12:
        info.canh_bao.append(f"Số CCCD đọc được có {len(info.so_cccd)} chữ số (thường là 12) — hãy kiểm tra lại.")
    if loai == LOAI_HC and not info.so_ho_chieu:
        info.canh_bao.append("Chưa đọc được số hộ chiếu — nếu chỉ chụp thị thực, hãy chụp thêm trang thông tin hộ chiếu.")
    return info


# --------------------------------------------------------------------------- #
# Hàm chính
# --------------------------------------------------------------------------- #
def extract(images_bytes: list[bytes], use_ai: bool = True, loai: str = "") -> GuestInfo:
    """Nhận 1 hoặc nhiều ảnh giấy tờ của cùng một người.

    `loai` là loại giấy tờ người dùng đã chọn (để trống = tự nhận diện).
    Chỉ CCCD mới có mã QR chứa thông tin; các loại khác cần AI.
    """
    images = [load_image(b) for b in images_bytes]

    result = GuestInfo()
    if loai in ("", LOAI_CCCD):
        for im in images:
            qr = read_qr(im)
            if qr:
                result.merge(qr)
                break

    can = [k for k in BAT_BUOC.get(loai or LOAI_CCCD, []) if k != "ngay_den"]
    missing = any(not getattr(result, k) for k in can) or not result.nguon
    if missing:
        if use_ai and ai_available():
            try:
                result.merge(read_with_ai(images))
            except Exception as e:  # lỗi mạng, sai key...
                result.canh_bao.append(f"Lỗi khi gọi AI: {e}")
        elif not result.nguon:
            result.canh_bao.append(
                "Không quét được mã QR. Hãy chụp lại rõ mã QR, hoặc cài ANTHROPIC_API_KEY để AI đọc chữ trên thẻ."
                if loai in ("", LOAI_CCCD) else
                f"{LOAI_HIEN_THI[loai][2:]} cần AI để đọc — hãy cài ANTHROPIC_API_KEY, hoặc nhập tay."
            )
    if loai and loai != LOAI_CCCD:
        result.so_cccd = ""
    if loai and result.loai and result.loai != loai:
        result.canh_bao.append(f"Bạn chọn \"{loai}\" nhưng ảnh có vẻ là \"{result.loai}\".")
    return result
