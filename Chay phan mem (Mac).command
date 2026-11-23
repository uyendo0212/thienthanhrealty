#!/bin/bash
# Nhấp đúp file này để chạy phần mềm trên macOS.
cd "$(dirname "$0")" || exit 1
echo "=== Phần mềm quản lý lưu trú ==="

# 1. Tìm Python 3.11 trở lên (không dùng /usr/bin/python3 của Apple vì quá cũ)
PY=""
for c in /Library/Frameworks/Python.framework/Versions/3.1[1-9]/bin/python3 \
         /opt/homebrew/bin/python3 /usr/local/bin/python3 \
         "$(command -v python3.13)" "$(command -v python3.12)" "$(command -v python3.11)"; do
  if [ -n "$c" ] && [ -x "$c" ] && "$c" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
    PY="$c"; break
  fi
done
if [ -z "$PY" ]; then
  echo
  echo "Chưa có Python 3.11+ trên máy."
  echo "Trang tải Python sẽ mở ra: tải bản 'macOS 64-bit universal2 installer' (3.12 hoặc 3.13),"
  echo "cài xong thì nhấp đúp lại file này."
  open "https://www.python.org/downloads/macos/"
  read -r -p "Nhấn Enter để đóng..."
  exit 1
fi

# 2. Cài thư viện lần đầu (hoặc khi danh sách thư viện thay đổi)
if [ ! -x .venv/bin/python ]; then
  echo "Đang chuẩn bị lần đầu (vài phút)..."
  "$PY" -m venv .venv || { read -r -p "Lỗi tạo môi trường. Nhấn Enter để đóng..."; exit 1; }
fi
if ! cmp -s requirements.txt .venv_ok; then
  echo "Đang cài thư viện..."
  .venv/bin/python -m pip install --upgrade pip -q
  if .venv/bin/python -m pip install -r requirements.txt; then
    cp requirements.txt .venv_ok
  else
    read -r -p "Cài thư viện bị lỗi (kiểm tra kết nối mạng). Nhấn Enter để đóng..."; exit 1
  fi
fi

# 3. Chạy phần mềm, tự mở trình duyệt; caffeinate giữ máy không ngủ khi đang chạy
echo
echo "Phần mềm đang chạy. ĐỪNG đóng cửa sổ này khi đang dùng (kể cả dùng trên điện thoại)."
echo "Muốn tắt: đóng cửa sổ này hoặc nhấn Ctrl+C."
(sleep 4 && open "http://localhost:8501") &
exec caffeinate -i .venv/bin/python -m streamlit run app.py
