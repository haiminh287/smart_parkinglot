### 3.3.4. Mockup giao diện và thiết kế xử lý các trang chính

Phần này trình bày 8 giao diện trọng yếu của hệ thống ParkSmart. Mỗi giao diện được thể hiện theo trình tự **(1) Mockup wireframe** thuộc giai đoạn thiết kế (low-fidelity wireframe — chỉ thể hiện cấu trúc bố cục, không phối màu/icon), **(2) Ảnh thực tế** đã được triển khai trên môi trường vận hành, và **(3) Bảng thiết kế xử lý** liệt kê các sự kiện chính cùng điều kiện kích hoạt và ý nghĩa nghiệp vụ tương ứng.

#### 1. Trang Index (Landing Page)

Trang chủ đóng vai trò điểm vào của hệ thống sau khi người dùng đăng nhập, tự động điều hướng dựa trên vai trò: tài khoản quản trị được chuyển sang trang quản trị, người dùng thường được hiển thị bảng điều khiển cá nhân.

![Wireframe trang Index](./wireframes/01-index.png)

_Hình 3.6a: Mockup wireframe trang chủ ParkSmart (giai đoạn thiết kế)_

![Giao diện thực tế trang Index](./screenshots/01-index.png)

_Hình 3.6b: Giao diện thực tế trang chủ sau khi triển khai_

**Bảng 3.4: Thiết kế xử lý giao diện Index (Trang chủ định tuyến)**

| STT | Tên xử lý           | Điều kiện gọi thực hiện                       | Ý nghĩa thực hiện                                                                                  |
| --- | ------------------- | --------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| 1   | Load_Page_Init      | Khi giao diện trang chủ được mở               | Đọc thông tin người dùng đang đăng nhập, chờ hệ thống xác minh xong mới quyết định hiển thị gì.    |
| 2   | AuthState_Change    | Khi thông tin xác thực người dùng thay đổi    | Nếu là quản trị viên thì chuyển sang trang quản trị; nếu là người dùng thường thì giữ tại trang chủ. |
| 3   | Loading_Render      | Khi đang chờ xác thực                         | Hiển thị màn hình chờ để người dùng biết hệ thống đang kiểm tra phiên đăng nhập.                  |
| 4   | UserDashboard_Mount | Khi xác thực xong và là người dùng thường     | Hiển thị bảng điều khiển cá nhân với các thông tin liên quan đến người dùng.                       |

#### 2. Trang User Dashboard

Trang Dashboard cá nhân hiển thị tóm tắt tình trạng đậu xe hiện tại, thống kê nhanh số lượng booking sắp tới và xe đã lưu, cùng các phím tắt đến các tác vụ chính như đặt chỗ mới, xem bản đồ và báo sự cố.

![Wireframe trang User Dashboard](./wireframes/02-user-dashboard.png)

_Hình 3.7a: Mockup wireframe trang Dashboard người dùng_

![Giao diện thực tế trang User Dashboard](./screenshots/02-user-dashboard.png)

_Hình 3.7b: Giao diện thực tế trang Dashboard sau khi triển khai_

**Bảng 3.5: Thiết kế xử lý giao diện User Dashboard**

| STT | Tên xử lý       | Điều kiện gọi thực hiện                                      | Ý nghĩa thực hiện                                                                                                                  |
| --- | --------------- | ------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Load_Page_Init  | Khi giao diện Dashboard được mở                              | Lấy thông tin xe đang đậu, danh sách booking sắp tới, thông báo chưa đọc và số lượng xe đã lưu để hiển thị tổng quan cho người dùng. |
| 2   | XemCamera_Click | Người dùng nhấn nút "Xem camera" trên thẻ xe đang đậu         | Mở trang camera giám sát đúng khu vực mà xe đang đậu để người dùng xem trực tiếp.                                                  |
| 3   | BaoSuCo_Click   | Người dùng nhấn nút "Báo sự cố"                              | Chuyển sang trang báo cáo sự cố khẩn cấp để người dùng nhập thông tin và gửi cho quản lý bãi.                                     |
| 4   | DatChoMoi_Click | Người dùng nhấn nút "Đặt chỗ ngay" hoặc "Đặt chỗ mới"        | Mở giao diện đặt chỗ để người dùng bắt đầu chọn bãi, xe, vị trí và thời gian.                                                       |
| 5   | XemBanDo_Click  | Người dùng nhấn nút "Xem bản đồ"                             | Mở trang bản đồ để xem sơ đồ bãi xe và đường đi tới slot đã đặt.                                                                   |
| 6   | LichSu_Click    | Người dùng nhấn vào thẻ thống kê "Sắp tới"                   | Mở trang lịch sử đặt chỗ để xem chi tiết các booking sắp tới và đã hoàn thành.                                                     |

#### 3. Trang Booking (Đặt chỗ)

Trang đặt chỗ triển khai luồng wizard 5 bước theo trình tự chọn bãi, chọn xe, chọn vị trí, chọn thời gian và thanh toán. Panel "Chi tiết đơn hàng" cập nhật giá tiền theo thời gian thực mỗi khi người dùng thay đổi lựa chọn.

![Wireframe trang Booking](./wireframes/03-booking.png)

_Hình 3.8a: Mockup wireframe trang Booking — wizard 5 bước_

![Giao diện thực tế trang Booking](./screenshots/03-booking.png)

_Hình 3.8b: Giao diện thực tế trang Booking sau khi triển khai_

**Bảng 3.6: Thiết kế xử lý giao diện Booking (Đặt chỗ)**

| STT | Tên xử lý           | Điều kiện gọi thực hiện                                                | Ý nghĩa thực hiện                                                                                                                                |
| --- | ------------------- | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | Load_Page_Init      | Khi giao diện Booking được mở                                          | Lấy danh sách bãi đỗ và danh sách xe đã lưu của người dùng, tự động chọn sẵn xe mặc định nếu có để rút ngắn thao tác.                            |
| 2   | ParkingLot_Change   | Khi người dùng chọn một bãi đỗ                                          | Lấy danh sách tầng và vùng đỗ của bãi vừa chọn để hiển thị ở các bước tiếp theo.                                                                  |
| 3   | Zone_Change         | Khi người dùng chọn một vùng đỗ                                         | Lấy danh sách ô đỗ trong vùng đó và đăng ký nhận cập nhật trạng thái slot theo thời gian thực để biết slot nào vừa bị giữ chỗ.                  |
| 4   | SlotRealtime_Change | Khi slot đang chọn vừa bị người khác giữ chỗ                            | Tự động bỏ chọn slot đó và hiển thị thông báo "Vị trí không còn trống" để người dùng chọn ô khác.                                                |
| 5   | LoaiXe_Change       | Người dùng nhấn nút "Ô tô" hoặc "Xe máy"                                | Cập nhật loại xe và đặt lại các trường tầng, vùng, slot, xe đã chọn để tránh đặt nhầm vị trí của loại xe khác.                                  |
| 6   | XeDaLuu_Click       | Người dùng nhấn vào một xe trong danh sách "Xe đã sử dụng gần đây"     | Tự động điền biển số và loại xe đã lưu vào form, đồng thời đặt lại vị trí để chọn lại theo loại xe đó.                                          |
| 7   | TiepTuc_Click       | Người dùng nhấn nút "Tiếp tục" tại các bước 1-4                        | Kiểm tra dữ liệu ở bước hiện tại đã hợp lệ chưa, nếu hợp lệ thì chuyển sang bước kế tiếp.                                                        |
| 8   | DatCho_Submit       | Người dùng nhấn "Thanh toán ngay" hoặc "Xác nhận đặt chỗ" tại bước 5  | Gửi thông tin đặt chỗ về hệ thống. Nếu chọn thanh toán online thì chuyển sang trang thanh toán; nếu trả tại cổng thì hiển thị mã QR để check-in. |

#### 4. Trang Map (Bản đồ bãi xe)

Trang bản đồ hiển thị sơ đồ bãi xe theo từng tầng và vẽ đường đi từ cổng vào tới slot đã đặt, hỗ trợ chạy hoạt cảnh xe di chuyển mô phỏng để người dùng dễ hình dung lộ trình.

![Wireframe trang Map](./wireframes/04-map.png)

_Hình 3.9a: Mockup wireframe trang Map — bản đồ bãi xe + chỉ đường_

![Giao diện thực tế trang Map](./screenshots/04-map.png)

_Hình 3.9b: Giao diện thực tế trang Map sau khi triển khai_

**Bảng 3.7: Thiết kế xử lý giao diện Map (Bản đồ và chỉ đường)**

| STT | Tên xử lý             | Điều kiện gọi thực hiện                              | Ý nghĩa thực hiện                                                                                                          |
| --- | --------------------- | ---------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| 1   | Load_Page_Init        | Khi giao diện Bản đồ được mở                         | Lấy thông tin booking đang hoạt động của người dùng; nếu chưa có thì hiển thị bản đồ minh hoạ với dữ liệu mẫu.            |
| 2   | CurrentParking_Change | Khi có booking đang hoạt động                        | Lấy toàn bộ vùng đỗ của bãi tương ứng để dựng sơ đồ tầng phù hợp.                                                          |
| 3   | Zones_Change          | Khi danh sách vùng đỗ đã được lấy về                  | Lấy chi tiết các ô đỗ trong từng vùng để dựng layout bản đồ.                                                                |
| 4   | Floor_Change          | Người dùng đổi tầng trên ô chọn tầng                  | Tính lại các vùng và ô đỗ thuộc tầng vừa chọn, cập nhật bản đồ hiển thị.                                                   |
| 5   | ChiDuong_Click        | Người dùng nhấn nút "Chỉ đường"                       | Bật hoặc tắt panel hướng dẫn đường đi cùng đường vẽ trên bản đồ.                                                            |
| 6   | StartNavigation_Click | Người dùng nhấn nút "Bắt đầu" trong panel chỉ đường   | Khởi động hoạt cảnh xe di chuyển dọc theo đường đi từ cổng vào tới slot đã đặt trong khoảng 8 giây.                        |
| 7   | StopNavigation_Click  | Người dùng nhấn nút "Dừng" trong banner chỉ đường     | Dừng hoạt cảnh đang chạy và quay lại trạng thái xem bản đồ tĩnh.                                                            |
| 8   | DatChoNgay_Click      | Người dùng nhấn nút "Đặt chỗ ngay" trên banner demo   | Chuyển sang trang đặt chỗ để người dùng tạo booking thật thay cho dữ liệu mẫu đang xem.                                    |

#### 5. Trang History (Lịch sử & Thống kê)

Trang lịch sử hiển thị danh sách các booking đã đặt, biểu đồ chi tiêu theo tháng, đồng thời cho phép người dùng huỷ booking, xem mã QR, chuyển sang thanh toán hoặc xem đường đi tới slot trực tiếp ngay trên từng dòng booking.

![Wireframe trang History](./wireframes/05-history.png)

_Hình 3.10a: Mockup wireframe trang Lịch sử đặt chỗ_

![Giao diện thực tế trang History](./screenshots/05-history.png)

_Hình 3.10b: Giao diện thực tế trang History sau khi triển khai_

**Bảng 3.8: Thiết kế xử lý giao diện History (Lịch sử đặt chỗ)**

| STT | Tên xử lý           | Điều kiện gọi thực hiện                                                                  | Ý nghĩa thực hiện                                                                                              |
| --- | ------------------- | ---------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| 1   | Load_Page_Init      | Khi giao diện Lịch sử được mở                                                            | Lấy danh sách booking của người dùng và thống kê tổng chi tiêu theo tháng để vẽ biểu đồ.                       |
| 2   | FilterStatus_Change | Khi người dùng đổi bộ lọc trạng thái (Tất cả / Đang đậu / Đã xác nhận / Hoàn thành)     | Lấy lại danh sách booking theo trạng thái mới và cập nhật bảng hiển thị.                                       |
| 3   | Search_Change       | Người dùng nhập vào ô "Tìm theo biển số"                                                | Lọc danh sách booking đang hiển thị theo biển số xe người dùng nhập.                                           |
| 4   | XemQR_Click         | Người dùng nhấn nút "Xem QR" trên một booking                                            | Mở cửa sổ hiển thị mã QR của booking đó để người dùng quét tại cổng vào.                                       |
| 5   | Huy_Click           | Người dùng nhấn nút "Huỷ" trên booking đang chờ thanh toán hoặc đã xác nhận             | Mở hộp thoại xác nhận huỷ booking và chờ người dùng xác nhận hoặc bỏ qua.                                      |
| 6   | XacNhanHuy_Click    | Người dùng nhấn "Xác nhận huỷ" trong hộp thoại                                          | Gửi yêu cầu huỷ booking về hệ thống, hiển thị thông báo kết quả và cập nhật lại danh sách hiển thị.            |
| 7   | ThanhToan_Click     | Người dùng nhấn nút "Thanh toán" trên booking chưa thanh toán                            | Chuyển sang trang thanh toán để người dùng hoàn tất việc thanh toán cho booking đang dở dang.                  |
| 8   | ChiDuong_Click      | Người dùng nhấn nút "Chỉ đường" trên booking đã check-in hoặc đã xác nhận                | Mở trang bản đồ và hiển thị đường đi tới slot đã đặt của booking đó.                                           |

#### 6. Trang Support (Chatbot AI)

Trang hỗ trợ cung cấp giao diện trò chuyện với trợ lý ảo thông minh tích hợp RAG, cho phép người dùng đặt câu hỏi bằng tiếng Việt tự nhiên về chính sách, quy định, giờ mở cửa và các thao tác trong hệ thống. Bot trả lời kèm gợi ý nhanh, nút xác nhận cho các tác vụ quan trọng và panel đánh giá sau hội thoại.

![Wireframe trang Support](./wireframes/06-support-chatbot.png)

_Hình 3.11a: Mockup wireframe trang Chatbot AI_

![Giao diện thực tế trang Support](./screenshots/06-support-chatbot.png)

_Hình 3.11b: Giao diện thực tế trang Chatbot AI sau khi triển khai_

**Bảng 3.9: Thiết kế xử lý giao diện Support (Chatbot AI)**

| STT | Tên xử lý         | Điều kiện gọi thực hiện                                              | Ý nghĩa thực hiện                                                                                                              |
| --- | ----------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| 1   | Load_Page_Init    | Khi giao diện Chatbot được mở                                        | Lấy lịch sử trò chuyện cũ và hiển thị tin nhắn chào mừng để người dùng tiếp tục cuộc hội thoại.                                |
| 2   | Messages_Change   | Khi có tin nhắn mới được gửi hoặc nhận                               | Tự động cuộn xuống cuối khung chat để người dùng luôn thấy tin nhắn mới nhất.                                                  |
| 3   | Send_Click        | Người dùng nhấn nút Gửi hoặc bấm Enter trong ô nhập                   | Hiển thị tin nhắn của người dùng, gửi nội dung lên hệ thống và hiển thị câu trả lời của trợ lý kèm các gợi ý liên quan.        |
| 4   | QuickAction_Click | Người dùng nhấn vào một trong các phím tắt gợi ý                     | Gửi luôn câu hỏi mẫu tương ứng để trợ lý xử lý mà không cần người dùng tự gõ.                                                  |
| 5   | Suggestion_Click  | Người dùng nhấn vào chip gợi ý hiển thị bên dưới câu trả lời của bot | Tiếp tục cuộc hội thoại theo nhánh gợi ý mà bot đề xuất.                                                                       |
| 6   | XacNhan_Click     | Khi bot yêu cầu xác nhận và người dùng nhấn "Xác nhận"               | Gửi xác nhận để bot thực thi tác vụ đang chờ (ví dụ tạo booking hoặc huỷ booking).                                             |
| 7   | HuyBo_Click       | Khi bot yêu cầu xác nhận và người dùng nhấn "Huỷ bỏ"                 | Huỷ tác vụ đang chờ và quay về trạng thái hội thoại bình thường.                                                                |
| 8   | DanhGia_Submit    | Người dùng nhấn "Gửi đánh giá" trong panel phản hồi                  | Gửi đánh giá và bình luận của người dùng về cuộc hội thoại, hiển thị thông báo cảm ơn và đóng panel.                          |

#### 7. Trang Payment (Thanh toán)

Trang thanh toán hiển thị mã QR chuyển khoản ngân hàng kèm thông tin số tài khoản, đồng hồ đếm ngược 15 phút và trạng thái thanh toán. Hệ thống tự động kiểm tra trạng thái thanh toán định kỳ và chuyển sang trang lịch sử ngay khi xác nhận thành công.

![Wireframe trang Payment](./wireframes/07-payment.png)

_Hình 3.12a: Mockup wireframe trang Thanh toán_

![Giao diện thực tế trang Payment](./screenshots/07-payment.png)

_Hình 3.12b: Giao diện thực tế trang Payment sau khi triển khai_

**Bảng 3.10: Thiết kế xử lý giao diện Payment (Thanh toán đặt chỗ)**

| STT | Tên xử lý           | Điều kiện gọi thực hiện                                              | Ý nghĩa thực hiện                                                                                                                                |
| --- | ------------------- | -------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | Load_Page_Init      | Khi giao diện Thanh toán được mở với mã booking đính kèm             | Lấy chi tiết booking cần thanh toán; nếu không tìm thấy thì hiển thị thông báo lỗi và quay về trang lịch sử.                                     |
| 2   | Booking_Change      | Khi đã có thông tin booking                                          | Bắt đầu đếm ngược 15 phút kể từ thời điểm tạo booking; khi hết giờ thì đánh dấu booking đã hết hạn thanh toán.                                  |
| 3   | PaymentPolling_Init | Khi trang sẵn sàng và booking chưa được xác nhận thanh toán          | Định kỳ kiểm tra trạng thái thanh toán; khi nhận được xác nhận thành công thì hiển thị thông báo và chuyển sang trang lịch sử.                  |
| 4   | Copy_Click          | Người dùng nhấn nút sao chép số tài khoản hoặc mã đặt chỗ            | Sao chép nội dung vào bộ nhớ tạm và hiển thị thông báo "Đã sao chép" để người dùng biết.                                                          |
| 5   | DaThanhToan_Click   | Người dùng nhấn nút "Tôi đã thanh toán"                              | Chuyển sang trạng thái đang xác minh và rút ngắn chu kỳ kiểm tra để xác nhận thanh toán nhanh hơn.                                              |
| 6   | Back_Click          | Người dùng nhấn nút mũi tên quay lại ở đầu trang                     | Quay về trang trước đó (thường là trang đặt chỗ hoặc lịch sử).                                                                                   |
| 7   | XemLichSu_Click     | Người dùng nhấn "Xem lịch sử đặt chỗ" sau khi thanh toán thành công | Mở trang lịch sử đặt chỗ để người dùng xem booking vừa hoàn tất.                                                                                  |

#### 8. Trang Admin Dashboard

Trang quản trị tổng quan hiển thị các chỉ số quan trọng (số người dùng, doanh thu, tỉ lệ lấp đầy bãi), tỉ lệ chiếm chỗ thời gian thực từ camera AI, danh sách booking gần nhất và các phím tắt đến các trang quản trị con.

![Wireframe trang Admin Dashboard](./wireframes/08-admin-dashboard.png)

_Hình 3.13a: Mockup wireframe trang Admin Dashboard_

![Giao diện thực tế trang Admin Dashboard](./screenshots/08-admin-dashboard.png)

_Hình 3.13b: Giao diện thực tế trang Admin Dashboard sau khi triển khai_

**Bảng 3.11: Thiết kế xử lý giao diện Admin Dashboard**

| STT | Tên xử lý             | Điều kiện gọi thực hiện                                    | Ý nghĩa thực hiện                                                                                                                |
| --- | --------------------- | ---------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Load_Page_Init        | Khi giao diện Quản trị được mở                              | Lấy đồng thời các chỉ số tổng quan và danh sách hoạt động gần đây để hiển thị bảng điều khiển cho quản trị viên.                |
| 2   | NguoiDung_Click       | Quản trị viên nhấn nút "Người dùng" trong khối Truy cập nhanh | Mở trang quản lý tài khoản người dùng để xem, chỉnh sửa và phân quyền.                                                          |
| 3   | Camera_Click          | Quản trị viên nhấn nút "Camera"                              | Mở trang cấu hình danh sách camera của hệ thống.                                                                                 |
| 4   | GiamSatLive_Click     | Quản trị viên nhấn nút "Giám sát live"                       | Mở trang xem trực tiếp luồng video từ tất cả camera trong bãi.                                                                  |
| 5   | BaoCao_Click          | Quản trị viên nhấn nút "Báo cáo"                             | Mở trang biểu đồ doanh thu và tỉ lệ lấp đầy theo thời gian.                                                                      |
| 6   | OccupancyBar_Render   | Khi đã lấy được tỉ lệ lấp đầy bãi                            | Hiển thị thanh tiến trình với màu thay đổi theo ngưỡng (xanh khi còn nhiều chỗ, vàng khi gần đầy, đỏ khi quá tải) để cảnh báo trực quan. |
| 7   | AILiveOccupancy_Mount | Sau khi đã lấy xong các chỉ số tổng quan                     | Hiển thị thẻ thông tin tỉ lệ chiếm chỗ thời gian thực, tự động cập nhật theo dữ liệu từ camera AI.                              |
| 8   | RecentActivity_Render | Khi đã lấy được danh sách hoạt động gần đây                  | Hiển thị tối đa 6 hoạt động mới nhất kèm biểu tượng tương ứng với từng loại sự kiện (check-in, check-out, đặt chỗ, thanh toán, sự cố). |

