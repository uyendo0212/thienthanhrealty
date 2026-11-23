# Phần mềm quản lý lưu trú — nhập khách từ ảnh giấy tờ

Tải ảnh giấy tờ lên → phần mềm tự đọc thông tin khách, bạn kiểm tra lại rồi bấm **Lưu** →
dữ liệu được ghi vào Excel. **Khách Việt Nam** và **khách nước ngoài** được lưu riêng
(2 file, hoặc 2 tab trong cùng 1 file), tự động phân loại theo quốc tịch.

## Loại khách và thông tin bắt buộc

| Loại khách | Thông tin bắt buộc | Cách nhập | Lưu vào |
|---|---|---|---|
| 🪪 CCCD | Họ tên, Ngày sinh, Số CCCD, Địa chỉ, Ngày đến | Quét mã QR trên thẻ, hoặc AI đọc | File khách Việt Nam |
| 🚗 Bằng lái xe | Họ tên, Ngày sinh, Địa chỉ, Ngày đến | AI đọc ảnh, hoặc nhập tay | File khách Việt Nam |
| 🛂 Hộ chiếu / Thị thực | Họ tên, Ngày sinh, Quốc tịch, Số hộ chiếu, Ngày đến | AI đọc ảnh + giải mã MRZ, hoặc nhập tay | Theo quốc tịch: Việt Nam → file khách Việt Nam, còn lại → file khách nước ngoài |
| 🧒 Trẻ em | Họ tên, Ngày sinh, Ngày đến | Nhập tay, không cần ảnh | File khách Việt Nam |

- Phần mềm không cho lưu khi còn thiếu thông tin bắt buộc, hoặc khi ngày đi trước ngày đến.
- Trùng khách được kiểm tra theo số CCCD / số hộ chiếu (hoặc họ tên + ngày sinh) cùng ngày đến.

## Ngày đến / ngày đi
- Khi nhập: chọn ngày đến, ngày đi bất kỳ (không bắt buộc là hôm nay). Ngày đi có thể để trống.
- Nhập nhiều khách: đặt ngày chung cho cả nhóm, rồi sửa riêng từng khách ngay trong bảng.
- Khách đã lưu: vào tab **Danh sách & sửa ngày**, sửa trực tiếp cột Ngày đến / Ngày đi
  (gia hạn, trả phòng sớm...) rồi bấm **Lưu thay đổi ngày** — file Excel được cập nhật đúng dòng của khách.

## Cách đọc giấy tờ
1. **CCCD — quét mã QR** (ưu tiên): miễn phí, không cần Internet, chính xác khi quét được.
2. **AI (Claude) đọc ảnh**: dùng cho bằng lái xe, hộ chiếu, thị thực và CCCD không quét được QR.
   Cần API key của Anthropic (https://console.anthropic.com) — mất phí theo lượt dùng. Có thể tắt trong Cài đặt.
3. **Hộ chiếu / thị thực**: AI chép lại 2 dòng mã **MRZ** (dòng ký tự `P<KOR...` ở cuối trang), phần mềm tự
   giải mã và kiểm tra số kiểm tra (check digit) để xác nhận **quốc tịch**, số hộ chiếu, ngày sinh.
   Có thể tải cùng lúc trang hộ chiếu và trang thị thực của 1 người.

## Cài đặt (Windows)
1. Cài Python 3.10+ tại https://www.python.org/downloads/ (tích chọn **Add Python to PATH**).
2. Nhấp đúp **`chay_phan_mem.bat`**. Lần đầu sẽ tự cài thư viện (vài phút). Trình duyệt mở ở http://localhost:8501.

macOS / Linux: chạy `./chay_phan_mem.sh`.

Nếu muốn dùng AI, đặt biến môi trường `ANTHROPIC_API_KEY`, hoặc dán key vào ô trong phần Cài đặt
(key nhập trong ô chỉ dùng cho lần chạy đó, không được lưu vào file).

## File Excel
- Mặc định: `du_lieu/khach_viet_nam.xlsx` và `du_lieu/khach_nuoc_ngoai.xlsx` (tự tạo).
- Muốn **1 file, 2 tab**: trong Cài đặt nhập cùng một đường dẫn file cho cả hai nhóm, đặt tên sheet khác nhau
  (ví dụ "Khach Viet Nam" và "Khach nuoc ngoai"), rồi bấm **Lưu cài đặt**.
- File khách nước ngoài có các cột: Họ tên, Ngày sinh, Giới tính, Quốc tịch, Số hộ chiếu, Loại giấy tờ,
  Số thị thực, Thị thực có giá trị đến, Ngày đến, Ngày đi, Phòng, Ghi chú.
- Nếu dùng **file mẫu có sẵn**, phần mềm tự tìm dòng tiêu đề và khớp cột theo tên (ví dụ "Họ tên khách",
  "Số giấy tờ", "Quốc tịch", "Ngày lưu trú"...). Cột nào cần ghi mà file chưa có sẽ được thêm vào cuối.
- Hãy **đóng file Excel** trước khi bấm Lưu (Excel đang mở sẽ khóa file).

## Bảo mật
Dữ liệu khách là thông tin cá nhân. Thư mục `du_lieu/` và các file `.xlsx` đã được loại khỏi Git.
