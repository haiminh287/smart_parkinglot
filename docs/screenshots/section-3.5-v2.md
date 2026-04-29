## 3.5. Kết quả đạt được

Hệ thống ParkSmart đã triển khai đầy đủ và đưa vào vận hành các nhóm chức năng nghiệp vụ quan trọng. Phần này trình bày kết quả thực tế của 7 tính năng chính theo trình tự **(1) Ảnh giao diện thực tế**, **(2) Mô tả ngắn** về chức năng, và **(3) Ý nghĩa** của tính năng đó trong tổng thể hệ thống.

### 3.5.1. Đặt chỗ online (Online Booking)

![Giao diện đặt chỗ online](./screenshots/03-booking.png)

_Hình 3.14: Giao diện chức năng đặt chỗ online_

**Mô tả ngắn**: Người dùng đặt trước ô đỗ xe qua wizard 5 bước trên web (chọn bãi → chọn xe → chọn vị trí → thời gian → thanh toán). Trạng thái ô đỗ được cập nhật theo thời gian thực; sau khi đặt thành công, hệ thống sinh mã QR định danh dùng để check-in tại cổng và hỗ trợ hai phương thức thanh toán: trực tuyến qua VietQR hoặc trả tại cổng.

**Ý nghĩa**: Đây là tính năng cốt lõi mở ra hành trình sử dụng dịch vụ — người dùng có thể đảm bảo chỗ đậu trước khi đến bãi, tránh tình trạng đến nơi mới biết hết chỗ. Việc đặt chỗ online cũng giúp bãi xe quản lý nguồn lực hiệu quả hơn (dự báo lưu lượng, tránh quá tải) và là điều kiện đầu vào cho các tính năng tự động hoá phía sau như check-in bằng QR và chỉ đường tới slot.

### 3.5.2. Bản đồ bãi xe thời gian thực (Real-time Map)

![Giao diện bản đồ bãi xe](./screenshots/04-map.png)

_Hình 3.15: Giao diện bản đồ bãi xe thời gian thực và chỉ đường tới slot_

**Mô tả ngắn**: Trang bản đồ hiển thị sơ đồ bãi xe theo từng tầng, trạng thái từng ô đỗ được phân biệt bằng màu sắc và cập nhật tức thời qua WebSocket. Sau khi check-in, người dùng có thể xem đường đi từ cổng vào tới slot đã đặt và xem mô phỏng hoạt cảnh xe di chuyển theo lộ trình.

**Ý nghĩa**: Tính năng bản đồ giải quyết hai bài toán phổ biến tại các bãi xe lớn: người dùng không biết slot mình đã đặt nằm ở đâu và phải mất thời gian dò tìm. Việc cập nhật trạng thái ô đỗ theo thời gian thực còn hỗ trợ quản lý bãi nắm tổng thể mức độ lấp đầy, phục vụ ra quyết định điều phối lưu lượng xe vào/ra.

### 3.5.3. Chatbot AI (Trợ lý ảo thông minh)

![Giao diện Chatbot AI](./screenshots/06-support-chatbot.png)

_Hình 3.16: Giao diện chatbot AI hỗ trợ người dùng bằng tiếng Việt_

**Mô tả ngắn**: Chatbot tích hợp mô hình ngôn ngữ lớn Google Gemini và cơ chế Retrieval-Augmented Generation (RAG) với cơ sở tri thức nội bộ về chính sách, quy định và thông tin từng bãi xe. Người dùng có thể trò chuyện bằng tiếng Việt tự nhiên để tra cứu thông tin, đặt chỗ qua hội thoại nhiều lượt, hoặc nhận gợi ý các tác vụ phổ biến.

**Ý nghĩa**: Chatbot đóng vai trò kênh hỗ trợ 24/7 thay thế cho việc liên hệ tổng đài, giảm tải cho nhân viên vận hành và rút ngắn thời gian phản hồi cho người dùng. Cơ chế RAG đảm bảo chatbot trả lời dựa trên dữ liệu đã được kiểm duyệt thay vì bịa thông tin, mang lại độ tin cậy cao và phù hợp cho môi trường nghiệp vụ.

### 3.5.4. Check-in tự động bằng QR + AI biển số

![Giao diện kiểm tra check-in](./screenshots/05-history.png)

_Hình 3.17: Mã QR booking trên trang lịch sử dùng để check-in tại cổng_

**Mô tả ngắn**: Khi người dùng đến cổng và xuất trình mã QR đã đặt chỗ, hệ thống quét mã đồng thời sử dụng camera AI để nhận diện biển số xe và đối chiếu với booking. Khi thông tin khớp, thiết bị IoT điều khiển barrier tự động mở; sau ít giây barrier đóng lại để tránh nhiều xe lọt vào cùng lúc.

**Ý nghĩa**: Đây là tính năng thay thế hoàn toàn quy trình vé giấy và nhân viên thủ công tại cổng, đem lại trải nghiệm "vào — ra" nhanh chóng cho người dùng và giảm chi phí nhân sự cho bãi xe. Việc kết hợp hai kênh xác minh (QR + AI biển số) còn nâng cao tính an toàn — chỉ xe đúng biển số đã đăng ký mới được mở cổng, hạn chế nguy cơ sử dụng QR của người khác.

### 3.5.5. Nhận diện tiền mặt bằng AI tại cổng

![Ma trận nhầm lẫn của mô hình nhận diện tiền](./screenshots/09-banknote-confusion-matrix.png)

_Hình 3.18: Ma trận nhầm lẫn của mô hình nhận diện 9 mệnh giá tiền Việt Nam_

**Mô tả ngắn**: Khi người dùng chọn phương thức thanh toán "trả tại cổng" và đến cổng ra, hệ thống bật camera nhận diện tiền mặt; người dùng đưa từng tờ tiền trước camera và mô hình AI EfficientNetV2-S sẽ phân loại mệnh giá rồi tích luỹ cho đến khi đủ số tiền cần trả. Mô hình đạt độ chính xác 100% trên tập kiểm thử 3.818 ảnh thuộc 9 mệnh giá tiền Việt Nam (1.000 đ → 500.000 đ).

**Ý nghĩa**: Tính năng này mang lại sự linh hoạt cho người dùng không quen sử dụng các hình thức thanh toán điện tử, đặc biệt với khách lớn tuổi hoặc khách vãng lai. Đồng thời, việc đếm tiền tự động bằng AI giúp loại bỏ rủi ro nhầm lẫn của con người, giúp ghi nhận giao dịch chính xác và tích hợp được với dữ liệu doanh thu của hệ thống.

### 3.5.6. Mô phỏng 3D bãi xe (Digital Twin)

![Giao diện trang quản trị tổng quan](./screenshots/02-user-dashboard.png)

_Hình 3.19: Bảng điều khiển hiển thị tóm tắt tình trạng đậu xe của người dùng_

**Mô tả ngắn**: Hệ thống xây dựng một bản sao kỹ thuật số (Digital Twin) của bãi xe bằng Unity 3D với 158 ô đỗ, 6 camera ảo, mô phỏng đầy đủ luồng xe vào/ra và thiết bị ESP32 ảo. Bản sao này gọi vào cùng API của hệ thống thật và phát hiện ảnh từ camera ảo qua cùng pipeline AI nhận diện biển số.

**Ý nghĩa**: Digital Twin giải quyết bài toán lớn trong giai đoạn nghiên cứu — không có sẵn bãi xe thật và phần cứng IoT để kiểm thử. Nhờ mô phỏng, đội phát triển có thể kiểm thử toàn bộ luồng nghiệp vụ (đặt chỗ → check-in → đỗ xe → check-out) trong điều kiện sát thực mà không phụ thuộc phần cứng, đồng thời cho phép trình diễn hệ thống một cách trực quan trước hội đồng đánh giá.

### 3.5.7. Bảng điều khiển quản trị (Admin Dashboard)

![Giao diện Admin Dashboard](./screenshots/08-admin-dashboard.png)

_Hình 3.20: Giao diện trang quản trị tổng quan của hệ thống_

**Mô tả ngắn**: Trang quản trị tập trung hiển thị các chỉ số quan trọng (số người dùng, doanh thu, tỉ lệ lấp đầy bãi), tỉ lệ chiếm chỗ thời gian thực từ camera AI, danh sách hoạt động gần nhất và các phím tắt đến những trang quản trị con như quản lý người dùng, camera, ESP32 và báo cáo doanh thu.

**Ý nghĩa**: Bảng điều khiển quản trị cung cấp cho chủ bãi và quản lý vận hành cái nhìn tổng quan về sức khoẻ của hệ thống chỉ trên một màn hình, giảm thời gian truy vấn dữ liệu phân tán. Đây cũng là cơ sở để ra quyết định kinh doanh — biết được khung giờ cao điểm, doanh thu theo ngày/tuần/tháng, và phát hiện sớm các sự cố bất thường.