#### UC04 — Đặt chỗ online (Online Booking)

| Tiêu đề            | Nội dung                                                                                                                                                                                                                                                                                                                                                              |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Tên Use Case**   | Đặt chỗ gửi xe online                                                                                                                                                                                                                                                                                                                                                 |
| **Mô tả vắn tắt**  | Người dùng đặt chỗ gửi xe trực tuyến qua giao diện đặt chỗ. Hệ thống kiểm tra hợp lệ rồi xác nhận đặt chỗ. Nếu chọn thanh toán online thì hiển thị mã VietQR để thanh toán; nếu chọn trả tại cổng thì sinh QR code để check-in tại cổng.                                                                                                                              |
| **Actor chính**    | User                                                                                                                                                                                                                                                                                                                                                                  |
| **Actor phụ**      | VietQR (khi thanh toán online)                                                                                                                                                                                                                                                                                                                                        |
| **Tiền điều kiện** | User đã đăng nhập, đã có phương tiện hợp lệ, bãi xe còn chỗ trống.                                                                                                                                                                                                                                                                                                    |
| **Hậu điều kiện**  | Booking được lưu, slot được giữ chỗ, người dùng nhận thông báo đặt chỗ thành công và được chuyển sang trang thanh toán hoặc lịch sử đặt chỗ.                                                                                                                                                                                                                          |

**Luồng hoạt động chính:**

| Bước   | Hoạt động                                                                                                                       |
| ------ | ------------------------------------------------------------------------------------------------------------------------------- |
| **B1** | User mở chức năng đặt chỗ và chọn bãi đỗ xe.                                                                                    |
| **B2** | User chọn loại xe, gói thời gian, ngày bắt đầu, tầng và vùng đỗ.                                                                |
| **B3** | User chọn một slot còn trống trên sơ đồ.                                                                                        |
| **B4** | User chọn phương thức thanh toán (online qua VietQR hoặc trả tại cổng) rồi nhấn xác nhận đặt chỗ.                              |
| **B5** | Hệ thống kiểm tra dữ liệu hợp lệ và lưu booking, giữ chỗ slot tương ứng.                                                        |
| **B6** | Nếu chọn thanh toán online: hệ thống hiển thị mã VietQR và chờ user thanh toán; sau khi thanh toán thành công thì xác nhận booking. |
| **B7** | Nếu chọn trả tại cổng: hệ thống sinh QR code để check-in tại cổng.                                                              |
| **B8** | Hệ thống gửi thông báo đặt chỗ thành công và chuyển sang trang lịch sử đặt chỗ.                                                |

**Luồng thay thế:**

| Mã     | Điều kiện                                                | Xử lý                                                                                                                              |
| ------ | -------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------- |
| **A1** | Tầng đã chọn không còn slot trống cho loại xe của user  | Hệ thống đề xuất tầng hoặc vùng khác còn chỗ, giữ nguyên các thông tin user đã chọn để không phải nhập lại.                       |
| **A2** | Slot user định chọn vừa bị người khác giữ chỗ           | Hệ thống thông báo slot không còn khả dụng, yêu cầu chọn slot khác và cập nhật lại sơ đồ.                                          |

**Luồng ngoại lệ:**

| Mã     | Điều kiện                                                       | Xử lý                                                                              |
| ------ | --------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| **E1** | Dữ liệu đầu vào không hợp lệ (sai ngày, thiếu thông tin)        | Từ chối yêu cầu, hiển thị lỗi cụ thể trên từng trường để user chỉnh lại.          |
| **E2** | User chưa đăng nhập hoặc phiên hết hạn                          | Chuyển về trang đăng nhập, yêu cầu đăng nhập lại rồi mới cho đặt chỗ tiếp.        |
| **E3** | Thanh toán VietQR thất bại hoặc quá thời gian chờ               | Hủy phiên thanh toán, thông báo cho user và cho phép đặt lại hoặc đổi phương thức. |
| **E4** | Lỗi hệ thống hoặc mất kết nối mạng                              | Thông báo lỗi thân thiện, cho phép user thử lại mà không mất dữ liệu đã nhập.     |

---

#### UC05 — Xem map hướng dẫn đỗ xe

| Tiêu đề            | Nội dung                                                                                                                                                          |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Tên Use Case**   | Xem map hướng dẫn đỗ xe                                                                                                                                            |
| **Mô tả vắn tắt**  | Người dùng xem bản đồ hướng dẫn đường đi từ cổng vào tới slot đã đặt sau khi đã check-in vào bãi.                                                                 |
| **Actor chính**    | User                                                                                                                                                              |
| **Actor phụ**      | —                                                                                                                                                                 |
| **Tiền điều kiện** | User đã đăng nhập, đã đặt chỗ trước và đã check-in vào bãi.                                                                                                       |
| **Hậu điều kiện**  | Hiển thị bản đồ hướng dẫn cùng đường đi tới slot đã đặt.                                                                                                          |

**Luồng hoạt động chính:**

| Bước   | Hoạt động                                                                |
| ------ | ------------------------------------------------------------------------ |
| **B1** | User mở trang lịch sử đặt chỗ.                                           |
| **B2** | User chọn xem bản đồ của booking đã đặt.                                 |
| **B3** | Hệ thống hiển thị bản đồ tầng tương ứng kèm vị trí slot đã đặt.         |
| **B4** | Hệ thống vẽ đường đi từ cổng vào tới slot và cho phép user xem hoạt cảnh chỉ đường. |

**Luồng thay thế:**

| Mã     | Điều kiện                                          | Xử lý                                                                            |
| ------ | -------------------------------------------------- | -------------------------------------------------------------------------------- |
| **A1** | Bãi xe chưa có dữ liệu sơ đồ chi tiết             | Hiển thị thông báo "Khu vực này chưa hỗ trợ chỉ đường" và cho phép quay lại.    |

**Luồng ngoại lệ:**

| Mã     | Điều kiện                | Xử lý                                                                       |
| ------ | ------------------------ | --------------------------------------------------------------------------- |
| **E1** | User chưa check-in vào bãi | Hệ thống thông báo "Bạn cần check-in trước" và yêu cầu user đến cổng. |

---

#### UC06 — Check-in bằng QR Code

| Tiêu đề            | Nội dung                                                                                                                                                                                                                                  |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Tên Use Case**   | Check-in bằng QR Code tại cổng                                                                                                                                                                                                            |
| **Mô tả vắn tắt**  | Người dùng đến cổng gửi xe và xuất trình QR code đã đặt chỗ. Hệ thống quét QR và dùng AI nhận diện biển số. Nếu chọn trả tại cổng thì hiển thị mã VietQR thanh toán. Khi xác minh thành công thì barrier tự động mở.                       |
| **Actor chính**    | User                                                                                                                                                                                                                                      |
| **Actor phụ**      | IoT (ESP32, barrier), Camera, VietQR (khi thanh toán tại cổng)                                                                                                                                                                            |
| **Tiền điều kiện** | User đã đặt chỗ online, QR code còn hiệu lực trong khoảng thời gian đã đặt.                                                                                                                                                                |
| **Hậu điều kiện**  | Barrier mở cửa, booking chuyển sang trạng thái đã check-in.                                                                                                                                                                                |

**Luồng hoạt động chính:**

| Bước   | Hoạt động                                                                                                            |
| ------ | -------------------------------------------------------------------------------------------------------------------- |
| **B1** | User đến cổng và xuất trình QR code.                                                                                 |
| **B2** | Camera quét QR và chụp biển số xe gửi đến hệ thống.                                                                  |
| **B3** | Hệ thống xử lý và kiểm tra QR cùng biển số có khớp với booking hay không.                                            |
| **B4** | Nếu phương thức thanh toán là trả tại cổng: hệ thống hiển thị mã VietQR để user quét và thanh toán.                  |
| **B5** | Hệ thống gửi tín hiệu mở barrier; sau ít giây barrier tự động đóng.                                                  |

**Luồng thay thế:**

| Mã     | Điều kiện                                          | Xử lý                                                                            |
| ------ | -------------------------------------------------- | -------------------------------------------------------------------------------- |
| **A1** | User đã thanh toán online từ trước                 | Bỏ qua bước B4, đi thẳng từ B3 sang B5 mở barrier.                              |
| **A2** | Camera đọc thấy biển số mờ hoặc bị che             | Hệ thống cảnh báo và không cho vào, yêu cầu user đỗ thẳng để chụp lại.          |

**Luồng ngoại lệ:**

| Mã     | Điều kiện                                   | Xử lý                                                                  |
| ------ | ------------------------------------------- | ---------------------------------------------------------------------- |
| **E1** | QR code lỗi hoặc hết hạn                    | Hệ thống báo lỗi và không mở barrier.                                  |
| **E2** | Biển số không khớp với booking              | Hệ thống báo lỗi và giữ barrier đóng.                                  |
| **E3** | Thanh toán tại cổng thất bại                | Hệ thống thông báo và không mở barrier cho đến khi thanh toán xong.   |

