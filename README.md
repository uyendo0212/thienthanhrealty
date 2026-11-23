# Phần mềm quản lý lưu trú — nhập khách từ ảnh CCCD

Tải ảnh căn cước công dân lên → phần mềm tự đọc **Họ tên, Ngày sinh, Giới tính, Số CCCD, Địa chỉ**,
bạn chọn **Ngày lưu trú** (mặc định hôm nay), kiểm tra lại rồi bấm **Lưu** → dữ liệu được ghi vào file Excel bạn chỉ định.

## Cách đọc thẻ
1. **Quét mã QR trên thẻ** (ưu tiên): miễn phí, không cần Internet, chính xác 100% khi quét được.
   Chụp mặt có mã QR, rõ nét, đủ sáng.
2. **AI đọc chữ** (dự phòng): khi ảnh không quét được QR, phần mềm gửi ảnh cho Claude để đọc.
   Cần API key của Anthropic (https://console.anthropic.com) — mất phí theo lượt dùng.
   Có thể tắt trong phần Cài đặt.

## Cài đặt (Windows)
1. Cài Python 3.10+ tại https://www.python.org/downloads/ (tích chọn **Add Python to PATH**).
2. Tải thư mục này về máy, nhấp đúp **`chay_phan_mem.bat`**.
   Lần đầu sẽ tự cài thư viện (vài phút). Trình duyệt sẽ mở ở http://localhost:8501.

macOS / Linux: chạy `./chay_phan_mem.sh`.

Nếu muốn dùng AI, đặt biến môi trường `ANTHROPIC_API_KEY`, hoặc dán key vào ô trong phần Cài đặt của phần mềm
(key nhập trong ô chỉ dùng cho lần chạy đó, không được lưu vào file).

## Chức năng
- **Nhập 1 khách**: tải ảnh mặt trước/mặt sau hoặc chụp bằng camera, sửa lại nếu cần, lưu vào Excel.
- **Nhập nhiều khách**: tải nhiều ảnh cùng lúc (mỗi ảnh 1 người), sửa trong bảng, lưu tất cả.
- **Danh sách**: xem, tìm kiếm khách đã nhập, tải file Excel.
- Cảnh báo khi trùng khách (cùng số CCCD và cùng ngày đến).

## File Excel
- Mặc định: `du_lieu/so_luu_tru.xlsx` (tự tạo). Đổi đường dẫn và tên sheet trong phần **Cài đặt**, rồi bấm **Lưu cài đặt**.
- Nếu dùng **file mẫu có sẵn** của bạn, phần mềm tự tìm dòng tiêu đề (trong 15 dòng đầu) và khớp cột theo tên,
  ví dụ: "Họ tên khách", "Năm sinh", "Số giấy tờ", "Địa chỉ thường trú", "Ngày lưu trú", "Phòng"...
  Cột nào cần ghi mà file chưa có sẽ được thêm vào cuối.
- Hãy **đóng file Excel** trước khi bấm Lưu (Excel đang mở sẽ khóa file).

## Bảo mật
Dữ liệu khách là thông tin cá nhân. Thư mục `du_lieu/` và các file `.xlsx` đã được loại khỏi Git để không bị đưa lên GitHub.
