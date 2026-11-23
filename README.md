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

## Cài đặt và chạy

### MacBook (khuyên dùng)
1. Cài Python **3.12 hoặc 3.13** tại https://www.python.org/downloads/macos/ (bản *macOS 64-bit universal2 installer*).
2. Giải nén thư mục phần mềm, **nhấp đúp `Chay phan mem (Mac).command`**.
   - Nếu macOS báo *"không thể mở vì từ nhà phát triển không xác định"*: **chuột phải (hoặc Control + bấm) → Mở → Mở**. Chỉ cần làm 1 lần.
   - Nếu máy hỏi *"cho phép Python nhận kết nối mạng?"*: chọn **Cho phép** (để điện thoại kết nối được).
3. Lần đầu tự cài thư viện (vài phút), sau đó trình duyệt tự mở phần mềm. **Giữ cửa sổ Terminal mở** khi đang dùng.

### Windows
1. Cài Python 3.12 hoặc 3.13 tại https://www.python.org/downloads/ (tích chọn **Add Python to PATH**).
2. Nhấp đúp **`chay_phan_mem.bat`**.

## Dùng trên điện thoại 📱
Phần mềm chạy trên máy tính, điện thoại chỉ cần trình duyệt — **không phải cài gì**.
1. Trên máy tính, ở cột bên trái mục **📱 Dùng trên điện thoại**: đặt **mật khẩu** (để khách dùng chung Wi-Fi không xem được dữ liệu).
2. Điện thoại kết nối **cùng Wi-Fi** với máy tính, mở Camera quét **mã QR** hiện trên máy tính (hoặc gõ địa chỉ `http://...:8501`).
3. Đăng nhập bằng mật khẩu. Mẹo: trên iPhone bấm **Chia sẻ → Thêm vào MH chính** để có biểu tượng như ứng dụng.
4. Chụp giấy tờ: bấm **Upload → Chụp ảnh**.

Lưu ý: máy tính phải **đang bật, không ngủ, và đang chạy phần mềm** (khi chạy, phần mềm tự giữ cho Mac không ngủ;
gập màn hình MacBook thì máy vẫn ngủ). File Excel lưu trên máy tính.

## Cài API key (để AI đọc bằng lái, hộ chiếu, thị thực)
Tạo key tại https://console.anthropic.com → API Keys. Dán vào ô **ANTHROPIC_API_KEY** ở cột bên trái
(trên máy tính), giữ dấu tích **Ghi nhớ key trên máy này** để lần sau không phải nhập lại.

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
