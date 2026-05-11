# Chương 4. KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN

---

## 4.1. Kết luận

### 4.1.1. Kết quả đạt được

Trong phạm vi khoá luận, tác giả đã xây dựng thành công hệ thống bãi giữ xe thông minh ParkSmart ở mức triển khai đầy đủ trên môi trường thực tế (https://parksmart.ghepdoicaulong.shop), với các thiết bị phần cứng mô phỏng quy mô nhỏ. Mô hình gần như hoàn thiện toàn bộ vòng đời nghiệp vụ của một bãi giữ xe hiện đại: đặt chỗ trực tuyến, check-in tại cổng, đỗ xe theo chỉ dẫn, check-out, thanh toán điện tử và tiền mặt, cùng giám sát hệ thống qua camera. Phần cứng camera vẫn còn thiếu hụt do chưa có điều kiện trang bị camera chuyên dụng.

Hệ thống đã tích hợp được các công nghệ hiện đại theo từng nhóm chức năng: **Django REST Framework** cho các dịch vụ quản lý dữ liệu nghiệp vụ, **FastAPI** cho các dịch vụ AI và xử lý bất đồng bộ, **Go (Gin + Gorilla WebSocket)** cho lớp Gateway và truyền thông thời gian thực, **React + Vite + Tailwind** cho giao diện người dùng đáp ứng đa thiết bị; **YOLOv8 + TrOCR** kết hợp với EasyOCR và Tesseract làm dự phòng cho nhận diện biển số xe, **EfficientNetV2-S** cho nhận diện 9 mệnh giá tiền giấy Việt Nam đạt độ chính xác 100% trên tập kiểm thử, **YOLO11n** cho phát hiện ô đỗ trống; **Internet of Things** với ESP32, Arduino UNO, servo điều khiển barrier, OLED hiển thị, camera quét QR và camera RTSP đọc biển số; **Chatbot AI** sử dụng Google Gemini kết hợp **Retrieval-Augmented Generation (RAG)** với cơ sở tri thức nội bộ; **Unity Digital Twin** mô phỏng bản sao kỹ thuật số của bãi xe gồm 158 ô đỗ và 6 camera ảo phục vụ kiểm thử toàn bộ pipeline.

### 4.1.2. Vấn đề đã được giải quyết

Hệ thống ParkSmart đã giải quyết hiệu quả những hạn chế cố hữu của mô hình bãi giữ xe truyền thống. Quy trình check-in và check-out hoàn toàn tự động đã giúp **giảm chi phí nhân sự** so với phương pháp thủ công, đồng thời mang lại trải nghiệm gửi và lấy xe **nhanh gọn, tiện lợi và an toàn** cho người dùng. Việc thay thế vé giấy bằng mã QR kỹ thuật số kết hợp xác minh chéo bằng AI biển số đã **hạn chế tối đa sai sót** và rủi ro thất lạc vé. Người dùng giờ đây có thể **chủ động** trong toàn bộ quá trình — biết trước tình trạng chỗ trống, đặt chỗ từ xa, check-in linh hoạt và thanh toán đa kênh, qua đó **nâng cao đáng kể trải nghiệm người dùng** so với phương thức truyền thống. Bên cạnh đó, dữ liệu vận hành được lưu trữ điện tử đầy đủ, giúp chủ bãi quản lý doanh thu minh bạch và có cơ sở dữ liệu để phân tích, ra quyết định kinh doanh.

### 4.1.3. Ưu điểm và khuyết điểm

#### 4.1.3.1. Ưu điểm

- **Tự động hoá toàn quy trình:** từ đặt chỗ, check-in, đỗ xe, đến thanh toán và check-out đều diễn ra tự động, nhanh chóng, tiện lợi và minh bạch.
- **Tích hợp AI sâu rộng:** nhận diện biển số xe, phát hiện ô đỗ trống, nhận diện mệnh giá tiền giấy và trợ lý hội thoại tiếng Việt đều được tích hợp ngay trong luồng nghiệp vụ.
- **Giao tiếp thời gian thực:** trạng thái ô đỗ, sự kiện check-in/check-out và các thay đổi nghiệp vụ được cập nhật tức thời lên giao diện người dùng và bảng quản trị.
- **Đa kênh tương tác:** người dùng có thể sử dụng hệ thống qua web đáp ứng đa thiết bị, qua trợ lý chatbot, qua thiết bị IoT tại cổng và qua mô phỏng 3D Digital Twin.
- **Kiến trúc microservices có tính mở rộng cao:** mỗi dịch vụ độc lập và có thể nhân bản theo nhu cầu, dễ dàng triển khai cho nhiều bãi giữ xe tại các trung tâm thương mại khác nhau.
- **Bảo mật nhiều lớp:** xác thực phiên đăng nhập, phân quyền theo vai trò, kiểm soát truy cập qua API Gateway, khoá bí mật nội bộ giữa các dịch vụ và token riêng cho thiết bị IoT.
- **Trải nghiệm người dùng được nâng cao:** đặt chỗ từ xa, biết trước tình trạng chỗ, có bản đồ chỉ đường tới slot và nhận thông báo theo thời gian thực.

#### 4.1.3.2. Khuyết điểm

- **Chi phí đầu tư phần cứng còn khá cao** khi triển khai ở quy mô bãi xe thực tế với nhiều cổng và camera chuyên dụng.
- **AI nhận diện biển số đôi lúc chưa chuẩn xác** trong các điều kiện ánh sáng kém, biển số bị mờ, bị che khuất hoặc góc chụp xiên.
- **Chatbot đôi lúc còn sai sót** trong các tác vụ đặt chỗ phức tạp do phụ thuộc vào chất lượng phản hồi của mô hình ngôn ngữ lớn từ bên thứ ba.
- **Camera và thiết bị IoT cần bảo trì định kỳ** để đảm bảo hệ thống hoạt động ổn định, đặc biệt là camera RTSP và servo điều khiển barrier.
- **Phần cứng hiện ở mức mô phỏng quy mô nhỏ:** servo SG90/MG996R chỉ phù hợp cho mô hình demo, chưa đáp ứng được tải trọng và độ bền của barrier công nghiệp.
- **Khả năng mở rộng đa bãi chưa cao:** kiến trúc hiện tại tối ưu cho một bãi đơn lẻ, cần điều chỉnh để hỗ trợ mô hình quản lý nhiều bãi đồng thời.

---

## 4.2. Hướng phát triển

### 4.2.1. Vấn đề còn tồn tại

- **Chatbot** đã hỗ trợ đặt chỗ và trả lời người dùng nhưng phản hồi đôi lúc chưa ổn định khi gặp các câu hỏi mơ hồ hoặc nhiều ý.
- **Độ chính xác của các mô hình AI** còn hạn chế trong môi trường thực tế khi điều kiện ánh sáng, góc chụp và chất lượng camera không đồng đều.
- **Phần cứng IoT** còn ở mức mô phỏng quy mô nhỏ, chưa được đầu tư các thiết bị công nghiệp đạt chuẩn vận hành.
- **Khả năng mở rộng hệ thống chưa cao**, dễ gây tắc nghẽn khi triển khai đồng thời cho nhiều bãi giữ xe và lưu lượng người dùng lớn.
- **Hệ thống thanh toán** chưa được tích hợp chính thức với các cổng thanh toán phổ biến tại Việt Nam như VNPay hay MoMo, hiện chỉ hỗ trợ chuyển khoản qua VietQR và tiền mặt tại cổng.
- **Giám sát và truy vết** chưa đạt chuẩn của một môi trường sản xuất quy mô lớn, thiếu các công cụ chuyên nghiệp như Prometheus, Grafana hay ELK Stack để theo dõi sức khoẻ hệ thống tập trung.
- **Bảo mật** chưa có các lớp bảo vệ nâng cao như xác thực hai yếu tố (2FA), xoay khoá API tự động hoặc tường lửa ứng dụng web (WAF).

### 4.2.2. Giải pháp và định hướng phát triển

- **Tối ưu hoá AI và Chatbot:** mở rộng và bổ sung dữ liệu huấn luyện cho các mô hình nhận diện biển số và phát hiện ô đỗ để cải thiện độ chính xác trong môi trường thực tế; đồng thời mở rộng cơ sở tri thức RAG và cải tiến khả năng phản hồi theo ngữ nghĩa và ngữ cảnh hội thoại của chatbot.
- **Tích hợp công nghệ định vị:** ứng dụng GPS, bản đồ số và các cảm biến hỗ trợ để hướng dẫn người dùng từ vị trí hiện tại đến bãi xe gần nhất, sau đó đến đúng slot đã đặt một cách trực quan nhất.
- **Mở rộng tính năng nhận diện:** hoàn thiện hơn nữa chức năng nhận diện tiền mặt để hỗ trợ nhiều mệnh giá và nhiều tình huống thực tế; đồng thời phát triển khả năng phát hiện loại xe, màu xe và phát hiện va chạm dựa trên hình ảnh từ camera.
- **Nâng cấp phần cứng:** thay thế các thiết bị mô phỏng (servo SG90, camera DroidCam) bằng các thiết bị công nghiệp tiên tiến và chuẩn xác hơn (motor DC/stepper với driver chuyên dụng, camera IP công nghiệp, cảm biến ô đỗ siêu âm/từ trường); bổ sung pin dự phòng (UPS) và cập nhật firmware từ xa (OTA) cho thiết bị ESP32.
- **Mở rộng thanh toán và quản lý doanh thu:** tích hợp chính thức với các cổng thanh toán phổ biến tại Việt Nam như VNPay, MoMo, ZaloPay; xây dựng hệ thống định giá động (dynamic pricing) theo giờ cao điểm và thấp điểm để tối ưu doanh thu cho chủ bãi.
- **Nâng cao bảo mật và giám sát:** triển khai xác thực hai yếu tố (2FA), cơ chế xoay khoá API tự động, tường lửa ứng dụng web (WAF) và hệ thống giám sát tập trung dựa trên Prometheus, Grafana, ELK Stack để đảm bảo hệ thống vận hành ổn định ở quy mô lớn.
- **Phát triển ứng dụng di động gốc:** xây dựng ứng dụng di động bằng React Native hoặc Flutter chia sẻ phần lớn nghiệp vụ với phiên bản web, giúp người dùng có trải nghiệm mượt mà hơn so với giao diện web đáp ứng hiện tại.
- **Mở rộng kiến trúc đa bãi:** thiết kế lại các thành phần chia sẻ và lớp điều phối IoT để hỗ trợ mô hình một hệ thống quản lý nhiều bãi xe, mở đường cho việc thương mại hoá và nhân rộng giải pháp tại nhiều địa điểm khác nhau.
- **Triển khai AI tại biên (Edge AI):** chuyển một phần luồng nhận diện AI từ máy chủ trung tâm về các thiết bị biên (Jetson Nano, Coral TPU) đặt gần camera, giúp giảm độ trễ, giảm tải băng thông và tăng tính tự chủ cho từng cổng bãi xe.

