"""Phần mềm quản lý lưu trú — nhập khách từ ảnh CCCD vào Excel.

Chạy:  streamlit run app.py
"""

from __future__ import annotations

import json
import os
from datetime import date

import pandas as pd
import streamlit as st

import cccd_reader
import excel_store

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE, "config.json")
DEFAULT_CONFIG = {
    "excel_path": os.path.join(BASE, "du_lieu", "so_luu_tru.xlsx"),
    "sheet": "Khach luu tru",
    "use_ai": True,
}


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            cfg.update(json.load(f))
    except (OSError, ValueError):
        pass
    return cfg


def save_config(cfg: dict) -> None:
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


st.set_page_config(page_title="Quản lý lưu trú", page_icon="🏠", layout="wide")
cfg = load_config()

# ----------------------------------------------------------------- Sidebar
with st.sidebar:
    st.header("⚙️ Cài đặt")
    excel_path = st.text_input(
        "Đường dẫn file Excel",
        cfg["excel_path"],
        help="Ví dụ: D:\\LuuTru\\so_khach.xlsx. Nếu file chưa có sẽ tự tạo. "
        "Nếu là file mẫu có sẵn, phần mềm tự nhận diện các cột theo tiêu đề.",
    )
    sheet = st.text_input("Tên sheet", cfg["sheet"])
    use_ai = st.checkbox("Dùng AI đọc chữ khi không quét được QR", cfg["use_ai"])
    if use_ai and not cccd_reader.ai_available():
        key = st.text_input("ANTHROPIC_API_KEY", type="password",
                            help="Chỉ cần khi muốn AI đọc ảnh không có/không quét được mã QR.")
        if key:
            os.environ["ANTHROPIC_API_KEY"] = key.strip()
    if st.button("💾 Lưu cài đặt"):
        cfg.update(excel_path=excel_path, sheet=sheet, use_ai=use_ai)
        save_config(cfg)
        st.success("Đã lưu cài đặt")
    st.caption("Mẹo: chụp **mặt có mã QR** rõ nét, đủ sáng — phần mềm đọc QR ngay, không cần Internet.")


def show_warnings(info: cccd_reader.GuestInfo) -> None:
    for w in info.canh_bao:
        st.warning(w)
    if info.nguon:
        st.caption(f"Nguồn dữ liệu: {info.nguon}  ·  Hãy kiểm tra lại trước khi lưu.")


def save_record(rec: dict) -> None:
    dup = excel_store.find_duplicate(excel_path, sheet, rec["so_cccd"], rec["ngay_den"])
    if dup:
        st.warning(f"Khách {rec['ho_ten']} ({rec['so_cccd']}) đã có ở dòng {dup} với cùng ngày đến — bỏ qua.")
        return
    row = excel_store.append_guest(excel_path, rec, sheet)
    st.success(f"✅ Đã lưu {rec['ho_ten']} vào dòng {row} của {os.path.basename(excel_path)}")


st.title("🏠 Quản lý lưu trú — nhập khách từ ảnh CCCD")
tab1, tab2, tab3 = st.tabs(["👤 Nhập 1 khách", "👥 Nhập nhiều khách", "📋 Danh sách"])

# ----------------------------------------------------------------- Tab 1
with tab1:
    c1, c2 = st.columns([1, 1])
    with c1:
        files = st.file_uploader(
            "Ảnh CCCD (mặt trước và/hoặc mặt sau của cùng 1 người)",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            key="single_upload",
        )
        cam = st.camera_input("Hoặc chụp trực tiếp bằng camera", key="cam") if st.toggle("Dùng camera") else None
        imgs = [f.getvalue() for f in (files or [])] + ([cam.getvalue()] if cam else [])
        for b in imgs:
            st.image(b, width="stretch")
        if imgs and st.button("🔍 Đọc thông tin", type="primary"):
            with st.spinner("Đang đọc thẻ..."):
                st.session_state.info = cccd_reader.extract(imgs, use_ai=use_ai)

    with c2:
        info: cccd_reader.GuestInfo = st.session_state.get("info") or cccd_reader.GuestInfo()
        if "info" in st.session_state:
            show_warnings(info)
        with st.form("guest_form", clear_on_submit=False):
            ho_ten = st.text_input("Họ và tên", info.ho_ten)
            a, b = st.columns(2)
            ngay_sinh = a.text_input("Ngày sinh (dd/mm/yyyy)", info.ngay_sinh)
            gioi_tinh = b.text_input("Giới tính", info.gioi_tinh)
            so_cccd = st.text_input("Số CCCD", info.so_cccd)
            dia_chi = st.text_area("Địa chỉ (nơi thường trú / cư trú)", info.dia_chi, height=80)
            a, b = st.columns(2)
            ngay_den = a.date_input("Ngày lưu trú (ngày đến)", date.today(), format="DD/MM/YYYY")
            ngay_di = b.date_input("Ngày đi (nếu biết)", None, format="DD/MM/YYYY")
            a, b = st.columns(2)
            phong = a.text_input("Phòng")
            ghi_chu = b.text_input("Ghi chú")
            if st.form_submit_button("💾 Lưu vào Excel", type="primary"):
                if not ho_ten or not so_cccd:
                    st.error("Cần có ít nhất Họ tên và Số CCCD.")
                else:
                    save_record(dict(ho_ten=ho_ten.strip(), ngay_sinh=ngay_sinh.strip(), gioi_tinh=gioi_tinh.strip(),
                                     so_cccd=so_cccd.strip(), dia_chi=dia_chi.strip(), ngay_den=ngay_den,
                                     ngay_di=ngay_di, phong=phong, ghi_chu=ghi_chu))
                    st.session_state.pop("info", None)

# ----------------------------------------------------------------- Tab 2
with tab2:
    st.write("Tải lên nhiều ảnh — **mỗi ảnh là 1 khách** (nên chụp mặt có mã QR).")
    many = st.file_uploader("Ảnh CCCD", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True,
                            key="multi_upload")
    a, b, c = st.columns(3)
    nd = a.date_input("Ngày đến chung", date.today(), format="DD/MM/YYYY", key="nd_all")
    ndi = b.date_input("Ngày đi chung", None, format="DD/MM/YYYY", key="ndi_all")
    ph = c.text_input("Phòng chung", key="ph_all")
    if many and st.button("🔍 Đọc tất cả", type="primary"):
        rows, prog = [], st.progress(0.0)
        for i, f in enumerate(many):
            inf = cccd_reader.extract([f.getvalue()], use_ai=use_ai)
            rows.append(dict(ho_ten=inf.ho_ten, ngay_sinh=inf.ngay_sinh, gioi_tinh=inf.gioi_tinh,
                             so_cccd=inf.so_cccd, dia_chi=inf.dia_chi, nguon=inf.nguon or "—",
                             anh=f.name, canh_bao="; ".join(inf.canh_bao)))
            prog.progress((i + 1) / len(many))
        st.session_state.batch = pd.DataFrame(rows)

    if "batch" in st.session_state:
        st.caption("Bấm vào ô để sửa nếu đọc sai.")
        edited = st.data_editor(
            st.session_state.batch, width="stretch", num_rows="dynamic",
            column_config={"ho_ten": "Họ và tên", "ngay_sinh": "Ngày sinh", "gioi_tinh": "Giới tính",
                           "so_cccd": "Số CCCD", "dia_chi": st.column_config.TextColumn("Địa chỉ", width="large"),
                           "nguon": "Nguồn", "anh": "Ảnh", "canh_bao": "Cảnh báo"},
            disabled=["nguon", "anh", "canh_bao"],
        )
        if st.button("💾 Lưu tất cả vào Excel", type="primary"):
            for _, r in edited.iterrows():
                if not str(r.get("ho_ten") or "").strip() or not str(r.get("so_cccd") or "").strip():
                    st.error(f"Bỏ qua ảnh {r.get('anh')}: thiếu họ tên hoặc số CCCD.")
                    continue
                save_record(dict(ho_ten=str(r["ho_ten"]).strip(), ngay_sinh=str(r["ngay_sinh"] or ""),
                                 gioi_tinh=str(r["gioi_tinh"] or ""), so_cccd=str(r["so_cccd"]).strip(),
                                 dia_chi=str(r["dia_chi"] or ""), ngay_den=nd, ngay_di=ndi, phong=ph))
            del st.session_state.batch

# ----------------------------------------------------------------- Tab 3
with tab3:
    headers, rows = excel_store.read_all(excel_path, sheet)
    st.write(f"File: `{excel_path}` — **{len(rows)}** khách")
    if rows:
        df = pd.DataFrame(rows, columns=[str(h) or f"Cột {i+1}" for i, h in enumerate(headers)])
        q = st.text_input("🔎 Tìm theo tên / số CCCD")
        if q:
            mask = df.astype(str).apply(lambda col: col.str.contains(q, case=False, na=False)).any(axis=1)
            df = df[mask]
        st.dataframe(df, width="stretch", hide_index=True)
        with open(excel_path, "rb") as f:
            st.download_button("⬇️ Tải file Excel", f.read(), file_name=os.path.basename(excel_path))
