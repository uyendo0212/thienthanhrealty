# Phần mềm quản lý lưu trú — nhập khách từ ảnh CCCD / bằng lái xe

Tải ảnh căn cước công dân lên → phần mềm tự đọc **Họ tên, Ngày sinh, Giới tính, Số CCCD, Địa chỉ**,
bạn chọn **Ngày lưu trú** (mặc định hôm nay), kiểm tra lại rồi bấm **Lưu** → dữ liệu được ghi vào file Excel bạn chỉ định.

## Loại khách và thông tin bắt buộc

| Loại khách | Thông tin bắt buộc | Cách nhập |
|---|---|---|
| 🪪 CCCD | Họ tên, Ngày sinh, Số CCCD, Địa chỉ, Ngày lưu trú | Tải ảnh CCCD (quét mã QR, hoặc AI đọc) |
| 🚗 Bằng lái xe | Họ tên, Ngày sinh, Địa chỉ, Ngày lưu trú | Tải ảnh bằng lái (AI đọc), hoặc nhập tay |
| 🧒 Trẻ em | Họ tên, Ngày sinh, Ngày lưu trú | Nhập tay, không cần ảnh |

Phần mềm không cho lưu khi còn thiếu thông tin bắt buộc. Cột **Loại giấy tờ** trong Excel ghi rõ khách thuộc loại nào.
Trùng khách được kiểm tra theo số CCCD; với trẻ em và khách dùng bằng lái xe thì kiểm tra theo họ tên + ngày sinh + ngày đến.

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
- **Nhập 1 khách**: chọn loại khách (CCCD / Bằng lái xe / Trẻ em), tải ảnh hoặc chụp bằng camera, sửa lại nếu cần, lưu vào Excel.
- **Nhập nhiều khách**: tải nhiều ảnh cùng lúc (mỗi ảnh 1 người, tự nhận diện CCCD hay bằng lái), thêm dòng trẻ em bằng tay, sửa trong bảng, lưu tất cả.
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
