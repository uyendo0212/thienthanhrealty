"""Phần mềm quản lý lưu trú — nhập khách từ ảnh giấy tờ vào Excel.

Khách Việt Nam và khách nước ngoài được lưu vào 2 file (hoặc 2 sheet) riêng,
tự động phân loại theo quốc tịch đọc được từ hộ chiếu / thị thực.

Chạy:  streamlit run app.py
"""

from __future__ import annotations

import json
import os
from datetime import date

import pandas as pd
import streamlit as st

import cccd_reader as L
import excel_store as E

BASE = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE, "config.json")
DEFAULT_CONFIG = {
    "excel_vn": os.path.join(BASE, "du_lieu", "khach_viet_nam.xlsx"),
    "sheet_vn": "Khach Viet Nam",
    "excel_nn": os.path.join(BASE, "du_lieu", "khach_nuoc_ngoai.xlsx"),
    "sheet_nn": "Khach nuoc ngoai",
    "use_ai": True,
}
TEN_NHOM = {"vn": "khách Việt Nam", "nn": "khách nước ngoài"}


def load_config() -> dict:
    cfg = dict(DEFAULT_CONFIG)
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            old = json.load(f)
        # tương thích cài đặt cũ (1 file)
        if "excel_path" in old and "excel_vn" not in old:
            old["excel_vn"], old["sheet_vn"] = old.pop("excel_path"), old.pop("sheet", cfg["sheet_vn"])
        cfg.update(old)
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
    st.markdown("**🇻🇳 Khách Việt Nam**")
    excel_vn = st.text_input("File Excel", cfg["excel_vn"], key="excel_vn",
                             help="Ví dụ: D:\\LuuTru\\khach_viet_nam.xlsx. Chưa có thì tự tạo. "
                                  "Nếu là file mẫu có sẵn, phần mềm tự nhận diện cột theo tiêu đề.")
    sheet_vn = st.text_input("Tên sheet", cfg["sheet_vn"], key="sheet_vn")
    st.markdown("**🌏 Khách nước ngoài**")
    excel_nn = st.text_input("File Excel", cfg["excel_nn"], key="excel_nn")
    sheet_nn = st.text_input("Tên sheet", cfg["sheet_nn"], key="sheet_nn")
    st.caption("Muốn dùng **chung 1 file, 2 tab**: nhập cùng một đường dẫn file, khác tên sheet.")
    if os.path.abspath(excel_vn) == os.path.abspath(excel_nn) and sheet_vn == sheet_nn:
        st.error("Hai nhóm khách đang trùng cả file lẫn sheet — hãy đặt tên sheet khác nhau.")
    st.divider()
    use_ai = st.checkbox("Dùng AI đọc giấy tờ (bằng lái, hộ chiếu, thị thực, CCCD không quét được QR)",
                         cfg["use_ai"])
    if use_ai and not L.ai_available():
        key = st.text_input("ANTHROPIC_API_KEY", type="password",
                            help="Cần để đọc bằng lái xe, hộ chiếu, thị thực. CCCD có mã QR thì không cần.")
        if key:
            os.environ["ANTHROPIC_API_KEY"] = key.strip()
    if st.button("💾 Lưu cài đặt"):
        cfg.update(excel_vn=excel_vn, sheet_vn=sheet_vn, excel_nn=excel_nn, sheet_nn=sheet_nn, use_ai=use_ai)
        save_config(cfg)
        st.success("Đã lưu cài đặt")
    st.caption("Mẹo: với CCCD, chụp **mặt có mã QR** rõ nét — đọc ngay, không cần Internet. "
               "Với hộ chiếu, chụp rõ **trang thông tin có 2 dòng mã MRZ** ở dưới cùng.")

TARGET = {"vn": (excel_vn, sheet_vn), "nn": (excel_nn, sheet_nn)}


def nhom_cua(rec: dict) -> str:
    return "nn" if L.la_nguoi_nuoc_ngoai(rec.get("quoc_tich", "")) else "vn"


def show_warnings(info: L.GuestInfo) -> None:
    for w in info.canh_bao:
        st.warning(w)
    if info.nguon:
        msg = f"Nguồn dữ liệu: {info.nguon}"
        if info.quoc_tich:
            nhom = "nn" if L.la_nguoi_nuoc_ngoai(info.quoc_tich) else "vn"
            msg += f"  ·  Quốc tịch: **{info.quoc_tich}** → lưu vào file {TEN_NHOM[nhom]}"
        st.caption(msg + "  ·  Hãy kiểm tra lại trước khi lưu.")


def save_record(rec: dict) -> bool:
    """Kiểm tra và lưu 1 khách. Trả về True nếu đã lưu (hoặc đã có sẵn)."""
    loai = rec.get("loai_giay_to") or L.LOAI_CCCD
    ten = rec.get("ho_ten") or "Khách"
    thieu = L.thieu_truong(loai, rec)
    if thieu:
        st.error(f"{ten} ({loai}): còn thiếu {', '.join(thieu)}.")
        return False
    nd, ndi = rec.get("ngay_den"), rec.get("ngay_di")
    if isinstance(nd, date) and isinstance(ndi, date) and ndi < nd:
        st.error(f"{ten}: ngày đi ({ndi:%d/%m/%Y}) trước ngày đến ({nd:%d/%m/%Y}).")
        return False
    nhom = nhom_cua(rec)
    path, sheet = TARGET[nhom]
    dup = E.find_duplicate(path, sheet, rec, nhom)
    if dup:
        st.warning(f"{ten} đã có ở dòng {dup} (file {TEN_NHOM[nhom]}) với cùng ngày đến — bỏ qua.")
        return True
    row = E.append_guest(path, rec, sheet, nhom)
    so_dem = f", {(ndi - nd).days} đêm" if isinstance(nd, date) and isinstance(ndi, date) else ""
    st.success(f"✅ Đã lưu {ten} ({loai}{so_dem}) vào dòng {row} — file {TEN_NHOM[nhom]} "
               f"({os.path.basename(path)} / {sheet})")
    return True


def _s(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return str(v).strip()


def _d(v):
    """Chuyển giá trị ô bảng thành date (hoặc None)."""
    if v is None or v is pd.NaT or (isinstance(v, float) and pd.isna(v)):
        return None
    if isinstance(v, pd.Timestamp):
        return v.date()
    v = E._to_date(v)
    return v if isinstance(v, date) else None


st.title("🏠 Quản lý lưu trú — nhập khách từ ảnh giấy tờ")
tab1, tab2, tab3 = st.tabs(["👤 Nhập 1 khách", "👥 Nhập nhiều khách", "📋 Danh sách & sửa ngày"])

# ----------------------------------------------------------------- Tab 1
with tab1:
    loai = st.radio("Loại khách / giấy tờ", L.LOAI_LIST, horizontal=True, key="loai",
                    format_func=L.LOAI_HIEN_THI.get)
    st.caption("Bắt buộc: " + ", ".join(L.TEN_TRUONG[k] for k in L.BAT_BUOC[loai]))
    if st.session_state.get("info_loai") != loai:  # đổi loại thì bỏ kết quả đọc cũ
        st.session_state.pop("info", None)

    c1, c2 = st.columns([1, 1])
    with c1:
        if loai == L.LOAI_TRE_EM:
            st.info("Trẻ em không cần giấy tờ: chỉ nhập **Họ tên**, **Ngày sinh** và **Ngày đến**. "
                    "Có thể ghi tên bố/mẹ đi cùng vào ô Ghi chú. "
                    "Trẻ em người nước ngoài: chọn loại **Hộ chiếu / Thị thực**.")
        else:
            nhan = {L.LOAI_CCCD: "Ảnh CCCD (mặt trước và/hoặc mặt sau)",
                    L.LOAI_BLX: "Ảnh bằng lái xe (mặt trước và/hoặc mặt sau)",
                    L.LOAI_HC: "Ảnh trang thông tin hộ chiếu và/hoặc trang thị thực (có thể tải nhiều ảnh)"}[loai]
            files = st.file_uploader(nhan, type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True,
                                     key=f"single_upload_{loai}")
            cam = st.camera_input("Hoặc chụp trực tiếp bằng camera", key="cam") if st.toggle("Dùng camera") else None
            imgs = [f.getvalue() for f in (files or [])] + ([cam.getvalue()] if cam else [])
            for b in imgs:
                st.image(b, width="stretch")
            if imgs and st.button("🔍 Đọc thông tin", type="primary"):
                with st.spinner("Đang đọc giấy tờ..."):
                    st.session_state.info = L.extract(imgs, use_ai=use_ai, loai=loai)
                    st.session_state.info_loai = loai

    with c2:
        info: L.GuestInfo = st.session_state.get("info") or L.GuestInfo()
        if "info" in st.session_state:
            show_warnings(info)
        with st.form(f"guest_form_{loai}", clear_on_submit=False):
            ho_ten = st.text_input("Họ và tên *", info.ho_ten)
            a, b = st.columns(2)
            ngay_sinh = a.text_input("Ngày sinh (dd/mm/yyyy) *", info.ngay_sinh)
            gioi_tinh = b.text_input("Giới tính", info.gioi_tinh)
            so_cccd = dia_chi = so_ho_chieu = so_thi_thuc = han_thi_thuc = ""
            quoc_tich = "Việt Nam"
            if loai == L.LOAI_CCCD:
                so_cccd = st.text_input("Số CCCD *", info.so_cccd)
            if loai in (L.LOAI_CCCD, L.LOAI_BLX):
                dia_chi = st.text_area("Địa chỉ (nơi thường trú / cư trú) *", info.dia_chi, height=80)
            if loai == L.LOAI_HC:
                a, b = st.columns(2)
                quoc_tich = a.text_input("Quốc tịch *", info.quoc_tich,
                                         help="Khác \"Việt Nam\" → lưu vào file khách nước ngoài.")
                so_ho_chieu = b.text_input("Số hộ chiếu *", info.so_ho_chieu)
                a, b = st.columns(2)
                so_thi_thuc = a.text_input("Số thị thực", info.so_thi_thuc)
                han_thi_thuc = b.text_input("Thị thực có giá trị đến (dd/mm/yyyy)", info.han_thi_thuc)
            a, b = st.columns(2)
            ngay_den = a.date_input("Ngày đến *", date.today(), format="DD/MM/YYYY",
                                    help="Chọn đúng ngày khách đến (có thể chọn ngày trước hoặc sau hôm nay).")
            ngay_di = b.date_input("Ngày đi (nếu biết)", None, format="DD/MM/YYYY",
                                   help="Có thể để trống và cập nhật sau ở tab Danh sách & sửa ngày.")
            a, b = st.columns(2)
            phong = a.text_input("Phòng")
            ghi_chu = b.text_input("Ghi chú")
            if st.form_submit_button("💾 Lưu vào Excel", type="primary"):
                ok = save_record(dict(
                    loai_giay_to=loai, ho_ten=ho_ten.strip(), ngay_sinh=L._fmt_date(ngay_sinh),
                    gioi_tinh=gioi_tinh.strip(), so_cccd=so_cccd.strip(), dia_chi=dia_chi.strip(),
                    quoc_tich=quoc_tich.strip(), so_ho_chieu=so_ho_chieu.strip().upper(),
                    so_thi_thuc=so_thi_thuc.strip().upper(), han_thi_thuc=L._fmt_date(han_thi_thuc),
                    ngay_den=ngay_den, ngay_di=ngay_di, phong=phong.strip(), ghi_chu=ghi_chu.strip()))
                if ok:
                    st.session_state.pop("info", None)

# ----------------------------------------------------------------- Tab 2
BATCH_COLS = ["loai_giay_to", "ho_ten", "ngay_sinh", "gioi_tinh", "quoc_tich", "so_cccd", "so_ho_chieu",
              "so_thi_thuc", "han_thi_thuc", "dia_chi", "ngay_den", "ngay_di", "phong", "nguon", "anh", "canh_bao"]

with tab2:
    st.write("Tải lên nhiều ảnh — **mỗi ảnh là 1 khách** (CCCD, bằng lái, hộ chiếu; phần mềm tự nhận diện loại "
             "giấy tờ và quốc tịch). Trẻ em: bấm ➕ dưới bảng để thêm dòng, chọn loại **Trẻ em** và nhập tay.")
    many = st.file_uploader("Ảnh giấy tờ", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True,
                            key="multi_upload")
    a, b, c = st.columns(3)
    nd = a.date_input("Ngày đến (mặc định cho cả nhóm)", date.today(), format="DD/MM/YYYY", key="nd_all")
    ndi = b.date_input("Ngày đi (mặc định cho cả nhóm)", None, format="DD/MM/YYYY", key="ndi_all")
    ph = c.text_input("Phòng (mặc định)", key="ph_all")
    if many and st.button("🔍 Đọc tất cả", type="primary"):
        rows, prog = [], st.progress(0.0)
        for i, f in enumerate(many):
            inf = L.extract([f.getvalue()], use_ai=use_ai)
            rows.append(dict(loai_giay_to=inf.loai or L.LOAI_CCCD, ho_ten=inf.ho_ten, ngay_sinh=inf.ngay_sinh,
                             gioi_tinh=inf.gioi_tinh, quoc_tich=inf.quoc_tich or "Việt Nam",
                             so_cccd=inf.so_cccd, so_ho_chieu=inf.so_ho_chieu, so_thi_thuc=inf.so_thi_thuc,
                             han_thi_thuc=inf.han_thi_thuc, dia_chi=inf.dia_chi, ngay_den=nd, ngay_di=ndi,
                             phong=ph, nguon=inf.nguon or "—", anh=f.name, canh_bao="; ".join(inf.canh_bao)))
            prog.progress((i + 1) / len(many))
        st.session_state.batch = pd.DataFrame(rows, columns=BATCH_COLS)
    if "batch" not in st.session_state and st.button("➕ Nhập tay (không có ảnh, ví dụ trẻ em)"):
        st.session_state.batch = pd.DataFrame(
            [dict(loai_giay_to=L.LOAI_TRE_EM, quoc_tich="Việt Nam", ngay_den=nd, ngay_di=ndi, phong=ph,
                  nguon="Nhập tay")], columns=BATCH_COLS)

    if "batch" in st.session_state:
        st.caption("Bấm vào ô để sửa. **Ngày đến / Ngày đi** sửa riêng được cho từng khách. "
                   "Quốc tịch khác \"Việt Nam\" sẽ lưu vào file khách nước ngoài.")
        edited = st.data_editor(
            st.session_state.batch, width="stretch", num_rows="dynamic", hide_index=True,
            column_config={
                "loai_giay_to": st.column_config.SelectboxColumn("Loại", options=L.LOAI_LIST,
                                                                 default=L.LOAI_TRE_EM, required=True),
                "ho_ten": "Họ và tên", "ngay_sinh": "Ngày sinh", "gioi_tinh": "Giới tính",
                "quoc_tich": st.column_config.TextColumn("Quốc tịch", default="Việt Nam"),
                "so_cccd": "Số CCCD", "so_ho_chieu": "Số hộ chiếu", "so_thi_thuc": "Số thị thực",
                "han_thi_thuc": "Thị thực đến", "dia_chi": st.column_config.TextColumn("Địa chỉ", width="large"),
                "ngay_den": st.column_config.DateColumn("Ngày đến", format="DD/MM/YYYY", default=nd),
                "ngay_di": st.column_config.DateColumn("Ngày đi", format="DD/MM/YYYY"),
                "phong": st.column_config.TextColumn("Phòng", default=ph or None),
                "nguon": "Nguồn", "anh": "Ảnh", "canh_bao": "Cảnh báo"},
            disabled=["nguon", "anh", "canh_bao"],
        )
        if st.button("💾 Lưu tất cả vào Excel", type="primary"):
            con_lai = []
            for _, r in edited.iterrows():
                lo = _s(r.get("loai_giay_to")) or L.LOAI_CCCD
                rec = dict(loai_giay_to=lo, ho_ten=_s(r.get("ho_ten")),
                           ngay_sinh=L._fmt_date(_s(r.get("ngay_sinh"))), gioi_tinh=_s(r.get("gioi_tinh")),
                           quoc_tich=_s(r.get("quoc_tich")) if lo == L.LOAI_HC else "Việt Nam",
                           so_cccd=_s(r.get("so_cccd")) if lo == L.LOAI_CCCD else "",
                           so_ho_chieu=_s(r.get("so_ho_chieu")).upper(), so_thi_thuc=_s(r.get("so_thi_thuc")).upper(),
                           han_thi_thuc=L._fmt_date(_s(r.get("han_thi_thuc"))),
                           dia_chi=_s(r.get("dia_chi")) if lo in (L.LOAI_CCCD, L.LOAI_BLX) else "",
                           ngay_den=_d(r.get("ngay_den")), ngay_di=_d(r.get("ngay_di")), phong=_s(r.get("phong")))
                if not rec["ho_ten"] and not rec["ngay_sinh"] and not rec["so_cccd"] and not rec["so_ho_chieu"]:
                    continue  # dòng trống
                if not save_record(rec):
                    con_lai.append(r)
            if con_lai:  # giữ lại các dòng lỗi để sửa tiếp
                st.session_state.batch = pd.DataFrame(con_lai, columns=BATCH_COLS).reset_index(drop=True)
                st.info("Các dòng chưa lưu được vẫn còn trong bảng — sửa rồi bấm Lưu lại.")
            else:
                del st.session_state.batch

# ----------------------------------------------------------------- Tab 3
with tab3:
    nhom = st.radio("Xem danh sách", ["vn", "nn"], horizontal=True, key="ds_nhom",
                    format_func=lambda x: {"vn": "🇻🇳 Khách Việt Nam", "nn": "🌏 Khách nước ngoài"}[x])
    path, sheet = TARGET[nhom]
    headers, rows, row_nums, cols = E.read_all(path, sheet, nhom)
    st.write(f"File: `{path}` — sheet `{sheet}` — **{len(rows)}** khách")
    if rows:
        # Tên cột hiển thị (không trùng); cột Ngày đến / Ngày đi để dạng ngày cho phép sửa
        names, seen = [], set()
        for i, h in enumerate(headers):
            n = str(h).strip() or f"Cột {i + 1}"
            while n in seen:
                n += " "
            seen.add(n)
            names.append(n)
        date_cols = {k: names[cols[k] - 1] for k in ("ngay_den", "ngay_di") if k in cols}
        data = []
        for vals in rows:
            rec = {}
            for i, v in enumerate(vals):
                if names[i] in date_cols.values():
                    rec[names[i]] = _d(v)
                else:
                    rec[names[i]] = v.strftime("%d/%m/%Y") if isinstance(v, date) else ("" if v is None else str(v))
            data.append(rec)
        df = pd.DataFrame(data, index=row_nums, columns=names)
        for k in ("ngay_den", "ngay_di"):  # file chưa có cột này -> thêm cột để nhập
            if k not in date_cols:
                date_cols[k] = E.COLUMNS[k][0]
                df[date_cols[k]] = None
        for n in date_cols.values():
            df[n] = pd.to_datetime(df[n], errors="coerce").dt.date

        q = st.text_input("🔎 Tìm theo tên / số giấy tờ / phòng", key=f"q_{nhom}")
        if q:
            mask = df.astype(str).apply(lambda col: col.str.contains(q, case=False, na=False)).any(axis=1)
            df = df[mask]
        st.caption("✏️ Sửa trực tiếp cột **Ngày đến / Ngày đi** theo ngày khách thực tế lưu trú "
                   "(gia hạn, trả phòng sớm...), rồi bấm **Lưu thay đổi ngày**.")
        edited = st.data_editor(
            df, width="stretch", hide_index=True, key=f"editor_{nhom}",
            disabled=[n for n in df.columns if n not in date_cols.values()],
            column_config={n: st.column_config.DateColumn(n, format="DD/MM/YYYY") for n in date_cols.values()},
        )
        a, b = st.columns([1, 3])
        if a.button("💾 Lưu thay đổi ngày", type="primary", key=f"save_dates_{nhom}"):
            changes, loi = {}, []
            for row in edited.index:
                new = {k: _d(edited.at[row, n]) for k, n in date_cols.items()}
                old = {k: _d(df.at[row, n]) for k, n in date_cols.items()}
                if new == old:
                    continue
                if new["ngay_den"] and new["ngay_di"] and new["ngay_di"] < new["ngay_den"]:
                    loi.append(row)
                    continue
                changes[row] = {k: v for k, v in new.items() if v != old[k]}
            for r in loi:
                st.error(f"Dòng {r}: ngày đi trước ngày đến — chưa lưu.")
            if changes:
                E.update_dates(path, sheet, changes, nhom)
                st.success(f"✅ Đã cập nhật ngày cho {len(changes)} khách.")
            elif not loi:
                st.info("Không có thay đổi nào.")
        with open(path, "rb") as f:
            b.download_button("⬇️ Tải file Excel", f.read(), file_name=os.path.basename(path), key=f"dl_{nhom}")
