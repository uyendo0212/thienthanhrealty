"""Đọc thông tin từ ảnh Căn cước công dân (CCCD) / Thẻ căn cước Việt Nam.

Hai cách đọc, theo thứ tự ưu tiên:
1. Quét mã QR in trên thẻ (offline, miễn phí, chính xác tuyệt đối khi quét được).
   Nội dung QR có dạng:
   SoCCCD|SoCMNDcu|HoTen|NgaySinh(ddmmyyyy)|GioiTinh|DiaChi|NgayCap(ddmmyyyy)
2. Nếu không quét được QR (ảnh mờ, mặt sau...), gửi ảnh cho Claude (AI) để
   đọc chữ trên thẻ. Cần biến môi trường ANTHROPIC_API_KEY.
"""

from __future__ import annotations

import base64
import io
import os
import re
from dataclasses import dataclass, field

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


# Loại khách / giấy tờ và các trường bắt buộc tương ứng
LOAI_CCCD = "CCCD"
LOAI_BLX = "Bằng lái xe"
LOAI_TRE_EM = "Trẻ em"
LOAI_LIST = [LOAI_CCCD, LOAI_BLX, LOAI_TRE_EM]

TEN_TRUONG = {"ho_ten": "Họ tên", "ngay_sinh": "Ngày sinh", "so_cccd": "Số CCCD",
              "dia_chi": "Địa chỉ", "ngay_den": "Ngày lưu trú"}
BAT_BUOC = {
    LOAI_CCCD: ["ho_ten", "ngay_sinh", "so_cccd", "dia_chi", "ngay_den"],
    LOAI_BLX: ["ho_ten", "ngay_sinh", "dia_chi", "ngay_den"],
    LOAI_TRE_EM: ["ho_ten", "ngay_sinh", "ngay_den"],
}


def thieu_truong(loai: str, rec: dict) -> list[str]:
    """Trả về tên các trường bắt buộc còn trống theo loại khách."""
    return [TEN_TRUONG[k] for k in BAT_BUOC.get(loai, BAT_BUOC[LOAI_CCCD])
            if rec.get(k) in (None, "") or (isinstance(rec.get(k), str) and not rec[k].strip())]


@dataclass
class GuestInfo:
    ho_ten: str = ""
    ngay_sinh: str = ""  # dd/mm/yyyy
    gioi_tinh: str = ""
    so_cccd: str = ""
    dia_chi: str = ""
    loai: str = ""  # LOAI_CCCD / LOAI_BLX (do phần mềm nhận diện)
    nguon: str = ""  # "QR" hoặc "AI"
    canh_bao: list[str] = field(default_factory=list)

    def merge(self, other: "GuestInfo") -> "GuestInfo":
        """Điền các trường còn trống bằng dữ liệu từ `other`."""
        for f in ("ho_ten", "ngay_sinh", "gioi_tinh", "so_cccd", "dia_chi", "loai"):
            if not getattr(self, f) and getattr(other, f):
                setattr(self, f, getattr(other, f))
        if other.nguon and other.nguon not in self.nguon:
            self.nguon = "+".join(x for x in (self.nguon, other.nguon) if x)
        self.canh_bao.extend(other.canh_bao)
        return self


# --------------------------------------------------------------------------- #
# Tiện ích
# --------------------------------------------------------------------------- #
def _fmt_date(raw: str) -> str:
    """'01011990' -> '01/01/1990'; giữ nguyên nếu đã có dấu phân cách."""
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
# 1. Quét QR
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
        loai=LOAI_CCCD,
        nguon="QR",
    )


def _qr_candidates(img: Image.Image):
    """Sinh ra các biến thể ảnh (thu phóng, xám, tăng tương phản) để dễ quét."""
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
            arr = np.array(cand)
            try:
                ok, decoded, _, _ = cv2.QRCodeDetector().detectAndDecodeMulti(arr)
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
# 2. Đọc bằng Claude (AI)
# --------------------------------------------------------------------------- #
MODEL = os.environ.get("CCCD_MODEL", "claude-opus-5-5")

_PROMPT = """Đây là ảnh chụp giấy tờ tùy thân Việt Nam: căn cước công dân / thẻ căn cước, HOẶC giấy phép lái xe (bằng lái xe).
Ảnh có thể là mặt trước, mặt sau, hoặc cả hai. Hãy đọc chính xác, giữ nguyên dấu tiếng Việt:
- loai_giay_to: "CCCD" nếu là căn cước / căn cước công dân; "Bằng lái xe" nếu là giấy phép lái xe; "Khác" nếu không phải hai loại trên.
- ho_ten: Họ và tên (viết như trên giấy tờ)
- ngay_sinh: Ngày sinh, định dạng dd/mm/yyyy
- gioi_tinh: Giới tính (Nam/Nữ), để trống nếu giấy tờ không ghi
- so_cccd: CHỈ với CCCD: số định danh / số CCCD (12 chữ số). Với bằng lái xe để trống (không lấy số giấy phép lái xe).
- dia_chi: CCCD cũ: "Nơi thường trú"; thẻ căn cước mới: "Nơi cư trú"; bằng lái xe: "Nơi cư trú" / "Address".
  KHÔNG dùng "Quê quán" / "Nơi đăng ký khai sinh".
Trường nào không có trong ảnh hoặc không đọc được thì để chuỗi rỗng. Không đoán."""


def _get_schema():
    from typing import Literal

    from pydantic import BaseModel

    class CCCDFields(BaseModel):
        loai_giay_to: Literal["CCCD", "Bằng lái xe", "Khác"]
        ho_ten: str
        ngay_sinh: str
        gioi_tinh: str
        so_cccd: str
        dia_chi: str

    return CCCDFields


def _to_jpeg_b64(img: Image.Image, max_side: int = 1800) -> str:
    img = img.copy()
    img.thumbnail((max_side, max_side))
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=90)
    return base64.standard_b64encode(buf.getvalue()).decode()


def ai_available() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


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
    info = GuestInfo(
        ho_ten=d.ho_ten.strip(),
        ngay_sinh=_fmt_date(d.ngay_sinh),
        gioi_tinh=d.gioi_tinh.strip(),
        so_cccd=re.sub(r"\D", "", d.so_cccd),
        dia_chi=d.dia_chi.strip(),
        loai={"CCCD": LOAI_CCCD, "Bằng lái xe": LOAI_BLX}.get(d.loai_giay_to, ""),
        nguon="AI",
    )
    if info.loai == LOAI_BLX:
        info.so_cccd = ""
    if d.loai_giay_to == "Khác":
        info.canh_bao.append("Ảnh có vẻ không phải CCCD hoặc bằng lái xe — hãy kiểm tra lại.")
    if info.so_cccd and len(info.so_cccd) != 12:
        info.canh_bao.append(f"Số CCCD đọc được có {len(info.so_cccd)} chữ số (thường là 12) — hãy kiểm tra lại.")
    return info


# --------------------------------------------------------------------------- #
# Hàm chính
# --------------------------------------------------------------------------- #
def extract(images_bytes: list[bytes], use_ai: bool = True, loai: str = "") -> GuestInfo:
    """Nhận 1 hoặc nhiều ảnh (mặt trước / mặt sau) của cùng một giấy tờ.

    `loai` là loại giấy tờ người dùng đã chọn (để trống = tự nhận diện).
    Với bằng lái xe, bỏ qua bước quét QR (QR trên bằng lái không chứa thông tin cá nhân).
    """
    images = [load_image(b) for b in images_bytes]

    result = GuestInfo()
    if loai != LOAI_BLX:
        for im in images:
            qr = read_qr(im)
            if qr:
                result.merge(qr)
                break

    can = BAT_BUOC[LOAI_BLX] if loai == LOAI_BLX else BAT_BUOC[LOAI_CCCD]
    missing = any(not getattr(result, k) for k in can if k != "ngay_den")
    if missing:
        if use_ai and ai_available():
            try:
                result.merge(read_with_ai(images))
            except Exception as e:  # lỗi mạng, sai key...
                result.canh_bao.append(f"Lỗi khi gọi AI: {e}")
        elif not result.nguon:
            result.canh_bao.append(
                "Không quét được mã QR. Bằng lái xe cần AI để đọc — hãy cài ANTHROPIC_API_KEY, hoặc nhập tay."
                if loai == LOAI_BLX else
                "Không quét được mã QR. Hãy chụp lại rõ mã QR, hoặc cài ANTHROPIC_API_KEY để AI đọc chữ trên thẻ."
            )
    if loai == LOAI_BLX:
        result.so_cccd = ""
    if loai and result.loai and result.loai != loai:
        result.canh_bao.append(f"Bạn chọn \"{loai}\" nhưng ảnh có vẻ là \"{result.loai}\".")
    return result
