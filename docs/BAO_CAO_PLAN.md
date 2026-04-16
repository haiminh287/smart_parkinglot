# KHÓA LUẬN TỐT NGHIỆP

## HỆ THỐNG BÃI GIỮ XE THÔNG MINH PARKSMART

### Smart Parking System with AI, IoT, and Microservices Architecture

**Sinh viên thực hiện:** Nguyễn Hải Minh

---

## LỜI CẢM ƠN

_(Phần này dành cho sinh viên tự viết)_

---

## LỜI CAM ĐOAN

Tác giả xin cam đoan rằng khóa luận tốt nghiệp với đề tài **"Xây dựng hệ thống bãi giữ xe thông minh ParkSmart ứng dụng IoT và nhận diện biển số tự động"** là công trình nghiên cứu và phát triển do chính tác giả thực hiện dưới sự hướng dẫn của giảng viên.

Các số liệu, kết quả trình bày trong khóa luận là trung thực và chưa từng được công bố trong bất kỳ công trình nào khác. Các thông tin tham khảo, trích dẫn trong khóa luận đều được ghi rõ nguồn gốc tại phần Tài liệu tham khảo.

Tác giả xin chịu hoàn toàn trách nhiệm về nội dung và tính trung thực của khóa luận này.

TP. Hồ Chí Minh, tháng 4 năm 2026

**Sinh viên thực hiện**

Nguyễn Hải Minh

---

## TÓM TẮT

Trong bối cảnh đô thị hóa nhanh chóng tại Việt Nam, đặc biệt tại Thành phố Hồ Chí Minh với hơn 8 triệu xe máy và gần 1 triệu ô tô đăng ký, hệ thống bãi giữ xe truyền thống bộc lộ nhiều hạn chế nghiêm trọng: ùn tắc cổng ra/vào, rủi ro mất vé và gian lận, quản lý doanh thu thiếu minh bạch, và thiếu dữ liệu phân tích. Khóa luận này trình bày việc nghiên cứu và phát triển **ParkSmart** — hệ thống bãi giữ xe thông minh tích hợp trí tuệ nhân tạo, Internet of Things, và kiến trúc Microservices nhằm giải quyết triệt để các hạn chế nêu trên.

Hệ thống được xây dựng trên nền tảng **10 microservices** (4 Django 5.2.12 + 4 FastAPI 0.134.0 + 2 Go 1.22), triển khai trong **15 Docker containers**, giao tiếp qua API Gateway duy nhất. Về trí tuệ nhân tạo, ParkSmart tích hợp **5 pipeline AI** phục vụ nhận diện biển số xe (YOLOv8 + TrOCR cascade), phát hiện trạng thái ô đỗ (YOLO11n), đọc mã QR (OpenCV), nhận dạng tiền giấy (MobileNetV3 multi-branch), và nhận dạng tiền mặt (ResNet50). Chatbot thông minh sử dụng Google Gemini (gemini-3-flash-preview) với **7 giai đoạn pipeline** (Wizard → Intent → Confidence Gate → Safety → Action → Response → Memory), hỗ trợ **16 loại intent** và đặt chỗ qua hội thoại tiếng Việt tự nhiên.

Giao diện người dùng là ứng dụng React 18 SPA với **28 trang** (19 root + 9 admin) và **73 tổng UI components** (51 shadcn/ui + 22 custom). Phần cứng IoT gồm ESP32 kết nối WiFi giao tiếp HTTP với AI server, Arduino điều khiển servo barrier qua UART, cùng màn hình OLED và camera IP. Bộ mô phỏng Digital Twin trên Unity 2022.3 LTS với **30 C# scripts**, **6 camera ảo**, và **158 ô đỗ** tạo procedural cho phép kiểm thử toàn bộ pipeline mà không cần phần cứng thực tế.

Kết quả đạt được bao gồm: quy trình check-in/check-out hoàn toàn tự động, hệ thống đặt chỗ trực tuyến với bản đồ real-time qua WebSocket, chatbot AI hỗ trợ tiếng Việt 24/7, nhận dạng tiền mặt tại quầy, và admin dashboard phân tích doanh thu.

**Từ khóa:** Bãi giữ xe thông minh, Nhận diện biển số tự động, Internet of Things, Microservices, Chatbot AI, Digital Twin.

---

## ABSTRACT

This thesis presents the design and implementation of **ParkSmart** — a smart parking system integrating Artificial Intelligence, Internet of Things, and Microservices Architecture. The system addresses critical limitations of traditional parking lots in Vietnam, including gate congestion, ticket fraud, opaque revenue management, and lack of analytical data.

ParkSmart comprises **10 microservices** (4 Django 5.2.12 + 4 FastAPI 0.134.0 + 2 Go 1.22) deployed across **15 Docker containers**. The AI subsystem features **5 pipelines** for license plate recognition (YOLOv8 + TrOCR với xử lý dự phòng theo tầng), parking slot occupancy detection (YOLO11n), QR code reading, banknote classification (MobileNetV3 multi-branch), and cash recognition (ResNet50). An AI chatbot powered by Google Gemini processes Vietnamese natural language through a **7-stage pipeline** supporting 16 intent types and conversational booking.

The frontend is a React 18 SPA with **28 pages** and **73 UI components**. The IoT hardware consists of an ESP32 WiFi gateway communicating via HTTP with the AI server, an Arduino controlling servo barriers via UART, an OLED display, and IP cameras. A Unity 2022.3 LTS Digital Twin simulator with 6 virtual cameras and 158 procedurally-generated parking slots enables end-to-end testing without physical hardware.

Key results include fully autonomous check-in/check-out, online booking with real-time WebSocket maps, 24/7 Vietnamese AI chatbot support, cash recognition at kiosks, and a comprehensive admin analytics dashboard.

**Keywords:** Smart Parking, Automatic Number Plate Recognition, IoT, Microservices, AI Chatbot, Digital Twin.

---

## DANH MỤC TỪ VIẾT TẮT

| Từ viết tắt | Giải thích                                                                     |
| ----------- | ------------------------------------------------------------------------------ |
| AI          | Artificial Intelligence — Trí tuệ nhân tạo                                     |
| AMQP        | Advanced Message Queuing Protocol — Giao thức hàng đợi tin nhắn nâng cao       |
| ANPR        | Automatic Number Plate Recognition — Nhận diện biển số tự động                 |
| API         | Application Programming Interface — Giao diện lập trình ứng dụng               |
| ASGI        | Asynchronous Server Gateway Interface — Giao diện cổng máy chủ bất đồng bộ     |
| BFS         | Breadth-First Search — Tìm kiếm theo chiều rộng                                |
| CNN         | Convolutional Neural Network — Mạng nơ-ron tích chập                           |
| CORS        | Cross-Origin Resource Sharing — Chia sẻ tài nguyên nguồn gốc chéo              |
| CRUD        | Create, Read, Update, Delete — Tạo, Đọc, Cập nhật, Xóa                         |
| CSRF        | Cross-Site Request Forgery — Giả mạo yêu cầu liên trang                        |
| CSP         | Content Security Policy — Chính sách bảo mật nội dung                          |
| CV          | Computer Vision — Thị giác máy tính                                            |
| DI          | Dependency Injection — Tiêm phụ thuộc                                          |
| DRF         | Django REST Framework                                                          |
| DTO         | Data Transfer Object — Đối tượng truyền dữ liệu                                |
| ERD         | Entity Relationship Diagram — Sơ đồ quan hệ thực thể                           |
| FSM         | Finite State Machine — Máy trạng thái hữu hạn                                  |
| GPIO        | General Purpose Input/Output — Cổng vào/ra đa dụng                             |
| GPS         | Global Positioning System — Hệ thống định vị toàn cầu                          |
| HMR         | Hot Module Replacement — Thay thế module nóng                                  |
| HSV         | Hue, Saturation, Value — Sắc độ, Bão hòa, Giá trị                              |
| HTTP        | HyperText Transfer Protocol — Giao thức truyền siêu văn bản                    |
| HSTS        | HTTP Strict Transport Security — Bảo mật vận chuyển nghiêm ngặt HTTP           |
| I2C         | Inter-Integrated Circuit — Mạch tích hợp liên kết                              |
| IoT         | Internet of Things — Internet Vạn Vật                                          |
| IoU         | Intersection over Union — Giao trên Hợp                                        |
| JWT         | JSON Web Token — Mã thông báo Web JSON                                         |
| LBP         | Local Binary Pattern — Mẫu nhị phân cục bộ                                     |
| LLM         | Large Language Model — Mô hình ngôn ngữ lớn                                    |
| LPR         | License Plate Recognition — Nhận diện biển số xe                               |
| LTS         | Long Term Support — Hỗ trợ dài hạn                                             |
| MQTT        | Message Queuing Telemetry Transport — Vận chuyển đo lường hàng đợi tin nhắn    |
| NLU         | Natural Language Understanding — Hiểu ngôn ngữ tự nhiên                        |
| OCR         | Optical Character Recognition — Nhận dạng ký tự quang học                      |
| OLED        | Organic Light-Emitting Diode — Diode phát quang hữu cơ                         |
| ORM         | Object-Relational Mapping — Ánh xạ đối tượng-quan hệ                           |
| OTA         | Over-The-Air — Cập nhật qua không dây                                          |
| PWM         | Pulse Width Modulation — Điều chế độ rộng xung                                 |
| QR          | Quick Response — Phản hồi nhanh                                                |
| RDBMS       | Relational Database Management System — Hệ quản trị CSDL quan hệ               |
| REST        | Representational State Transfer — Chuyển giao trạng thái đại diện              |
| RTSP        | Real Time Streaming Protocol — Giao thức truyền phát thời gian thực            |
| SPA         | Single Page Application — Ứng dụng trang đơn                                   |
| SQL         | Structured Query Language — Ngôn ngữ truy vấn có cấu trúc                      |
| SRP         | Scriptable Render Pipeline — Pipeline render có thể lập trình                  |
| TLS         | Transport Layer Security — Bảo mật tầng vận chuyển                             |
| TTL         | Time To Live — Thời gian sống                                                  |
| UART        | Universal Asynchronous Receiver-Transmitter — Bộ thu phát bất đồng bộ vạn năng |
| UDP         | User Datagram Protocol — Giao thức gói dữ liệu người dùng                      |
| URP         | Universal Render Pipeline — Pipeline render phổ quát                           |
| UUID        | Universally Unique Identifier — Định danh duy nhất toàn cục                    |
| WS          | WebSocket — Ổ cắm Web                                                          |
| WSGI        | Web Server Gateway Interface — Giao diện cổng máy chủ Web                      |
| YOLO        | You Only Look Once — Chỉ nhìn một lần                                          |

---

## MỤC LỤC

_(Mục lục được tạo tự động khi xuất bản — xem cấu trúc heading bên dưới)_

- Chương 1. TỔNG QUAN ĐỀ TÀI
- Chương 2. CƠ SỞ LÝ THUYẾT
- Chương 3. HỆ THỐNG PHÁT TRIỂN BÃI GIỮ XE THÔNG MINH ỨNG DỤNG IOT VÀ NHẬN DIỆN BIỂN SỐ TỰ ĐỘNG
- Chương 4. KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN
- TÀI LIỆU THAM KHẢO
- PHỤ LỤC

---

# Chương 1. TỔNG QUAN ĐỀ TÀI

---

## 1.1. Giới thiệu đề tài

Trong bối cảnh đô thị hóa nhanh chóng tại Việt Nam, số lượng phương tiện cá nhân tăng mạnh đã tạo ra áp lực lớn lên hệ thống bãi giữ xe truyền thống. Phần lớn các bãi xe hiện nay vẫn vận hành theo phương thức thủ công: phát vé giấy khi vào, đối chiếu vé khi ra, thu phí bằng tiền mặt, và ghi chép sổ sách bằng tay. Phương thức này không chỉ tốn thời gian, gây ùn tắc tại cổng vào/ra, mà còn tiềm ẩn nhiều rủi ro như mất vé, gian lận, và khó khăn trong công tác quản lý, thống kê doanh thu.

Nhận thấy nhu cầu cấp thiết về một giải pháp quản lý bãi xe hiện đại, đề tài **"Xây dựng hệ thống bãi giữ xe thông minh ParkSmart ứng dụng IoT và nhận diện biển số tự động"** được thực hiện nhằm nghiên cứu và phát triển một hệ thống toàn diện, tích hợp nhiều công nghệ tiên tiến để giải quyết triệt để các hạn chế của bãi xe truyền thống.

Hệ thống ParkSmart — đối tượng nghiên cứu và phát triển của đề tài — được xây dựng trên nền tảng kiến trúc **Microservices** với **10 dịch vụ backend độc lập** sử dụng đa ngôn ngữ (Python Django, Python FastAPI, và Go), giao tiếp với nhau và với phía máy khách thông qua một API Gateway duy nhất. Giao diện người dùng là ứng dụng web Single Page Application (SPA) phát triển bằng React kết hợp TypeScript, với 51 thành phần giao diện shadcn/ui và 22 thành phần tùy biến (tổng cộng 73 UI components). Chi tiết về kiến trúc tổng thể và danh sách từng dịch vụ được trình bày tại **Chương 3**.

Về phương diện trí tuệ nhân tạo, hệ thống tích hợp một **AI pipeline** đa tầng phục vụ các bài toán sau:

- **Nhận diện biển số xe (License Plate Recognition — LPR)**: Sử dụng mô hình YOLO được tinh chỉnh (fine-tuned) để phát hiện vùng biển số, kết hợp TrOCR (Transformer-based OCR) làm bộ đọc chính, với cơ chế fallback sang EasyOCR và Tesseract khi cần thiết.
- **Phát hiện trạng thái ô đỗ (Slot Occupancy Detection)**: Sử dụng YOLO11n (phiên bản nano, tối ưu cho thiết bị biên) để phát hiện phương tiện trên bản đồ bãi xe, kết hợp IoU (Intersection over Union) matching để xác định ô đỗ trống hay đã có xe.
- **Đọc mã QR**: Sử dụng thư viện OpenCV để quét và giải mã mã QR booking tại cổng vào/ra.
- **Nhận dạng tiền giấy Việt Nam**: Sử dụng mô hình MobileNetV3 kết hợp phân tích HSV để nhận dạng mệnh giá tiền mặt, phục vụ thanh toán tại quầy.

Bên cạnh các pipeline AI nêu trên, hệ thống còn tích hợp một **chatbot trợ lý ảo** dựa trên mô hình ngôn ngữ lớn Google Gemini (phiên bản `gemini-3-flash-preview`), cho phép người dùng tương tác bằng tiếng Việt tự nhiên để tra cứu thông tin bãi xe, đặt chỗ, kiểm tra trạng thái booking và nhận hỗ trợ trực tuyến 24/7.

Về phương diện phần cứng IoT, đề tài sử dụng vi điều khiển **ESP32** kết nối WiFi để giao tiếp với máy chủ AI qua giao thức HTTP REST, kết hợp với vi điều khiển **Arduino** điều khiển servo barrier mở/đóng cổng vào và cổng ra thông qua giao tiếp UART. Các thiết bị ngoại vi đi kèm bao gồm màn hình OLED SSD1306 hiển thị biển số xe nhận dạng được, nút nhấn kích hoạt thao tác check-in hoặc check-out, camera IP thu hình qua DroidCam và camera RTSP EZVIZ thu hình phục vụ nhận diện biển số.

---

## 1.2. Lý do chọn đề tài

### 1.2.1. Thực trạng bãi giữ xe truyền thống tại Việt Nam

Tại các đô thị lớn như Thành phố Hồ Chí Minh, Hà Nội, Đà Nẵng, vấn đề bãi giữ xe đang trở thành một trong những bài toán nan giải nhất của quy hoạch đô thị. Theo thống kê của Sở Giao thông Vận tải TP.HCM, thành phố hiện có hơn 8 triệu xe máy và gần 1 triệu ô tô đăng ký, trong khi diện tích dành cho bãi đỗ xe chỉ đáp ứng được khoảng 20% nhu cầu thực tế.

Phần lớn các bãi giữ xe hiện nay vẫn hoạt động theo mô hình **thủ công truyền thống** với nhiều hạn chế nghiêm trọng:

- **Ùn tắc tại cổng vào/ra**: Quy trình phát vé giấy khi vào và đối chiếu vé khi ra mất trung bình 30–60 giây mỗi lượt, gây tắc nghẽn vào giờ cao điểm. Người dùng không biết trước bãi xe còn chỗ trống hay không, dẫn đến việc loanh quanh tìm kiếm lãng phí thời gian.
- **Rủi ro mất vé và gian lận**: Vé giấy dễ bị mất, rách, hoặc làm giả. Khi mất vé, quy trình xác minh phương tiện trở nên phức tạp, tốn thời gian, và dễ xảy ra tranh chấp giữa người gửi xe và bảo vệ.
- **Quản lý doanh thu thiếu minh bạch**: Thu phí bằng tiền mặt, ghi sổ bằng tay khiến việc thống kê doanh thu thiếu chính xác. Chủ bãi xe khó kiểm soát được số lượng xe ra/vào thực tế, tạo kẽ hở cho thất thoát.
- **Thiếu dữ liệu phân tích**: Không có hệ thống lưu trữ dữ liệu điện tử, chủ bãi xe không thể phân tích xu hướng sử dụng, tối ưu giá cả, hay dự báo nhu cầu.
- **Trải nghiệm người dùng kém**: Không thể đặt chỗ trước, không biết bãi xe nào gần nhất còn chỗ, không có hỗ trợ tự động khi gặp sự cố.

### 1.2.2. Xu hướng bãi xe thông minh trên thế giới

Trên thế giới, **Smart Parking** đang là một trong những ứng dụng quan trọng nhất của hệ sinh thái thành phố thông minh (Smart City). Theo báo cáo của Grand View Research, thị trường smart parking toàn cầu được dự báo đạt 11,13 tỷ USD vào năm 2027 với tốc độ tăng trưởng CAGR 12,6%.

Các giải pháp smart parking tiên tiến trên thế giới đang áp dụng nhiều công nghệ hiện đại:

- **Nhận diện biển số tự động (ALPR/ANPR)**: Sử dụng camera AI để nhận dạng biển số xe, loại bỏ hoàn toàn vé giấy. Các hệ thống như ParkMobile (Mỹ), APCOA (châu Âu) đã triển khai rộng rãi công nghệ này.
- **Cảm biến IoT**: Cảm biến siêu âm hoặc từ trường gắn tại mỗi ô đỗ, truyền dữ liệu real-time về trạng thái trống/đã đỗ lên server trung tâm. Smart Parking Ltd (Úc) và Streetline (Mỹ) là những đơn vị tiên phong.
- **Ứng dụng di động + Đặt chỗ trước**: SpotHero, ParkWhiz cho phép người dùng tìm kiếm, so sánh giá, và đặt trước chỗ đỗ xe qua ứng dụng di động.
- **Thanh toán không tiền mặt**: Tích hợp các cổng thanh toán điện tử, ví điện tử, giảm thiểu giao dịch tiền mặt tại bãi.
- **AI và Machine Learning**: Phân tích dữ liệu historical để dự báo nhu cầu, tối ưu giá động (dynamic pricing), phát hiện bất thường.

### 1.2.3. Cơ hội ứng dụng AI và IoT

Sự phát triển vượt bậc của trí tuệ nhân tạo và Internet of Things trong những năm gần đây đã mở ra cơ hội lớn cho việc ứng dụng vào lĩnh vực quản lý bãi xe tại Việt Nam:

- **AI/Computer Vision**: Các mô hình deep learning như YOLO, TrOCR đã đạt độ chính xác cao trong nhận diện biển số, đủ khả năng thay thế con người trong việc kiểm soát xe ra/vào. Chi phí triển khai ngày càng giảm nhờ các mô hình nhỏ gọn (nano) chạy được trên phần cứng phổ thông.
- **IoT giá rẻ**: Các vi điều khiển WiFi như ESP32 có giá chỉ từ 50.000–100.000 VNĐ nhưng tích hợp sẵn WiFi, Bluetooth, nhiều GPIO, đủ mạnh để làm IoT gateway. Kết hợp với Arduino để điều khiển phần cứng, tổng chi phí một bộ gate controller không quá 500.000 VNĐ.
- **LLM (Large Language Model)**: Các mô hình ngôn ngữ lớn như Google Gemini, OpenAI GPT đã hỗ trợ tốt tiếng Việt, cho phép xây dựng chatbot trợ lý ảo hiểu và phản hồi tự nhiên bằng tiếng Việt.
- **Kiến trúc Microservices**: Pattern kiến trúc này cho phép phát triển từng phần độc lập, dễ mở rộng, phù hợp cho một hệ thống phức tạp cần tích hợp nhiều công nghệ khác nhau (Python cho AI/ML, Go cho hiệu năng cao, React cho giao diện).

Từ những phân tích trên, việc nghiên cứu và phát triển hệ thống bãi giữ xe thông minh ParkSmart không chỉ có ý nghĩa thực tiễn trong việc giải quyết vấn đề bãi xe tại Việt Nam, mà còn là cơ hội để áp dụng và tích hợp nhiều công nghệ hiện đại vào một sản phẩm hoàn chỉnh.

---

## 1.3. Mục tiêu đề tài

Đề tài đặt ra các mục tiêu cụ thể sau:

### 1.3.1. Mục tiêu tổng quát

Xây dựng một hệ thống bãi giữ xe thông minh hoàn chỉnh, tích hợp IoT, trí tuệ nhân tạo, và chatbot, cho phép tự động hóa quy trình gửi xe từ khâu đặt chỗ, check-in, đến check-out và thanh toán.

### 1.3.2. Mục tiêu cụ thể

**a) Hệ thống đặt chỗ trực tuyến (Online Booking)**

- Cho phép người dùng đăng ký tài khoản, đăng ký phương tiện (biển số, loại xe, màu sắc).
- Cung cấp bản đồ bãi xe thời gian thực (real-time map) hiển thị trạng thái từng ô đỗ (trống, đã đặt, đang sử dụng) với cập nhật tức thời qua WebSocket.
- Hỗ trợ đặt chỗ trước với nhiều gói thời gian (theo giờ, theo ngày, theo tuần, theo tháng), tự động sinh mã QR cho mỗi booking.
- Tích hợp thanh toán trực tuyến và thanh toán tiền mặt tại quầy (với nhận dạng mệnh giá bằng AI).

**b) Check-in/Check-out tự động qua nhận diện biển số**

- Tự động nhận diện biển số xe tại cổng vào/ra bằng camera AI, xác minh với booking đã đặt.
- Hỗ trợ quét mã QR booking tại cổng như phương thức xác thực bổ sung.
- Điều khiển barrier (thanh chắn) tự động mở/đóng dựa trên kết quả xác minh.
- Toàn bộ quy trình check-in/check-out diễn ra tự động, không cần nhân viên can thiệp.

**c) Chatbot AI hỗ trợ tiếng Việt**

- Xây dựng chatbot thông minh tích hợp mô hình ngôn ngữ lớn Google Gemini, hiểu và phản hồi tiếng Việt tự nhiên.
- Hỗ trợ các tác vụ: tra cứu chỗ trống, đặt chỗ qua hội thoại (booking wizard), kiểm tra trạng thái booking, hỏi đáp thông tin bãi xe.
- Tích hợp cơ chế phát hiện ý định (intent detection) đa tầng, cổng tin cậy (confidence gate), và kiểm tra an toàn (safety validation).

**d) IoT Gateway với ESP32 và Arduino**

- Phát triển firmware ESP32 kết nối WiFi, giao tiếp với AI server qua HTTP REST/JSON.
- Phát triển firmware Arduino điều khiển servo barrier qua giao tiếp UART với ESP32.
- Tích hợp màn hình OLED hiển thị trạng thái, biển số xe, và thông báo cho người dùng tại cổng.
- Xây dựng giao thức giao tiếp UART tùy chỉnh giữa ESP32 và Arduino với cơ chế auto-close barrier và heartbeat monitoring.

---

## 1.4. Phương pháp thực hiện

### 1.4.1. Khảo sát thực trạng bãi xe truyền thống

Quá trình thực hiện đề tài bắt đầu bằng việc khảo sát thực tế hoạt động tại các bãi giữ xe truyền thống tại khu vực Thành phố Hồ Chí Minh. Qua khảo sát, nhóm đã ghi nhận các vấn đề chính cần giải quyết:

- **Quy trình vào/ra**: Mất trung bình 30–60 giây cho mỗi lượt xe, chủ yếu do thao tác phát vé, kiểm tra vé thủ công. Vào giờ cao điểm (7h–9h sáng, 17h–19h chiều), hàng chờ có thể kéo dài 10–15 phút.
- **Quản lý chỗ trống**: Bảo vệ phải đi kiểm tra trực tiếp hoặc dựa vào kinh nghiệm để biết còn chỗ trống. Không có cơ chế thông báo cho khách hàng biết trước tình trạng bãi xe.
- **Thanh toán**: 100% tiền mặt, không có hóa đơn điện tử. Khách thường xuyên không có tiền lẻ, gây chậm trễ. Chủ bãi khó kiểm soát doanh thu thực tế.
- **Bảo mật**: Vé giấy dễ làm giả hoặc sao chép. Không có hệ thống xác minh chủ sở hữu phương tiện ngoài việc đối chiếu vé.
- **Báo cáo và phân tích**: Hoàn toàn thủ công, không có dữ liệu số để phân tích xu hướng, tối ưu vận hành.

### 1.4.2. Giải pháp: Microservices + AI + IoT + Chatbot

Dựa trên kết quả khảo sát và phân tích yêu cầu, nhóm đề xuất giải pháp tổng thể với 4 trụ cột công nghệ chính:

**a) Kiến trúc Microservices**

Hệ thống được thiết kế theo kiến trúc microservices với 10 dịch vụ độc lập, mỗi dịch vụ đảm nhận một chức năng nghiệp vụ cụ thể. Kiến trúc đa ngôn ngữ (Python, Go) cho phép lựa chọn công nghệ phù hợp nhất cho từng loại tác vụ, đồng thời hỗ trợ phát triển, kiểm thử, và triển khai từng dịch vụ một cách độc lập. Toàn bộ hệ thống được đóng gói trong Docker container, quản lý bằng Docker Compose, giao tiếp qua API Gateway duy nhất, chia sẻ cơ sở dữ liệu MySQL 8.0, cache Redis 7, và message broker RabbitMQ. Danh sách chi tiết từng dịch vụ và bảng công nghệ được trình bày tại **Mục 3.1**.

**b) Trí tuệ nhân tạo (AI)**

AI pipeline được xây dựng tại ai-service-fastapi với 5 pipeline xử lý chuyên biệt:

- **Plate Recognition Pipeline**: YOLO (fine-tuned cho biển số Việt Nam) → TrOCR → EasyOCR → Tesseract (xử lý dự phòng từng tầng), đạt độ chính xác cao trên biển số Việt Nam.
- **Slot Detection Pipeline**: YOLO11n (nano) phát hiện phương tiện trên camera overview, IoU matching với tọa độ ô đỗ đã cấu hình.
- **QR Code Pipeline**: OpenCV detect và decode mã QR booking.
- **Banknote Detection Pipeline**: Hybrid approach kết hợp HSV color analysis và MobileNetV3 deep learning.
- **Cash Recognition Pipeline**: ResNet50 nhận dạng mệnh giá tiền Việt Nam.

**c) Internet of Things (IoT)**

Hệ thống phần cứng IoT đứng tại cổng ra/vào bãi xe, bao gồm:

- ESP32 làm IoT gateway: kết nối WiFi, nhận lệnh từ nút nhấn, gửi request đến AI server, hiển thị kết quả trên OLED, gửi lệnh mở/đóng barrier qua UART.
- Arduino điều khiển 2 servo motor (cổng vào và cổng ra) dựa trên lệnh UART từ ESP32.
- Camera IP (DroidCam trên smartphone) và camera RTSP (EZVIZ) cung cấp hình ảnh cho AI xử lý.

**d) Chatbot AI**

Chatbot service được xây dựng theo kiến trúc Hexagonal (Domain/Application/Infrastructure), pipeline 7 giai đoạn (Wizard → Intent → Confidence Gate → Safety → Action → Response → Memory) tích hợp Google Gemini LLM, hỗ trợ tiếng Việt, với booking wizard đa bước cho phép đặt chỗ hoàn toàn qua hội thoại.

**e) Phương pháp phát triển phần mềm**

- **Quy trình Agile/Scrum**: Phát triển theo sprint, mỗi sprint 1–2 tuần, ưu tiên deliverable.
- **Git workflow**: Conventional commits, feature branching, code review.
- **Testing**: Unit test (pytest, vitest), E2E test (Playwright [30]), integration test.
- **CI/CD**: Docker build, Docker Compose deployment.

---

## 1.5. Bố cục đề tài

Đề tài được trình bày trong 4 chương với nội dung như sau:

**Chương 1: Tổng quan đề tài** — Giới thiệu đề tài, lý do chọn đề tài, mục tiêu và phương pháp thực hiện. Chương này đặt nền tảng cho toàn bộ báo cáo bằng việc phân tích bối cảnh thực tế, xác định vấn đề cần giải quyết, và đề xuất giải pháp tổng thể.

**Chương 2: Cơ sở lý thuyết** — Trình bày nền tảng lý thuyết của 9 nhóm công nghệ cốt lõi được sử dụng trong đề tài: Hạ tầng và kiến trúc Microservices (MySQL, Redis, RabbitMQ, Docker, Nginx), Trí tuệ nhân tạo và Thị giác máy tính (nhận diện biển số, phát hiện phương tiện, nhận dạng tiền), Internet of Things (phần cứng nhúng ESP32, Arduino), Django REST Framework (backend API), FastAPI (backend bất đồng bộ), Go với Gin và WebSocket (API Gateway và real-time), ReactJS (giao diện người dùng), Chatbot AI (trợ lý ảo tích hợp Gemini), và Unity Game Engine (mô phỏng 3D Digital Twin). Các nhóm công nghệ được sắp xếp theo mức độ quan trọng đối với hệ thống. Mỗi nhóm công nghệ được phân tích từ góc độ giới thiệu, lý do lựa chọn (kèm bảng so sánh với giải pháp thay thế), kiến trúc, kỹ thuật cụ thể áp dụng, đến đánh giá ưu nhược điểm trong bối cảnh dự án.

**Chương 3: Phân tích và thiết kế hệ thống** — Phân tích yêu cầu hệ thống thông qua sơ đồ use case, đặc tả chi tiết các chức năng. Trình bày thiết kế kiến trúc microservices, sơ đồ cơ sở dữ liệu, thiết kế API, và luồng xử lý nghiệp vụ. Giới thiệu kết quả giao diện và demo chức năng đã phát triển.

**Chương 4: Kết luận và hướng phát triển** — Tổng kết kết quả đạt được, đánh giá ưu nhược điểm, và đề xuất hướng phát triển tương lai cho hệ thống ParkSmart.

---

# Chương 2. CƠ SỞ LÝ THUYẾT

---

Chương này trình bày cơ sở lý thuyết của **mười nhóm công nghệ** được ParkSmart áp dụng, sắp xếp theo **mức độ trọng yếu đối với đóng góp khoa học của đề tài** — ưu tiên trình bày các công nghệ cốt lõi tạo nên sự khác biệt trước, sau đó mới đến các framework phát triển ứng dụng và cuối cùng là hạ tầng hỗ trợ.

Mở đầu là **kiến trúc Microservices** (Mục 2.1) — bộ khung tổng thể định hình toàn bộ cách các dịch vụ trong hệ thống giao tiếp, triển khai và mở rộng độc lập. Tiếp theo, ba trụ cột công nghệ mang tính đặc thù của đề tài được trình bày tuần tự: **Trí tuệ nhân tạo và Thị giác máy tính** (Mục 2.2) — năm pipeline AI xử lý nhận diện biển số, phát hiện ô đỗ, đọc mã QR và nhận dạng tiền giấy; **Chatbot AI** (Mục 2.3) — trợ lý ảo tiếng Việt sử dụng mô hình ngôn ngữ lớn Google Gemini với pipeline bảy giai đoạn; và **Internet of Things** (Mục 2.4) — hệ thống phần cứng ESP32–Arduino điều khiển barrier vật lý tại cổng bãi xe. Mục 2.5 giới thiệu **bộ mô phỏng Unity Digital Twin** — công cụ kiểm thử toàn bộ pipeline ParkSmart trong môi trường 3D mà không cần phần cứng thực tế, giúp nhóm phát triển lặp nhanh trong giai đoạn nghiên cứu.

Các mục 2.6 đến 2.9 trình bày **các framework phát triển ứng dụng**: **Django REST Framework** cho bốn dịch vụ backend nghiệp vụ (Mục 2.6), **FastAPI** cho bốn dịch vụ backend bất đồng bộ và AI (Mục 2.7), **ngôn ngữ Go cùng Gin Framework và Gorilla WebSocket** cho hai dịch vụ hiệu năng cao là Gateway và Realtime (Mục 2.8), và **ReactJS kết hợp TypeScript** cho ứng dụng giao diện người dùng dạng Single Page Application (Mục 2.9). Kết thúc chương, Mục 2.10 tổng hợp các **dịch vụ hạ tầng và triển khai** bao gồm MySQL, Redis, RabbitMQ, Docker và Nginx — những thành phần vận hành nền tảng được chia sẻ giữa tất cả các microservice.

Mỗi nhóm công nghệ được trình bày thuần theo tính chất **cơ sở lý thuyết**, với bốn tiểu mục tiêu chuẩn: (1) **giới thiệu khái niệm** — định nghĩa công nghệ, lịch sử ra đời, tác giả và vị trí trong hệ sinh thái phần mềm; (2) **kiến trúc và nguyên lý hoạt động** — các thành phần chính, sơ đồ kiến trúc chung và các khái niệm kỹ thuật nền tảng; (3) **so sánh với các công nghệ thay thế** — bảng đánh giá song song với hai đến ba phương án tương đương, kèm đoạn biện luận ngắn về lý do đề tài lựa chọn công nghệ này; (4) **ưu điểm và nhược điểm** — đánh giá các đặc tính kỹ thuật vốn có của công nghệ trong khung tham chiếu phổ quát.

Chi tiết về **cách đề tài ParkSmart triển khai và áp dụng** từng công nghệ cụ thể — bao gồm cấu hình, phiên bản thư viện, tham số thuật toán, kiến trúc thư mục mã nguồn, và các quyết định thiết kế gắn với bài toán bãi giữ xe — được trình bày tại **Chương 3** (Hệ thống phát triển bãi giữ xe thông minh ứng dụng IoT và nhận diện biển số tự động). Cách phân tách này tuân thủ nguyên tắc **"cơ sở lý thuyết thuần túy"** của chuẩn khóa luận tốt nghiệp: Chương 2 trả lời câu hỏi _"công nghệ này là gì và hoạt động ra sao?"_, trong khi Chương 3 trả lời câu hỏi _"đề tài đã sử dụng công nghệ này như thế nào?"_. Sự phân tách rõ ràng giữa hai câu hỏi giúp người đọc có thể tiếp cận Chương 2 như một tài liệu giới thiệu công nghệ độc lập, và Chương 3 như một mô tả kỹ thuật triển khai có đủ chiều sâu.

> **Ghi chú về thứ tự và nguyên tắc trình bày**: Thứ tự các mục 2.1 → 2.10 được tái cấu trúc theo triết lý "Core and Unique First" — đưa các đóng góp khoa học đặc thù của đề tài lên trước, dồn các hạ tầng hỗ trợ phổ biến xuống sau. Nội dung các mục được viết theo nguyên tắc **lý thuyết thuần túy**, hạn chế lồng ghép chi tiết triển khai cụ thể của ParkSmart. Bảng ánh xạ với phiên bản cũ, danh sách các phần đã được chuyển sang Chương 3, và hướng dẫn tra cứu chéo được trình bày tại tài liệu phụ trợ `docs/BAO_CAO_PLAN_REORDER_GUIDE.md`.

## 2.1. Hạ tầng và Triển khai hệ thống

Một hệ thống microservices với nhiều dịch vụ độc lập không thể vận hành nếu chỉ có mã nguồn ứng dụng — nó cần một **hạ tầng kỹ thuật** bao gồm cơ sở dữ liệu lưu trữ, hệ thống cache và message broker cho giao tiếp giữa các dịch vụ, nền tảng containerization đảm bảo tính nhất quán môi trường, và reverse proxy phục vụ traffic production. Phần này trình bày lý thuyết về các thành phần hạ tầng cốt lõi và mô hình kiến trúc microservices mà ParkSmart áp dụng.

### 2.1.1. MySQL — Hệ quản trị cơ sở dữ liệu quan hệ

MySQL là hệ quản trị cơ sở dữ liệu quan hệ (Relational Database Management System — RDBMS) mã nguồn mở phổ biến nhất thế giới, được phát triển bởi Oracle Corporation [16]. Phiên bản sử dụng trong ParkSmart là **MySQL 8.0** — phiên bản lớn nhất tính đến thời điểm hiện tại, mang đến nhiều cải tiến quan trọng so với MySQL 5.x: hỗ trợ kiểu dữ liệu JSON native, window functions, Common Table Expressions (CTEs), cải thiện hiệu năng InnoDB engine, và tăng cường bảo mật với caching_sha2_password làm plugin xác thực mặc định.

MySQL hoạt động theo mô hình client-server: MySQL Server (mysqld) chạy như một tiến trình daemon, lắng nghe kết nối trên port 3306, tiếp nhận câu lệnh SQL từ client, thực thi truy vấn trên dữ liệu lưu trong storage engine (mặc định là InnoDB), và trả kết quả về client. InnoDB engine đảm bảo tính **ACID** (Atomicity, Consistency, Isolation, Durability) — bốn thuộc tính nền tảng của giao dịch cơ sở dữ liệu đáng tin cậy: mỗi giao dịch hoặc hoàn thành toàn bộ hoặc rollback hoàn toàn (Atomicity), dữ liệu luôn ở trạng thái hợp lệ sau mỗi giao dịch (Consistency), các giao dịch đồng thời không ảnh hưởng lẫn nhau (Isolation), và dữ liệu đã commit không bị mất ngay cả khi server crash (Durability). InnoDB còn hỗ trợ row-level locking (khóa ở mức dòng thay vì toàn bảng), foreign key constraints, và full-text search — tất cả cần thiết cho ứng dụng đa dịch vụ truy cập đồng thời như ParkSmart.

Trong kiến trúc ParkSmart, MySQL đóng vai trò **cơ sở dữ liệu duy nhất** của toàn hệ thống, lưu trữ trong một database đơn `parksmartdb`. Tất cả 9 dịch vụ Python đều kết nối đến cùng MySQL instance — tuy nhiên, mỗi dịch vụ sở hữu và quản lý tập bảng riêng của mình, không truy cập trực tiếp vào bảng của dịch vụ khác. Đây là pattern **Database-per-Service (logical)** — một biến thể phổ biến trong microservices nơi chi phí vận hành nhiều database instance riêng biệt chưa cần thiết. Về mặt triển khai, MySQL chạy trong Docker container với port mapping 3307 (host) → 3306 (container), sử dụng UUID dạng CHAR(36) làm primary key cho tất cả các bảng — đảm bảo tính duy nhất toàn cục (globally unique) mà không cần đồng bộ auto-increment giữa các dịch vụ.

**Lý do lựa chọn MySQL cho ParkSmart:**

ParkSmart yêu cầu một RDBMS có tính nhất quán cao (ACID), hỗ trợ quan hệ phức tạp giữa các thực thể (user–vehicle–booking–parking slot), tích hợp tốt với Django ORM (framework chính của 4/9 Python services), và dễ triển khai trong môi trường Docker. Bảng dưới so sánh MySQL 8.0 với ba lựa chọn phổ biến khác:

| Tiêu chí                     | MySQL 8.0          | PostgreSQL 16        | MongoDB 7            | SQLite 3          |
| ---------------------------- | ------------------ | -------------------- | -------------------- | ----------------- |
| Mô hình dữ liệu              | Quan hệ (SQL)      | Quan hệ (SQL)        | Tài liệu (NoSQL)     | Quan hệ (SQL)     |
| ACID compliance              | ✅ Đầy đủ (InnoDB) | ✅ Đầy đủ            | ⚠️ Ở mức document    | ✅ Đầy đủ         |
| Quan hệ phức tạp (FK, JOINs) | ✅ Tốt             | ✅ Rất tốt           | ❌ Không native      | ⚠️ Hạn chế        |
| Hỗ trợ JSON native           | ✅ (từ 5.7+)       | ✅ (JSONB, mạnh hơn) | ✅ (native document) | ❌ Không          |
| Django ORM tích hợp          | ✅ First-class     | ✅ First-class       | ⚠️ Cần djongo        | ✅ Mặc định       |
| Concurrent connections       | ✅ Hàng ngàn       | ✅ Hàng ngàn         | ✅ Hàng ngàn         | ❌ Một writer/lần |
| Cộng đồng và hosting         | ⭐⭐⭐⭐⭐         | ⭐⭐⭐⭐             | ⭐⭐⭐⭐             | ⭐⭐              |
| Hiệu năng ghi (writes)       | ⭐⭐⭐⭐           | ⭐⭐⭐⭐⭐           | ⭐⭐⭐⭐⭐           | ⭐⭐              |
| Docker deployment            | ✅ Official image  | ✅ Official image    | ✅ Official image    | ❌ Embedded       |

MySQL và PostgreSQL đều đáp ứng tốt yêu cầu ACID, quan hệ phức tạp, và Django ORM — hai ứng cử viên hàng đầu. PostgreSQL có ưu thế ở JSON processing (JSONB nhanh hơn MySQL JSON) và một số advanced features (partial indexes, materialized views, array types). Tuy nhiên, MySQL được lựa chọn cho ParkSmart vì ba lý do: (1) đội ngũ phát triển đã có kinh nghiệm làm việc với MySQL, giảm learning curve; (2) MySQL có cộng đồng sử dụng lớn nhất, tài liệu phong phú, dễ tìm hỗ trợ khi gặp vấn đề; (3) các tính năng advanced của PostgreSQL (JSONB, materialized views) chưa cần thiết cho scope hiện tại của ParkSmart — dữ liệu chủ yếu là quan hệ (user, vehicle, booking, slot), lượng JSON data không lớn. MongoDB bị loại vì ParkSmart có mô hình dữ liệu quan hệ rõ ràng (foreign keys giữa booking–user–vehicle–slot) mà document model không phù hợp. SQLite bị loại vì không hỗ trợ concurrent writes — hệ thống 10 services truy cập đồng thời sẽ gặp lock contention nghiêm trọng.

### 2.1.2. Redis — In-memory Cache và Message Broker

Redis (Remote Dictionary Server) là hệ thống lưu trữ dữ liệu **in-memory** (trong bộ nhớ RAM) theo mô hình key-value, được phát triển bởi Salvatore Sanfilippo [17]. Phiên bản sử dụng trong ParkSmart là **Redis 7** (image: redis:7-alpine). Khác với MySQL lưu dữ liệu trên đĩa cứng, Redis lưu toàn bộ dữ liệu trong RAM — cho tốc độ đọc/ghi ở mức **sub-millisecond** (dưới 1 mili-giây), nhanh hơn hàng trăm lần so với truy vấn database truyền thống. Redis hỗ trợ nhiều cấu trúc dữ liệu phong phú: strings, hashes, lists, sets, sorted sets, streams, và HyperLogLog — vượt xa mô hình key-value đơn giản. Ngoài ra, Redis còn cung cấp cơ chế **Pub/Sub** (Publish/Subscribe) cho messaging thời gian thực và khả năng **persistence** (lưu snapshot dữ liệu xuống đĩa qua RDB/AOF) để phục hồi sau restart.

Trong kiến trúc ParkSmart, Redis đảm nhận **năm vai trò đồng thời** — biến một công cụ duy nhất thành thành phần đa năng nhất của hạ tầng:

**Thứ nhất — Celery Broker và Result Backend (DB 0)**: Booking Service sử dụng Celery 5.4.0 cho các tác vụ bất đồng bộ — kiểm tra booking hết hạn, dọn dẹp định kỳ, gửi thông báo async. Redis DB 0 đóng vai trò message broker: khi Celery Beat lên lịch một task, nó đẩy message vào Redis queue; Celery Worker liên tục lắng nghe queue, lấy message ra và thực thi task; kết quả task được lưu lại trong cùng Redis DB 0 để tra cứu trạng thái.

**Thứ hai — Session Store cho Gateway (DB 1)**: Gateway Service (Go) lưu trữ session data người dùng trong Redis DB 1. Mỗi khi user đăng nhập, Auth Service tạo session và lưu vào Redis; mỗi request tiếp theo, Gateway tra cứu session trong Redis với độ trễ sub-millisecond để xác thực. Sử dụng Redis cho session (thay vì cookie-based JWT) cho phép **server-side session revocation** — khi user logout hoặc bị khóa tài khoản, chỉ cần xóa key trong Redis là session bị vô hiệu ngay lập tức.

**Thứ ba — Cache Layer cho các microservices (DB 2–4)**: Booking Service (DB 2), Parking Service và Chatbot Service (DB 3), và Vehicle Service (DB 4) sử dụng Redis để cache dữ liệu thường xuyên truy cập — thông tin parking slot, danh sách booking active, thông tin vehicle. Cache giúp giảm tải cho MySQL: thay vì mỗi request đều query database, service kiểm tra Redis trước — nếu dữ liệu đã có trong cache (cache hit), trả về ngay với latency sub-millisecond; nếu không (cache miss), query MySQL rồi lưu kết quả vào Redis cho lần sau.

**Thứ tư — Pub/Sub Channel cho Real-time Events (DB 5)**: Khi trạng thái bãi xe thay đổi (xe vào/ra slot), Parking Service publish event vào Redis pub/sub channel (DB 5). Realtime Service (Go) subscribe channel này và nhận event gần như tức thời, sau đó broadcast qua WebSocket đến tất cả client đang kết nối. Cơ chế pub/sub cho phép giao tiếp giữa Python services và Go services mà hai bên không cần biết nhau tồn tại — cùng một Redis instance làm trung gian.

**Thứ năm — Chatbot Conversation Cache (DB 6)**: Chatbot Service lưu ngữ cảnh hội thoại (conversation context) của từng user vào Redis DB 6, cho phép chatbot nhớ nội dung trao đổi trước đó trong cùng phiên hội thoại mà không cần query database mỗi lượt. Redis tự động xóa dữ liệu hết hạn (TTL — Time To Live), phù hợp cho conversation cache chỉ cần giữ trong thời gian ngắn.

Việc phân chia 7 logical databases (DB 0–6) trong cùng một Redis instance giúp ParkSmart tách biệt dữ liệu theo mục đích sử dụng mà không cần vận hành nhiều Redis server. Mỗi database hoạt động như một namespace riêng — data trong DB 0 (Celery) không xung đột với DB 1 (session), lệnh `FLUSHDB` chỉ xóa dữ liệu trong database hiện tại mà không ảnh hưởng database khác.

### 2.1.3. RabbitMQ — Message Broker theo chuẩn AMQP

RabbitMQ là hệ thống message broker mã nguồn mở, triển khai chuẩn giao thức **AMQP** (Advanced Message Queuing Protocol) — giao thức tiêu chuẩn cho truyền tải message đáng tin cậy giữa các ứng dụng phân tán [18]. Phiên bản sử dụng trong ParkSmart là **RabbitMQ 3** (image: rabbitmq:3-management-alpine), bao gồm giao diện quản trị web tại port 15672 và kết nối AMQP tại port 5672. RabbitMQ hoạt động theo mô hình **producer → exchange → queue → consumer**: producer gửi message đến exchange, exchange định tuyến message vào các queue dựa trên routing rules, consumer lắng nghe queue và xử lý message. Đặc điểm quan trọng nhất của RabbitMQ là **message persistence** (lưu trữ message trên đĩa) và **acknowledgment mechanism** (consumer xác nhận đã xử lý xong message) — đảm bảo không có message nào bị mất, ngay cả khi consumer bị crash giữa chừng.

Trong ParkSmart, RabbitMQ phục vụ làm broker cho **event-driven messaging giữa các microservices** — không phải cho Celery tasks (Celery sử dụng Redis DB 0 [17]): khi Auth Service tạo tài khoản mới, Booking Service tạo booking, hoặc Parking Service cập nhật trạng thái bãi xe, các service này publish event vào RabbitMQ. Chatbot Service subscribe các event này để gửi thông báo chủ động (proactive notification) đến người dùng — ví dụ: "Booking của bạn đã được xác nhận" hoặc "Xe của bạn đã rời bãi." Python client sử dụng thư viện aio-pika 9.4.0 (async AMQP client) để giao tiếp với RabbitMQ không chặn event loop.

**Lý do sử dụng RabbitMQ song song với Redis Pub/Sub:**

ParkSmart đã sử dụng Redis pub/sub (DB 5) cho real-time events — vậy tại sao cần thêm RabbitMQ? Câu trả lời nằm ở sự khác biệt cơ bản giữa hai cơ chế:

- **Redis Pub/Sub** hoạt động theo mô hình **gửi và quên**: khi publisher gửi message, subscriber đang online sẽ nhận được; nhưng nếu subscriber offline (bị restart, mất kết nối), message **bị mất hoàn toàn** — Redis không lưu trữ message chưa được nhận. Điều này chấp nhận được cho real-time slot updates (nếu client bỏ lỡ một cập nhật, vài giây sau sẽ có cập nhật mới) nhưng không chấp nhận được cho thông báo booking.
- **RabbitMQ** hoạt động theo mô hình **lưu và chuyển tiếp**: message được lưu trữ trong hàng đợi trên đĩa cho đến khi consumer xác nhận đã xử lý xong (acknowledgment). Nếu consumer bị crash, message vẫn nằm trong queue và sẽ được gửi lại khi consumer khởi động lại. Đây chính là **đảm bảo giao nhận** — đảm bảo message không bị mất.

ParkSmart sử dụng cả hai: Redis pub/sub cho real-time UI updates (latency thấp, mất message không nghiêm trọng), RabbitMQ cho critical business events (booking notifications, payment confirmations — PHẢI được gửi đến user, không được mất).

### 2.1.4. Docker và Docker Compose — Containerization

Docker là nền tảng **containerization** mã nguồn mở cho phép đóng gói ứng dụng cùng toàn bộ dependencies (thư viện, runtime, cấu hình) vào một đơn vị triển khai di động gọi là **container** [15]. Container chia sẻ kernel hệ điều hành host nhưng cô lập hoàn toàn filesystem, network, và process space — nhẹ hơn nhiều so với máy ảo (Virtual Machine) vốn phải chạy cả một guest OS riêng biệt. Mỗi service trong ParkSmart được đóng gói thành một Docker image thông qua **Dockerfile** — file cấu hình mô tả các bước xây dựng image (base image, copy source code, install dependencies, expose port, start command).

**Docker Compose** là công cụ orchestration cho phép định nghĩa và quản lý ứng dụng **multi-container** bằng một file cấu hình YAML duy nhất. Thay vì chạy 15 lệnh `docker run` riêng lẻ, Docker Compose cho phép khai báo toàn bộ 15 containers cùng volumes, networks, environment variables, health checks, và dependency order trong file `docker-compose.yml`, sau đó khởi động toàn bộ hệ thống bằng một lệnh `docker compose up`. Compose cũng quản lý vòng đời container: khởi động theo thứ tự phụ thuộc (MySQL khởi động trước services cần database), restart khi container crash, và dọn dẹp khi dừng hệ thống.

Trong ParkSmart, Docker Compose quản lý tổng cộng **15 containers** (16 trong production với Nginx):

- **3 containers hạ tầng**: MySQL 8.0, Redis 7 (Alpine), RabbitMQ 3 (Management Alpine)
- **4 containers Django services**: Auth Service, Booking Service, Parking Service, Vehicle Service — mỗi service chạy trên Gunicorn 22.0.0 (WSGI production server)
- **4 containers FastAPI services**: AI Service, Chatbot Service, Payment Service, Notification Service — mỗi service chạy trên Uvicorn (ASGI production server)
- **2 containers Go services**: Gateway Service, Realtime Service — mỗi service là compiled binary chạy trực tiếp
- **2 containers Celery**: Worker (xử lý task) và Beat (lên lịch task định kỳ) cho Booking Service
- **1 container Nginx** (chỉ production): reverse proxy và static file serving

Tất cả containers giao tiếp qua Docker internal network (`parksmart-network`, bridge mode) — mỗi container có hostname trùng với service name, cho phép service gọi nhau bằng tên (ví dụ: `http://booking-service:8002`) thay vì IP address. Dữ liệu bền vững được lưu trong Docker volumes: `mysql_data`, `redis_data`, `rabbitmq_data` cho infrastructure, `ai_models` và `ai_datasets` cho file mô hình AI.

**Lý do lựa chọn Docker cho ParkSmart:**

| Tiêu chí                       | Docker Container                    | Máy ảo (VM)                    | Bare Metal        | Serverless (FaaS)           |
| ------------------------------ | ----------------------------------- | ------------------------------ | ----------------- | --------------------------- |
| Mức độ cô lập                  | ⭐⭐⭐⭐ (process-level)            | ⭐⭐⭐⭐⭐ (OS-level)          | ⭐ (không cô lập) | ⭐⭐⭐⭐⭐ (function-level) |
| Thời gian khởi động            | Vài giây                            | Vài phút                       | Không áp dụng     | Mili-giây                   |
| Overhead tài nguyên            | Thấp (~10MB/container)              | Cao (~1GB/VM)                  | Không có          | Biến thiên                  |
| Tính tái tạo (reproducibility) | ⭐⭐⭐⭐⭐ (Dockerfile = blueprint) | ⭐⭐⭐ (cần provisioning tool) | ⭐ (cài thủ công) | ⭐⭐⭐ (vendor lock-in)     |
| Dev-Prod parity                | ✅ Cùng image cho mọi môi trường    | ⚠️ Khó đảm bảo                 | ❌ Khác biệt lớn  | ❌ Khác biệt lớn            |
| Multi-language support         | ✅ Mỗi container = runtime riêng    | ✅ Mỗi VM = OS riêng           | ⚠️ Phức tạp       | ⚠️ Giới hạn runtime         |

Docker là lựa chọn tối ưu cho ParkSmart vì hai lý do cốt lõi: (1) **Tái tạo môi trường** — Dockerfile đóng vai trò "bản thiết kế" cho mỗi service, đảm bảo môi trường phát triển (máy tính lập trình viên), staging, và production hoàn toàn giống nhau — loại bỏ lỗi "chỉ chạy được trên máy của lập trình viên"; (2) **Multi-language support** — ParkSmart sử dụng đồng thời Python 3.11+ và Go 1.22, mỗi ngôn ngữ cần runtime khác nhau — Docker cho phép mỗi service có container riêng với đúng runtime cần thiết, không xung đột dependencies. VM bị loại vì overhead quá lớn (chạy 15 VM đòi hỏi hàng chục GB RAM). Serverless bị loại vì ParkSmart cần WebSocket connections dài hạn (realtime service) và AI model loading nặng (ai-service) — không phù hợp với mô hình function-as-a-service ngắn hạn.

### 2.1.5. Nginx — Reverse Proxy và Web Server

Nginx (đọc "engine-x") là phần mềm web server và reverse proxy hiệu năng cao, nổi tiếng với khả năng xử lý hàng chục ngàn kết nối đồng thời nhờ kiến trúc event-driven, non-blocking I/O. Trong ParkSmart, Nginx được triển khai trong môi trường production (image: nginx:alpine) với bốn vai trò chính:

**Thứ nhất — Phục vụ static frontend**: Nginx serve trực tiếp các file tĩnh của ứng dụng React (HTML, CSS, JavaScript, hình ảnh) từ thư mục build (`spotlove-ai/dist/`). Mỗi khi người dùng truy cập trang web, Nginx trả về file `index.html` — từ đó React app khởi động và xử lý routing phía client (client-side routing). Nginx phục vụ file tĩnh nhanh hơn đáng kể so với bất kỳ application server nào (Gunicorn, Uvicorn) vì nó được thiết kế chuyên biệt cho tác vụ này.

**Thứ hai — Reverse proxy cho API requests**: Mọi request có path `/api/*` được Nginx chuyển tiếp đến Gateway Service (port 8000). Nginx đóng vai trò "lớp chắn" đầu tiên — client chỉ thấy một endpoint duy nhất, không biết phía sau có 10 services riêng biệt. Cấu hình proxy bao gồm truyền tiếp headers (`X-Real-IP`, `X-Forwarded-For`, `Host`) để backend services nhận được thông tin chính xác về client gốc.

**Thứ ba — WebSocket upgrade**: Các request đến path `/ws/*` được Nginx upgrade từ HTTP sang giao thức WebSocket và chuyển tiếp đến Realtime Service (port 8006). Nginx xử lý HTTP Upgrade handshake (header `Connection: Upgrade`, `Upgrade: websocket`) và duy trì kết nối persistent cho WebSocket communication.

**Thứ tư — Security headers và tối ưu hiệu năng**: Nginx tự động thêm các HTTP security headers theo khuyến nghị OWASP: `Content-Security-Policy` (CSP) ngăn XSS injection, `Strict-Transport-Security` (HSTS) bắt buộc HTTPS, `X-Frame-Options` ngăn clickjacking, `X-Content-Type-Options` ngăn MIME type sniffing. Về hiệu năng, Nginx bật Gzip compression giảm kích thước response truyền tải, và cấu hình cache policy dài hạn (1 năm, immutable) cho static assets có content hash trong tên file — giảm đáng kể bandwidth và thời gian tải trang.

### 2.1.6. Kiến trúc Microservices — Mô hình phát triển phần mềm

**Microservices** (kiến trúc vi dịch vụ) là mô hình thiết kế phần mềm trong đó một ứng dụng được phân rã thành tập hợp các **dịch vụ nhỏ, độc lập**, mỗi dịch vụ đảm nhận một chức năng nghiệp vụ cụ thể và giao tiếp qua các giao thức nhẹ như HTTP REST hoặc hàng đợi tin nhắn [23]. Thuật ngữ này được **Martin Fowler** và **James Lewis** chính thức định nghĩa vào năm 2014, kế thừa các ý tưởng từ kiến trúc hướng dịch vụ (SOA) nhưng đặt trọng tâm vào **độc lập hóa triển khai** và **tự trị nghiệp vụ** ở mức chi tiết hơn.

Kiến trúc microservices đối lập với mô hình **Monolithic** — nơi toàn bộ ứng dụng nằm trong một mã nguồn duy nhất, chia sẻ chung một connection pool cơ sở dữ liệu, và mọi thay đổi đều yêu cầu triển khai lại toàn bộ hệ thống. Monolithic đơn giản khi khởi đầu nhưng bộc lộ hạn chế khi ứng dụng lớn lên: cập lệ (coupling) giữa các module tăng cao, khó kiểm thử riêng từng phần, và một lỗi cục bộ có thể kéo theo sự cố toàn hệ thống.

**Các nguyên tắc thiết kế cốt lõi:**

1. **Single Responsibility**: Mỗi dịch vụ đảm nhận đúng một miền nghiệp vụ (bounded context), không can thiệp vào miền của dịch vụ khác.
2. **Independent Deployment**: Một dịch vụ có thể được cập nhật, triển khai, hoặc khôi phục độc lập với các dịch vụ còn lại.
3. **Decentralized Data Management**: Mỗi dịch vụ sở hữu cơ sở dữ liệu riêng; mọi trao đổi dữ liệu phải đi qua API công khai hoặc sự kiện bất đồng bộ.
4. **Failure Isolation**: Một dịch vụ gặp sự cố không làm sập các dịch vụ khác, nhờ cơ chế timeout, retry, và circuit breaker.
5. **Technology Heterogeneity**: Mỗi dịch vụ có thể dùng ngôn ngữ lập trình và cơ sở dữ liệu phù hợp nhất với bài toán của nó.

**Các mẫu thiết kế phổ biến:**

- **API Gateway Pattern**: Toàn bộ yêu cầu từ client đi qua một điểm vào duy nhất đảm nhiệm xác thực, định tuyến, và giới hạn tần suất.
- **Database per Service**: Mỗi microservice sở hữu cơ sở dữ liệu riêng (vật lý hoặc logic) để đảm bảo cô lập schema.
- **Service Discovery**: Các dịch vụ đăng ký địa chỉ vào một registry trung tâm để tra cứu lẫn nhau mà không cần mã hóa cứng địa chỉ.
- **Circuit Breaker**: Tạm thời ngừng gọi đến dịch vụ đang gặp sự cố, ngăn chặn hiện tượng **cascade failure** lan ra toàn hệ thống.
- **Event-Driven Architecture**: Các dịch vụ giao tiếp bất đồng bộ qua sự kiện thông qua message broker, giảm cập lệ giữa publisher và subscriber.
- **Saga Pattern**: Chia một giao dịch nghiệp vụ dài thành chuỗi giao dịch cục bộ, mỗi bước có cơ chế compensate khi bước sau thất bại — giải pháp thay thế two-phase commit trong môi trường phân tán.

**So sánh với các kiến trúc phần mềm thay thế:**

| Tiêu chí                      | Microservices              | Monolithic                 | Serverless (FaaS)        |
| ----------------------------- | -------------------------- | -------------------------- | ------------------------ |
| Độ phức tạp ban đầu           | Cao                        | Thấp                       | Trung bình               |
| Khả năng mở rộng              | ✅ Từng dịch vụ độc lập    | ❌ Phải mở rộng toàn bộ    | ✅ Tự động per-function  |
| Hỗ trợ đa ngôn ngữ lập trình  | ✅ Mỗi dịch vụ tùy chọn    | ❌ Một ngôn ngữ duy nhất   | ⚠️ Giới hạn runtime      |
| Cô lập lỗi                    | ✅ Mức dịch vụ             | ❌ Một lỗi sập toàn bộ     | ✅ Mức function          |
| Triển khai độc lập            | ✅                         | ❌                         | ✅                       |
| Nhất quán dữ liệu             | ⚠️ Eventual consistency    | ✅ ACID trong 1 database   | ⚠️ Eventual consistency  |
| Chi phí hạ tầng               | Cao                        | Thấp                       | Thấp (pay per use)       |
| Độ phức tạp gỡ lỗi            | Cao (distributed tracing)  | Thấp                       | Rất cao (ephemeral)      |

Microservices là lựa chọn tối ưu khi dự án cần sử dụng đồng thời nhiều ngôn ngữ lập trình, có các thành phần với yêu cầu tài nguyên khác biệt rõ rệt, hoặc yêu cầu cô lập lỗi nghiêm ngặt giữa các chức năng. Chi tiết phân rã các microservice cụ thể của đề tài ParkSmart được trình bày tại **Chương 3, Mục 3.1.2**.

### 2.1.7. Ưu và nhược điểm của kiến trúc Microservices

**Ưu điểm:**

- **Mở rộng độc lập**: Mỗi dịch vụ được scale theo nhu cầu riêng, tối ưu chi phí hạ tầng so với monolithic vốn phải scale toàn bộ ứng dụng.
- **Cô lập lỗi**: Một dịch vụ gặp sự cố không kéo theo toàn hệ thống sập, kết hợp với circuit breaker cho phép hệ thống **tự phục hồi** khỏi các sự cố cục bộ.
- **Triển khai nhanh chóng**: Các dịch vụ được triển khai độc lập nhiều lần mỗi ngày, rút ngắn chu kỳ phản hồi với người dùng.
- **Tự do công nghệ**: Mỗi dịch vụ có thể sử dụng ngôn ngữ và cơ sở dữ liệu phù hợp nhất với bài toán — tận dụng thế mạnh của từng công nghệ thay vì ràng buộc bởi một lựa chọn đa năng.

**Nhược điểm:**

- **Vận hành phức tạp**: Quản lý nhiều dịch vụ cùng lúc đòi hỏi kinh nghiệm DevOps và các công cụ monitoring, logging, service discovery — rào cản với đội nhỏ.
- **Gỡ lỗi khó khăn**: Một request đi qua nhiều dịch vụ nối tiếp cần công cụ truy vết phân tán như Jaeger hoặc OpenTelemetry để xác định nguyên nhân lỗi.
- **Giao dịch phân tán**: Không thể đảm bảo ACID xuyên qua nhiều dịch vụ theo cách truyền thống; phải áp dụng Saga hoặc chấp nhận **nhất quán dần dần (eventual consistency)**.
- **Chi phí hạ tầng cao hơn**: Nhiều container và tiến trình đồng thời làm tăng tổng chi phí so với monolithic — lợi ích chỉ được bù đắp khi dự án đủ lớn.

Mặc dù có các nhược điểm nêu trên, microservices vẫn là kiến trúc chuẩn mực cho các hệ thống phần mềm quy mô trung bình đến lớn hiện nay, được các công ty như Netflix, Amazon, Uber, và Spotify áp dụng rộng rãi từ đầu thập niên 2010.

---

## 2.2. Trí tuệ nhân tạo và Thị giác máy tính

Phần này trình bày trụ cột công nghệ cốt lõi tạo nên sự khác biệt của ParkSmart so với bãi xe truyền thống: **Trí tuệ nhân tạo (Artificial Intelligence — AI)** và **Thị giác máy tính (Computer Vision — CV)**. Trước khi đi vào các ứng dụng cụ thể trong dự án, cần hiểu rõ nền tảng lý thuyết của các lĩnh vực này — từ khái niệm AI tổng quát, qua Machine Learning và Deep Learning, đến Computer Vision và kiến trúc mạng nơ-ron tích chập (CNN) — bởi đây chính là nền tảng khoa học mà mọi pipeline AI trong ParkSmart được xây dựng lên.

### 2.2.1. Trí tuệ nhân tạo (Artificial Intelligence)

**Trí tuệ nhân tạo (Artificial Intelligence — AI)** là lĩnh vực khoa học máy tính nghiên cứu và phát triển các hệ thống có khả năng thực hiện những nhiệm vụ thường đòi hỏi trí tuệ con người — bao gồm nhận diện hình ảnh, hiểu ngôn ngữ tự nhiên, ra quyết định, và giải quyết vấn đề. Thuật ngữ "Artificial Intelligence" được chính thức đề xuất bởi John McCarthy tại hội nghị Dartmouth năm 1956, đánh dấu sự ra đời của AI như một ngành học thuật độc lập.

Trước đó, Alan Turing đã đặt nền móng lý thuyết với bài báo "Computing Machinery and Intelligence" (1950), đề xuất **Turing Test** — tiêu chí đánh giá khả năng "suy nghĩ" của máy tính thông qua việc liệu một người đánh giá có thể phân biệt được phản hồi của máy với phản hồi của con người hay không. Ý tưởng cốt lõi của Turing đã trở thành kim chỉ nam cho nghiên cứu AI trong nhiều thập kỷ.

**Các nhánh chính của AI:**

| Nhánh | Mô tả | Ví dụ ứng dụng |
| --- | --- | --- |
| **Machine Learning (ML)** | Hệ thống học từ dữ liệu, cải thiện hiệu năng theo thời gian mà không cần lập trình cụ thể từng quy tắc | Dự đoán spam email, đề xuất sản phẩm |
| **Deep Learning (DL)** | Nhánh con của ML sử dụng mạng nơ-ron nhiều tầng (deep neural networks) để học các biểu diễn phức tạp từ dữ liệu | Nhận diện khuôn mặt, dịch máy |
| **Computer Vision (CV)** | Máy tính "nhìn" và hiểu nội dung hình ảnh/video | Phát hiện đối tượng, nhận dạng biển số |
| **Natural Language Processing (NLP)** | Máy tính hiểu và xử lý ngôn ngữ tự nhiên của con người | Chatbot, tóm tắt văn bản |
| **Robotics** | Hệ thống tự động thực hiện hành động vật lý trong thế giới thực | Robot công nghiệp, xe tự lái |
| **Expert Systems** | Hệ thống mô phỏng khả năng ra quyết định của chuyên gia trong lĩnh vực cụ thể | Chẩn đoán y tế, hệ thống tư vấn |

**Phân loại AI theo năng lực:**

- **Narrow AI (AI hẹp)**: Hệ thống AI được thiết kế và huấn luyện cho một nhiệm vụ cụ thể. Đây là dạng AI duy nhất đã đạt được trong thực tế hiện nay — ví dụ: hệ thống nhận diện biển số xe, trợ lý ảo Siri/Alexa, AlphaGo. Mỗi hệ thống chỉ giỏi trong phạm vi nhiệm vụ nó được huấn luyện.
- **General AI (AI tổng quát / AGI)**: Hệ thống AI có khả năng nhận thức, học hỏi và thực hiện bất kỳ nhiệm vụ trí tuệ nào mà con người có thể làm. AGI hiện vẫn là mục tiêu nghiên cứu dài hạn, chưa đạt được.
- **Super AI (Siêu AI / ASI)**: AI vượt qua trí tuệ con người ở mọi lĩnh vực — hiện chỉ là khái niệm lý thuyết.

Tất cả các ứng dụng AI trong đề tài này (nhận diện biển số, phát hiện ô đỗ, nhận dạng tiền giấy, chatbot) đều thuộc dạng **Narrow AI** — mỗi pipeline được huấn luyện chuyên biệt cho một bài toán duy nhất.

### 2.2.2. Học máy và Học sâu (Machine Learning & Deep Learning)

**Machine Learning (Học máy)** là nhánh quan trọng nhất của AI, nghiên cứu các thuật toán cho phép máy tính tự động cải thiện hiệu năng thông qua kinh nghiệm (dữ liệu) mà không cần được lập trình một cách tường minh cho từng tình huống. Theo định nghĩa kinh điển của Tom Mitchell (1997): "Một chương trình máy tính được gọi là học từ kinh nghiệm E đối với một lớp nhiệm vụ T và thước đo hiệu năng P, nếu hiệu năng của nó trên T, được đo bằng P, cải thiện theo E."

**Ba phương pháp học máy cơ bản:**

1. **Supervised Learning (Học có giám sát)**: Học từ dữ liệu đã được gán nhãn (labeled data). Mô hình nhận đầu vào X và đầu ra mong muốn Y, học ánh xạ f: X → Y. Ví dụ: phân loại ảnh (đầu vào = ảnh, nhãn = "chó" hoặc "mèo"), nhận diện biển số (đầu vào = ảnh xe, nhãn = vị trí biển số). Đây là phương pháp được sử dụng chính trong đề tài.
2. **Unsupervised Learning (Học không giám sát)**: Học từ dữ liệu không có nhãn, tìm cấu trúc ẩn trong dữ liệu. Ví dụ: phân cụm (clustering) khách hàng, giảm chiều dữ liệu (dimensionality reduction).
3. **Reinforcement Learning (Học tăng cường)**: Agent tương tác với môi trường, nhận phần thưởng (reward) hoặc hình phạt (penalty) cho mỗi hành động, học chiến lược tối ưu theo thời gian. Ví dụ: AlphaGo, xe tự lái.

**Deep Learning (Học sâu)** là nhánh con của Machine Learning sử dụng **mạng nơ-ron nhân tạo (Artificial Neural Network — ANN)** với nhiều tầng ẩn (hidden layers) để tự động học các đặc trưng (features) phức tạp từ dữ liệu thô, thay vì phải thiết kế đặc trưng thủ công (manual feature engineering) như ML truyền thống.

**Kiến trúc mạng nơ-ron nhân tạo cơ bản:**

- **Neuron nhân tạo (Perceptron)**: Đơn vị tính toán cơ bản, mô phỏng neuron sinh học. Nhận nhiều đầu vào x₁, x₂, ..., xₙ, mỗi đầu vào có trọng số (weight) w₁, w₂, ..., wₙ, tính tổng có trọng số z = Σ(wᵢ·xᵢ) + b (bias), rồi đưa qua hàm kích hoạt (activation function) để tạo đầu ra.
- **Hàm kích hoạt (Activation Function)**: Đưa phi tuyến vào mạng, cho phép mô hình học các patterns phức tạp. Các hàm phổ biến: **ReLU** (f(x) = max(0, x) — đơn giản, hiệu quả, giải quyết vanishing gradient), **Sigmoid** (f(x) = 1/(1+e⁻ˣ) — nén output về [0,1]), **Softmax** (chuẩn hóa vector thành phân phối xác suất — dùng cho bài toán phân loại nhiều lớp).
- **Tầng (Layer)**: Các neuron được tổ chức thành tầng: Input Layer (nhận dữ liệu thô), Hidden Layers (trích xuất đặc trưng, càng nhiều tầng → "càng sâu" → học đặc trưng phức tạp hơn), Output Layer (trả kết quả cuối cùng).

**Quá trình huấn luyện (Training Process):**

1. **Forward Propagation (Lan truyền thuận)**: Dữ liệu đầu vào đi qua các tầng từ input → hidden → output, mỗi tầng thực hiện phép biến đổi toán học (nhân ma trận trọng số + hàm kích hoạt).
2. **Loss Function (Hàm mất mát)**: Đo lường sai lệch giữa kết quả dự đoán và kết quả thực tế. Ví dụ: Cross-Entropy Loss cho phân loại, Mean Squared Error cho hồi quy.
3. **Backpropagation (Lan truyền ngược)**: Tính gradient (đạo hàm riêng) của loss function theo từng trọng số, lan truyền ngược từ output về input thông qua quy tắc chuỗi (chain rule).
4. **Gradient Descent (Hạ gradient)**: Cập nhật trọng số theo hướng giảm gradient: w_new = w_old − η·∂L/∂w, với η là tốc độ học (learning rate). Các biến thể cải tiến: **SGD** (Stochastic Gradient Descent), **Adam** (Adaptive Moment Estimation — kết hợp momentum và adaptive learning rate, được sử dụng rộng rãi nhất hiện nay).

**Mối quan hệ bao hàm: AI ⊃ ML ⊃ DL**

```
┌──────────────────────────────────────────────────────────┐
│  Artificial Intelligence (AI)                            │
│  Hệ thống thể hiện hành vi thông minh                   │
│                                                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Machine Learning (ML)                             │  │
│  │  Học từ dữ liệu, không cần lập trình tường minh   │  │
│  │                                                    │  │
│  │  ┌──────────────────────────────────────────────┐  │  │
│  │  │  Deep Learning (DL)                          │  │  │
│  │  │  Mạng nơ-ron nhiều tầng                      │  │  │
│  │  │  Tự động trích xuất đặc trưng                │  │  │
│  │  │                                              │  │  │
│  │  │  CNN, RNN, Transformer, GAN, ...             │  │  │
│  │  └──────────────────────────────────────────────┘  │  │
│  │                                                    │  │
│  │  SVM, Random Forest, KNN, Naive Bayes, ...        │  │
│  └────────────────────────────────────────────────────┘  │
│                                                          │
│  Expert Systems, Logic-based AI, Search Algorithms, ...  │
└──────────────────────────────────────────────────────────┘
```

Điểm khác biệt then chốt giữa ML truyền thống và Deep Learning nằm ở **trích xuất đặc trưng**: ML truyền thống yêu cầu người thiết kế phải tự chọn đặc trưng đầu vào (ví dụ: histogram màu, HOG descriptor, LBP texture — đây gọi là **feature engineering**), trong khi Deep Learning tự động học đặc trưng tối ưu từ dữ liệu thô thông qua nhiều tầng biểu diễn (representation learning). Khả năng này giúp Deep Learning vượt trội ở các bài toán xử lý dữ liệu phi cấu trúc như ảnh, âm thanh, và văn bản.

### 2.2.3. Thị giác máy tính (Computer Vision)

**Thị giác máy tính (Computer Vision — CV)** là lĩnh vực liên ngành nghiên cứu cách máy tính có thể hiểu được nội dung hình ảnh và video kỹ thuật số ở **mức ngữ nghĩa** — tương tự cách hệ thống thị giác của con người nhận diện đối tượng, đọc chữ viết, và hiểu bối cảnh không gian. Computer Vision nằm ở giao điểm của khoa học máy tính, toán học ứng dụng, và khoa học nhận thức.

**Lịch sử phát triển:**

- **Thập niên 1960–1970**: Những nghiên cứu đầu tiên tại MIT (Larry Roberts, 1963) về nhận diện hình học 3D từ ảnh 2D. Hướng tiếp cận dựa trên quy tắc thủ công (rule-based), xử lý cạnh (edge detection) và biến đổi hình học.
- **Thập niên 1980–1990**: Phát triển các kỹ thuật xử lý ảnh cổ điển: bộ lọc Gaussian, phát hiện cạnh Canny (1986), biến đổi Hough, optical flow. Các thuật toán feature-based: SIFT (Scale-Invariant Feature Transform, 1999), HOG (Histogram of Oriented Gradients, 2005).
- **Thập niên 2000**: Machine Learning bắt đầu ứng dụng vào CV: Support Vector Machine (SVM) kết hợp HOG cho phát hiện người đi bộ (Dalal & Triggs, 2005), Viola-Jones detector cho nhận diện khuôn mặt (2001).
- **2012 — Bước ngoặt ImageNet**: Mạng **AlexNet** (Alex Krizhevsky, 2012) lần đầu sử dụng Deep CNN trong cuộc thi phân loại ảnh ImageNet Large Scale Visual Recognition Challenge (ILSVRC), giảm top-5 error rate từ 25.8% (phương pháp truyền thống) xuống 16.4% — mở ra kỷ nguyên Deep Learning cho Computer Vision. Từ đây, mọi bài toán CV đều chuyển sang hướng tiếp cận deep learning.
- **2015–nay**: Đột phá liên tiếp — ResNet (2015, 152 tầng, skip connections), YOLO (2016, real-time object detection), Transformer trong CV (ViT, 2020), Foundation Models (SAM, DINO, 2023).

**Các bài toán cơ bản trong Computer Vision:**

| Bài toán | Mô tả | Đầu ra | Ví dụ mô hình |
| --- | --- | --- | --- |
| **Image Classification** | Phân loại toàn bộ ảnh thuộc lớp nào | Nhãn lớp + xác suất | ResNet, MobileNet, EfficientNet |
| **Object Detection** | Phát hiện VỊ TRÍ (bounding box) và LOẠI đối tượng trong ảnh | Danh sách [bbox, class, confidence] | YOLO, Faster R-CNN, SSD |
| **Semantic Segmentation** | Phân loại từng pixel trong ảnh thuộc lớp nào | Mask (cùng kích thước ảnh) | U-Net, DeepLab, FCN |
| **Instance Segmentation** | Phân loại + tách biệt từng instance đối tượng | Mask + instance ID | Mask R-CNN, YOLACT |
| **Optical Character Recognition (OCR)** | Nhận diện và đọc chữ viết trong ảnh | Chuỗi ký tự | TrOCR, Tesseract, EasyOCR |
| **Pose Estimation** | Phát hiện các điểm khớp (keypoints) trên cơ thể | Tọa độ keypoints | OpenPose, MediaPipe |

Trong đề tài ParkSmart, ba bài toán được sử dụng trực tiếp là: **Object Detection** (phát hiện biển số xe, phát hiện xe trong ô đỗ), **Image Classification** (phân loại mệnh giá tiền giấy), và **OCR** (đọc ký tự biển số).

### 2.2.4. Mạng nơ-ron tích chập (Convolutional Neural Network — CNN)

**Mạng nơ-ron tích chập (CNN)** là kiến trúc mạng nơ-ron sâu được thiết kế đặc biệt cho dữ liệu có cấu trúc lưới (grid-like topology), đặc biệt là hình ảnh. CNN là nền tảng của hầu hết các mô hình Computer Vision hiện đại — từ image classification đến object detection, OCR, và segmentation. Ý tưởng CNN được khởi nguồn từ nghiên cứu sinh học thần kinh thị giác của Hubel & Wiesel (1962) về cách vỏ não thị giác (visual cortex) của động vật có vú xử lý thông tin hình ảnh thông qua các tế bào thần kinh phản ứng với các vùng nhỏ trong trường thị giác (receptive fields).

**Các tầng cơ bản trong kiến trúc CNN:**

1. **Convolutional Layer (Tầng tích chập)**: Đây là tầng cốt lõi đặc trưng của CNN. Sử dụng các bộ lọc (filter/kernel) — ma trận trọng số nhỏ (thường 3×3 hoặc 5×5) — trượt qua toàn bộ ảnh đầu vào, thực hiện phép tích chập (convolution) tại mỗi vị trí để tạo ra **feature map** (bản đồ đặc trưng). Mỗi bộ lọc học cách phát hiện một đặc trưng cụ thể: cạnh ngang, cạnh dọc, góc, kết cấu, v.v. Tầng tích chập có hai đặc điểm quan trọng: **parameter sharing** (cùng bộ lọc dùng chung cho mọi vị trí trên ảnh, giảm đáng kể số tham số so với fully connected) và **translation invariance** (phát hiện đặc trưng bất kể vị trí trong ảnh).

2. **Pooling Layer (Tầng gộp)**: Giảm kích thước không gian (spatial dimensions) của feature map, giữ lại thông tin quan trọng nhất. Hai loại phổ biến: **Max Pooling** (lấy giá trị lớn nhất trong vùng cửa sổ, ví dụ 2×2 → giảm kích thước một nửa) và **Average Pooling** (lấy trung bình). Max Pooling được sử dụng phổ biến hơn vì giữ lại các đặc trưng nổi bật nhất. Pooling giúp giảm tính toán, tăng receptive field, và tạo tính bất biến nhỏ với dịch chuyển (slight translation invariance).

3. **Fully Connected Layer (Tầng kết nối đầy đủ)**: Sau khi các tầng tích chập và pooling trích xuất đặc trưng, feature maps được làm phẳng (flatten) thành vector 1D, đưa qua tầng fully connected để thực hiện phân loại cuối cùng. Tầng cuối thường dùng hàm Softmax (phân loại nhiều lớp) hoặc Sigmoid (phân loại nhị phân).

4. **Batch Normalization**: Chuẩn hóa đầu ra của mỗi tầng theo batch, giúp ổn định và tăng tốc quá trình huấn luyện, cho phép sử dụng learning rate cao hơn.

5. **Dropout**: Kỹ thuật regularization — ngẫu nhiên "tắt" một tỷ lệ neuron trong quá trình huấn luyện, chống overfitting (mô hình học thuộc lòng dữ liệu huấn luyện thay vì tổng quát hóa).

**Hệ thống phân cấp đặc trưng (Feature Hierarchy):**

Điểm mạnh cốt lõi của CNN là khả năng tự động học đặc trưng theo thứ bậc:

```
Tầng đầu (shallow):     Cạnh, góc, gradient cục bộ
         ↓
Tầng giữa (middle):     Kết cấu, họa tiết, bộ phận nhỏ
         ↓
Tầng sâu (deep):        Đối tượng hoàn chỉnh, khuôn mặt, biển số xe
```

Ví dụ: trong bài toán nhận diện biển số xe, tầng đầu học phát hiện cạnh viền biển số, tầng giữa học kết hợp cạnh thành hình chữ nhật và ký tự, tầng sâu nhận diện toàn bộ biển số với bố cục đặc trưng.

**Các kiến trúc CNN tiêu biểu trong lịch sử:**

| Kiến trúc | Năm | Đặc điểm chính | Số tầng | Tham số |
| --- | --- | --- | --- | --- |
| **LeNet-5** | 1998 | CNN đầu tiên thành công (nhận diện chữ viết tay), LeCun | 7 | ~60K |
| **AlexNet** | 2012 | Bước ngoặt ImageNet, ReLU activation, GPU training | 8 | ~60M |
| **VGG-16** | 2014 | Kiến trúc đơn giản, chỉ dùng filter 3×3, rất sâu | 16 | ~138M |
| **GoogLeNet/Inception** | 2014 | Inception module (multi-scale convolution song song) | 22 | ~7M |
| **ResNet** | 2015 | **Skip connections** (residual learning) — giải quyết vanishing gradient, cho phép mạng cực sâu | 50–152 | ~25–60M |
| **MobileNet** | 2017–2019 | **Depthwise separable convolution** — CNN nhẹ cho mobile/edge | ~28 | ~3–5M |
| **EfficientNet** | 2019 | Compound scaling (cân bằng width, depth, resolution) | ~30–80 | ~5–66M |

Trong đề tài ParkSmart, các kiến trúc CNN được sử dụng trực tiếp bao gồm: **ResNet50** (backbone cho nhận dạng tiền mặt), **MobileNetV3-Large** (backbone cho nhận dạng tiền giấy — ưu tiên hiệu năng trên CPU), và mạng CNN trong **YOLO** (backbone CSPDarknet cho object detection).

**Transfer Learning — Học chuyển giao:**

Một kỹ thuật quan trọng liên quan đến CNN là **Transfer Learning** — sử dụng mô hình đã được huấn luyện trước (pre-trained) trên tập dữ liệu lớn (thường ImageNet với 14 triệu ảnh, 1000 lớp) làm điểm khởi đầu, sau đó tinh chỉnh (fine-tune) trên tập dữ liệu nhỏ hơn cho bài toán cụ thể. Transfer Learning giải quyết hai vấn đề thực tế: (1) thiếu dữ liệu huấn luyện cho bài toán cụ thể, và (2) chi phí tính toán cao khi huấn luyện từ đầu. Trong ParkSmart, tất cả mô hình đều sử dụng Transfer Learning: YOLO pre-trained trên COCO → fine-tune trên dữ liệu biển số Việt Nam; MobileNetV3 pre-trained trên ImageNet → fine-tune cho nhận dạng tiền giấy.

### 2.2.5. Ứng dụng AI và Computer Vision trong bãi xe thông minh

Dựa trên nền tảng lý thuyết AI, Machine Learning, Deep Learning, Computer Vision, và CNN đã trình bày ở các mục 2.2.1–2.2.4, phần này trình bày cách áp dụng các kiến thức đó vào lĩnh vực bãi giữ xe thông minh — và cụ thể là trong hệ thống ParkSmart.\r

Trong lĩnh vực bãi giữ xe thông minh, Computer Vision được ứng dụng cho bốn bài toán chính:

- **Nhận diện biển số xe tự động (License Plate Recognition — LPR)**, còn gọi là ANPR (Automatic Number Plate Recognition): phát hiện vùng biển số trên hình ảnh (Object Detection), sau đó đọc các ký tự trên biển số (OCR). Đây là bài toán cốt lõi cho check-in/check-out tự động, thay thế hoàn toàn vé giấy bằng biển số xe làm định danh duy nhất.
- **Phát hiện trạng thái ô đỗ (Slot Occupancy Detection)**: sử dụng Object Detection để phát hiện phương tiện trên bản đồ bãi xe, xác định ô đỗ nào đang trống, đang có xe, từ đó cập nhật bản đồ real-time cho người dùng và nhà quản lý.
- **Quét và giải mã mã QR (QR Code Reading)**: nhận diện và giải mã mã QR booking tại cổng vào/ra, xác thực đặt chỗ trước mà không cần thao tác thủ công.
- **Nhận dạng mệnh giá tiền giấy (Banknote Recognition)**: sử dụng Image Classification để phân loại mệnh giá tiền Việt Nam từ hình ảnh camera, phục vụ thanh toán tiền mặt tại quầy thu phí.

ParkSmart tích hợp năm pipeline AI phục vụ bốn bài toán trên, sử dụng tổng cộng bốn kiến trúc mô hình Deep Learning khác nhau (YOLO — object detection, TrOCR — sequence-to-sequence OCR, MobileNetV3 — image classification, ResNet50 — image classification) kết hợp với các kỹ thuật xử lý ảnh cổ điển (phân tích không gian màu HSV, trích xuất đặc trưng kết cấu Gabor và LBP, phát hiện cạnh). Chiến lược thiết kế xuyên suốt là **xử lý dự phòng theo tầng (cascade fallback)** — mỗi pipeline có nhiều tầng xử lý, khi tầng trước thất bại thì tầng sau tiếp quản — đảm bảo hệ thống vẫn hoạt động ngay cả trong điều kiện không lý tưởng (ánh sáng yếu, biển số mờ, camera rung).

Các mục tiếp theo trình bày lần lượt từng công nghệ AI/CV được sử dụng: YOLO (object detection), TrOCR (optical character recognition), MobileNetV3 (image classification), OpenCV (xử lý ảnh), và kiến trúc tổng thể của các pipeline.

### 2.2.6. YOLO — Phát hiện đối tượng thời gian thực

**YOLO (You Only Look Once)** là kiến trúc mạng nơ-ron phát hiện đối tượng (object detection) thuộc nhóm **one-stage detector** — phát hiện vị trí và phân loại đối tượng chỉ trong một lần chạy qua mạng (single forward pass), thay vì hai bước tách biệt như các phương pháp truyền thống. Ý tưởng cốt lõi: chia hình ảnh đầu vào thành lưới ô vuông (grid), mỗi ô dự đoán đồng thời bounding box (vị trí, kích thước) và xác suất thuộc từng lớp đối tượng — tất cả trong một lần tính toán duy nhất.

YOLO được giới thiệu lần đầu vào năm 2016 bởi Joseph Redmon và cộng sự tại Đại học Washington [10], đánh dấu bước đột phá trong object detection thời gian thực. Kiến trúc YOLO đã trải qua nhiều phiên bản cải tiến: YOLOv1 (2016) → YOLOv2/YOLO9000 (2017) → YOLOv3 (2018, thêm multi-scale detection) → YOLOv4 (2020, Alexey Bochkovskiy) → YOLOv5 (2020, Ultralytics — phiên bản đầu tiên trên framework PyTorch thuần, dễ fine-tune) → YOLOv8 (2023, Ultralytics — thiết kế không cần neo (anchor-free), cải thiện accuracy đáng kể) → YOLO11 (2024, Ultralytics — phiên bản mới nhất với kiến trúc tối ưu hơn). Từ YOLOv5 trở đi, công ty Ultralytics đã phát triển framework chuẩn hóa cho YOLO [9], cung cấp CLI và Python API thống nhất cho training, fine-tuning, inference, và export mô hình.

Một đặc điểm quan trọng của YOLO hiện đại là hệ thống **variant theo kích thước**: mỗi phiên bản có nhiều biến thể từ nano (n), small (s), medium (m), large (l) đến extra-large (x) — cùng kiến trúc nhưng khác nhau về số lượng tham số. Biến thể nano (~6MB, ~3 triệu tham số) được thiết kế cho thiết bị biên (edge devices) và ứng dụng yêu cầu tốc độ cao, trong khi biến thể extra-large (~130MB) cho độ chính xác tối đa. Sự linh hoạt này cho phép chọn mô hình phù hợp với ràng buộc phần cứng cụ thể.

**ParkSmart sử dụng ba mô hình YOLO cho ba bài toán khác nhau:**

1. **YOLOv8 fine-tuned** cho phát hiện biển số xe: Mô hình YOLOv8 được tinh chỉnh (fine-tuned) trên tập dữ liệu biển số xe Việt Nam, chuyên phát hiện vùng chứa biển số trong ảnh chụp từ camera. Sau khi phát hiện, vùng biển số được cắt ra và chuyển sang bước OCR để đọc ký tự. File mô hình: license-plate-finetune-v1m.pt.
2. **YOLO11n (nano)** cho phát hiện trạng thái ô đỗ: Biến thể nano của YOLO phiên bản 11, được sử dụng để phát hiện các phương tiện (xe hơi, xe máy, xe buýt, xe tải) trên hình ảnh bản đồ bãi xe. Kết quả phát hiện được so khớp với bounding box của từng ô đỗ đã đăng ký để xác định ô nào đang có xe, ô nào trống.
3. **YOLOv8n (nano)** cho phát hiện vùng tiền giấy: Bước đầu tiên trong pipeline nhận dạng tiền mặt — phát hiện và cắt vùng chứa tờ tiền từ ảnh camera trước khi chuyển sang bước phân loại mệnh giá.

Cả ba mô hình đều chạy trên framework Ultralytics phiên bản 8.4.18, với cấu hình chung: ngưỡng tin cậy (confidence threshold) 0.25 — chỉ giữ lại phát hiện có độ tin cậy từ 25% trở lên, và ngưỡng IoU (Intersection over Union) 0.15 — loại bỏ các bounding box trùng lặp qua Non-Maximum Suppression.

**Lý do chọn YOLO — So sánh với các kiến trúc object detection khác:**

| Tiêu chí                  | YOLO (v8/11)        | SSD             | Faster R-CNN | DETR        |
| ------------------------- | ------------------- | --------------- | ------------ | ----------- |
| Tốc độ inference          | ⭐⭐⭐⭐⭐          | ⭐⭐⭐⭐        | ⭐⭐         | ⭐⭐⭐      |
| Độ chính xác (mAP)        | ⭐⭐⭐⭐            | ⭐⭐⭐          | ⭐⭐⭐⭐⭐   | ⭐⭐⭐⭐    |
| Khả năng chạy real-time   | ✅                  | ✅              | ❌           | ❌          |
| Dễ dàng fine-tune         | ⭐⭐⭐⭐⭐          | ⭐⭐⭐          | ⭐⭐         | ⭐⭐        |
| Kích thước mô hình (nano) | ~6 MB               | Trung bình      | Lớn          | Lớn         |
| Framework hỗ trợ          | Ultralytics CLI/API | Nhiều framework | Detectron2   | HuggingFace |

- **SSD (Single Shot MultiBox Detector)**: Cũng là one-stage detector, tốc độ tốt nhưng accuracy thấp hơn YOLO v8+ trên hầu hết benchmark, và không có ecosystem fine-tuning tiện lợi như Ultralytics.
- **Faster R-CNN**: Two-stage detector (Region Proposal Network + classifier), accuracy cao nhất nhưng chậm gấp 5–10 lần YOLO — không phù hợp cho xử lý video stream real-time từ camera bãi xe.
- **DETR (Detection Transformer)**: Kiến trúc dựa trên Transformer của Facebook AI, loại bỏ hoàn toàn anchor boxes, nhưng inference chậm hơn YOLO và yêu cầu tài nguyên GPU lớn hơn.

ParkSmart chọn YOLO vì ba yếu tố quyết định: **(1)** yêu cầu xử lý real-time từ camera stream — mỗi frame cần được phân tích trong vài chục millisecond; **(2)** biến thể nano cho phép chạy trên server không có GPU chuyên dụng mạnh; **(3)** Ultralytics framework cung cấp quy trình fine-tune đơn giản — chỉ cần chuẩn bị dataset theo chuẩn và chạy một lệnh, không cần viết training loop thủ công.

### 2.2.7. TrOCR — Nhận dạng ký tự quang học bằng Transformer

**TrOCR (Transformer-based Optical Character Recognition)** là mô hình nhận dạng ký tự quang học do Microsoft Research phát triển [11], sử dụng kiến trúc Transformer end-to-end cho bài toán đọc chữ từ hình ảnh. Khác với phương pháp OCR truyền thống phải tách riêng từng bước (phát hiện dòng text → phân đoạn ký tự → nhận dạng từng ký tự → ghép lại), TrOCR thực hiện toàn bộ quy trình trong một mạng nơ-ron duy nhất: nhận đầu vào là ảnh chứa text, trả đầu ra trực tiếp là chuỗi ký tự.

Kiến trúc TrOCR gồm hai thành phần chính: **Vision Encoder** dựa trên Vision Transformer (ViT) — chia ảnh đầu vào thành các patch nhỏ, mã hóa thành chuỗi embedding biểu diễn nội dung hình ảnh; và **Text Decoder** theo kiến trúc tương tự GPT-2 — sinh ra từng ký tự một cách tuần tự (autoregressive) dựa trên biểu diễn hình ảnh từ encoder. Mô hình được huấn luyện trước (pre-trained) trên hàng triệu cặp ảnh-text, sau đó có thể fine-tune cho domain cụ thể. Microsoft cung cấp nhiều phiên bản trên HuggingFace: trocr-small-printed, trocr-base-printed, trocr-large-printed (cho chữ in), và các phiên bản handwritten (cho chữ viết tay).

**ParkSmart sử dụng mô hình microsoft/trocr-base-printed** (phiên bản base, tối ưu cho chữ in — phù hợp với font chữ trên biển số xe) làm bộ đọc ký tự chính (Priority #1) trong pipeline nhận diện biển số. Sau khi YOLO phát hiện và cắt ra vùng biển số, ảnh biển số được đưa vào TrOCR để đọc chuỗi ký tự. Mô hình được tải từ kho HuggingFace và chạy inference thông qua thư viện Transformers.

- **Ưu điểm**: Accuracy cao cho printed text nhờ pre-training trên dữ liệu lớn; kiến trúc end-to-end loại bỏ bước phân đoạn ký tự (character segmentation) — vốn rất khó với biển số bị nghiêng, mờ, hoặc bị che một phần; khả năng fine-tune cho font chữ đặc thù (biển số Việt Nam).
- **Nhược điểm**: Chậm hơn đáng kể so với OCR dựa trên luật (rule-based OCR) hoặc các engine nhẹ — do kiến trúc Transformer với hàng triệu tham số cần nhiều phép tính hơn; yêu cầu GPU cho inference nhanh (trên CPU, mỗi ảnh biển số mất khoảng 1–3 giây).

**Lý do chọn TrOCR — So sánh với các phương pháp OCR khác:**

| Tiêu chí                    | TrOCR                        | Tesseract               | EasyOCR        | PaddleOCR      |
| --------------------------- | ---------------------------- | ----------------------- | -------------- | -------------- |
| Kiến trúc                   | Transformer (end-to-end)     | Rule-based + LSTM       | CRAFT + CRNN   | Nhiều pipeline |
| Độ chính xác (printed text) | ⭐⭐⭐⭐⭐                   | ⭐⭐⭐                  | ⭐⭐⭐⭐       | ⭐⭐⭐⭐       |
| Tốc độ (CPU)                | Chậm (~1–3s/ảnh)             | Nhanh                   | Trung bình     | Trung bình     |
| Tốc độ (GPU)                | Nhanh (~0.1–0.3s/ảnh)        | Không hỗ trợ GPU        | Nhanh          | Nhanh          |
| Pre-trained models          | HuggingFace (nhiều ngôn ngữ) | Nhiều ngôn ngữ          | Nhiều ngôn ngữ | Nhiều ngôn ngữ |
| Yêu cầu fine-tune           | Thấp (pre-trained tốt)       | Cao (cần training data) | Trung bình     | Trung bình     |

- **Tesseract**: Engine OCR mã nguồn mở lâu đời nhất (HP, 1985; Google duy trì từ 2006). Nhanh, nhẹ, chạy hoàn toàn trên CPU, nhưng accuracy thấp hơn với ảnh biển số chất lượng kém (nghiêng, mờ, ánh sáng không đều). Trong ParkSmart, Tesseract đóng vai trò **fallback cuối cùng** (Priority #3) khi cả TrOCR và EasyOCR đều không trả về kết quả tin cậy.
- **EasyOCR**: Thư viện OCR dựa trên deep learning (CRAFT text detector + CRNN recognizer), hỗ trợ hơn 80 ngôn ngữ. Cân bằng giữa accuracy và tốc độ, chạy được trên CPU với thời gian chấp nhận được. Trong ParkSmart, EasyOCR phiên bản 1.7.2 đóng vai trò **fallback thứ hai** (Priority #2) — được gọi khi TrOCR không khả dụng hoặc trả về kết quả không đạt ngưỡng tin cậy.
- **PaddleOCR**: Thư viện OCR của Baidu, hiệu năng tốt, nhưng hệ sinh thái phụ thuộc PaddlePaddle framework — thêm dependency lớn bên cạnh PyTorch đã dùng cho YOLO và MobileNetV3.

Chiến lược **cascade fallback** (TrOCR → EasyOCR → Tesseract) đảm bảo reliability tối đa: TrOCR cho accuracy cao nhất khi điều kiện lý tưởng; EasyOCR tiếp quản khi TrOCR gặp vấn đề; Tesseract là "lưới an toàn" cuối cùng — nhẹ nhất, nhanh nhất, luôn trả về kết quả (dù accuracy thấp hơn). Sau khi bất kỳ engine nào trả về kết quả, hệ thống áp dụng bước hậu xử lý: kiểm tra chuỗi ký tự có khớp định dạng biển số Việt Nam hay không (regex pattern matching), cho phép fuzzy matching với ngưỡng tối đa 3 ký tự sai.

### 2.2.8. MobileNetV3 — Kiến trúc CNN tối ưu cho thiết bị di động

**MobileNetV3** là kiến trúc mạng nơ-ron tích chập nhẹ (lightweight CNN) do Google phát triển và công bố năm 2019 [12], được thiết kế đặc biệt cho thiết bị di động và biên (mobile/edge devices) với ràng buộc tài nguyên tính toán hạn chế. MobileNetV3 kế thừa và cải tiến hai phiên bản trước (MobileNetV1 với depthwise separable convolution, MobileNetV2 với inverted residual blocks) bằng cách kết hợp hai kỹ thuật tối ưu: **Neural Architecture Search (NAS)** — thuật toán tự động tìm kiến trúc mạng tối ưu trên không gian thiết kế rộng, và **NetAdapt** — thuật toán tinh chỉnh từng layer để đạt target latency trên thiết bị đích. Kết quả là mô hình đạt accuracy gần bằng các mạng lớn (ResNet, EfficientNet) nhưng với số lượng tham số và phép tính (FLOPs) ít hơn nhiều lần.

MobileNetV3 có hai biến thể chính: **Large** (cho ứng dụng cần accuracy cao, ~5.4 triệu tham số) và **Small** (cho ứng dụng cần tốc độ tối đa, ~2.5 triệu tham số). Cả hai đều được pre-trained trên tập ImageNet (1.000 lớp đối tượng, hơn 1.2 triệu ảnh) và có thể được sử dụng làm **bộ trích xuất đặc trưng (feature extractor)** — lấy phần backbone đã học được biểu diễn hình ảnh tổng quát, thay thế lớp phân loại cuối cùng bằng lớp mới phù hợp với bài toán cụ thể. Kỹ thuật này gọi là **Transfer Learning** (học chuyển giao) — tận dụng kiến thức đã học từ tập dữ liệu lớn để giải quyết bài toán mới với lượng dữ liệu huấn luyện nhỏ hơn nhiều.

**ParkSmart sử dụng MobileNetV3-Large trong kiến trúc đa nhánh (multi-branch)** cho bài toán phân loại mệnh giá tiền giấy Việt Nam. Thay vì chỉ dựa vào đặc trưng từ CNN (vốn tốt cho hình dạng, màu sắc tổng thể nhưng có thể bỏ sót chi tiết kết cấu bề mặt), hệ thống kết hợp nhiều nguồn đặc trưng:

- **Nhánh 1 — CNN backbone (MobileNetV3-Large)**: Trích xuất đặc trưng hình ảnh tổng quát từ layer trước lớp phân loại, cho vector 960 chiều biểu diễn nội dung hình ảnh ở mức ngữ nghĩa cao (high-level semantic features).
- **Nhánh 2 — Đặc trưng kết cấu Gabor (24 chiều)**: Bộ lọc Gabor mô phỏng cách hệ thống thị giác sinh học phản ứng với các vân kết cấu ở nhiều hướng và tần số khác nhau — phát hiện các hoa văn in ấn đặc trưng trên mỗi mệnh giá tiền.
- **Nhánh 3 — Đặc trưng vi kết cấu LBP (10 chiều)**: Local Binary Pattern (LBP) mô tả mối quan hệ cường độ pixel giữa điểm trung tâm và các điểm lân cận — nhận diện các chi tiết nhỏ trên bề mặt tiền giấy khó thấy bằng mắt thường.
- **Nhánh 4 — Đặc trưng cấu trúc cạnh (36 chiều)**: Phân tích phân bố hướng cạnh (edge orientation histogram) — nhận diện đường viền, khung, và các yếu tố đồ họa cấu trúc của mỗi mệnh giá.

Bốn nhánh đặc trưng được **tổng hợp (fusion)** thành vector duy nhất: 960 (CNN) + 24 (Gabor) + 10 (LBP) + 36 (Edge) = 1.030 chiều gốc, qua các lớp chiếu (projection layers) thành vector 1.088 chiều, đưa vào bộ phân loại cuối cùng (fully-connected layers) để xác định mệnh giá tiền. Ngoài MobileNetV3 dùng trong inference, ParkSmart còn sử dụng **ResNet50** [13] (mạng residual 50 lớp, pre-trained trên ImageNet) trong pipeline huấn luyện (training pipeline) cho bài toán nhận dạng tiền mặt — ResNet50 có accuracy cao hơn MobileNetV3 nhưng nặng hơn, phù hợp cho giai đoạn training offline.

**Lý do chọn MobileNetV3 — So sánh với các kiến trúc CNN phân loại ảnh:**

| Tiêu chí                  | MobileNetV3-Large | EfficientNet-B0 | ResNet50    | VGG16      |
| ------------------------- | ----------------- | --------------- | ----------- | ---------- |
| Số tham số                | ~5.4 triệu        | ~5.3 triệu      | ~25.6 triệu | ~138 triệu |
| Kích thước mô hình        | ~22 MB            | ~20 MB          | ~98 MB      | ~528 MB    |
| Top-1 Accuracy (ImageNet) | 75.2%             | 77.1%           | 76.1%       | 71.6%      |
| Tốc độ inference (CPU)    | ⭐⭐⭐⭐⭐        | ⭐⭐⭐⭐        | ⭐⭐⭐      | ⭐⭐       |
| Thiết kế cho mobile/edge  | ✅                | ✅              | ❌          | ❌         |
| Depthwise separable conv  | ✅                | ✅              | ❌          | ❌         |

- **EfficientNet**: Accuracy cao hơn một chút, nhưng MobileNetV3 được tối ưu đặc biệt cho latency thấp trên CPU — phù hợp hơn cho server không có GPU mạnh.
- **ResNet50**: Accuracy tương đương nhưng nặng gấp ~5 lần — phù hợp cho training nhưng không lý tưởng cho inference thường xuyên trên server với tài nguyên hạn chế.
- **VGG16**: Kiến trúc cũ (2014), nặng nhất, accuracy thấp nhất trong nhóm — không phù hợp cho deployment hiện đại.

Thiết kế multi-branch kết hợp deep features (CNN) với handcrafted features (Gabor, LBP, Edge) giúp mô hình robust hơn so với chỉ dùng CNN đơn thuần — đặc biệt quan trọng khi phân loại tiền giấy Việt Nam có nhiều mệnh giá cùng kích thước nhưng khác biệt tinh tế về hoa văn, kết cấu bề mặt, và phân bố màu sắc.

### 2.2.9. OpenCV — Thư viện xử lý ảnh nền tảng

**OpenCV (Open Source Computer Vision Library)** là thư viện xử lý ảnh và thị giác máy tính mã nguồn mở phổ biến nhất thế giới, được khởi tạo bởi Intel Research (Gary Bradski) vào năm 1999 và phát hành phiên bản đầu tiên năm 2000 dưới giấy phép BSD. Trải qua hơn 25 năm phát triển với sự đóng góp từ cộng đồng toàn cầu (hơn 2.500 thuật toán tối ưu), OpenCV đã trở thành nền tảng không thể thiếu cho hầu hết mọi ứng dụng computer vision — từ nghiên cứu học thuật đến sản phẩm thương mại [24]. Thư viện hỗ trợ nhiều ngôn ngữ (C++, Python, Java, JavaScript), trong đó Python binding là phổ biến nhất nhờ sự gọn nhẹ của cú pháp.

Trong ParkSmart, OpenCV phiên bản 4.10.0.84 (biến thể headless — không cần GUI, tối ưu cho server) đóng vai trò **nền tảng xử lý ảnh** xuyên suốt tất cả các pipeline AI, thực hiện nhiều chức năng thiết yếu:

- **Tiền xử lý ảnh (Image Preprocessing)**: Chuyển đổi không gian màu (BGR sang HSV, RGB sang grayscale), cân bằng sáng (white balance), giảm nhiễu, resize ảnh về kích thước chuẩn trước khi đưa vào mô hình AI — đảm bảo đầu vào nhất quán dù ảnh gốc từ nhiều nguồn camera khác nhau.
- **Quét và giải mã mã QR**: Sử dụng bộ giải mã QR tích hợp sẵn trong OpenCV để đọc mã QR booking tại cổng vào/ra — nhanh, nhẹ, không cần mô hình AI riêng.
- **Chuyển đổi không gian màu HSV**: Phân tích phân bố màu sắc của tiền giấy trong không gian HSV (Hue-Saturation-Value) — bước đầu tiên trong pipeline nhận dạng tiền mặt, cho phép phân loại nhanh dựa trên màu sắc đặc trưng của mỗi mệnh giá mà không cần gọi mô hình AI (giảm tải tính toán).
- **Trích xuất đặc trưng kết cấu**: Tính toán bộ lọc Gabor, LBP, và histogram hướng cạnh — cung cấp đặc trưng thủ công (handcrafted) cho các nhánh phụ của mô hình phân loại tiền giấy MobileNetV3 multi-branch.
- **Thu nhận khung hình từ camera**: Kết nối và đọc video stream từ camera IP qua giao thức RTSP (camera EZVIZ) và HTTP (DroidCam trên điện thoại) — cung cấp ảnh đầu vào cho toàn bộ pipeline xử lý.

OpenCV không phải mô hình AI — nó là tầng xử lý ảnh cơ sở (image processing layer) mà tất cả các mô hình AI trong hệ thống đều phụ thuộc vào: YOLO cần OpenCV để đọc ảnh và resize, TrOCR cần OpenCV để cắt vùng biển số, MobileNetV3 cần OpenCV để trích xuất texture features. Sự kết hợp giữa kỹ thuật xử lý ảnh cổ điển (OpenCV) và deep learning hiện đại (YOLO, TrOCR, MobileNetV3) phản ánh xu hướng thiết kế AI pipeline thực tế — không hoàn toàn "end-to-end deep learning" mà kết hợp linh hoạt giữa hai paradigm để đạt hiệu quả tối ưu.

### 2.2.10. Kiến trúc AI/Computer Vision Pipeline

Một hệ thống AI/Computer Vision hoàn chỉnh được tổ chức thành các **pipeline** — chuỗi xử lý tuần tự biến đổi dữ liệu thô (ảnh, video) thành kết quả có ý nghĩa (nhận dạng, phân loại, đọc chữ). Phần này trình bày kiến trúc pipeline tổng quát trong lĩnh vực thị giác máy tính.

**Computer Vision Pipeline tổng quát**

Mọi ứng dụng CV đều tuân theo luồng xử lý cơ bản:

```
Input            Preprocessing       Detection/         Recognition/       Postprocessing     Output
(Camera/Image) → (Resize, Normalize, → Segmentation    → Classification  → (NMS, Filtering, → (Kết quả
                  Color Convert,       (Tìm vùng         (Hiểu nội dung     Validation,        cuối cùng)
                  Denoise)             quan tâm - ROI)    vùng ROI)          Format)
```

- **Preprocessing**: chuẩn hóa đầu vào — resize về kích thước chuẩn cho model, chuyển đổi không gian màu (BGR → RGB, HSV), cân bằng sáng, giảm nhiễu. Bước này đảm bảo model nhận input nhất quán dù ảnh gốc từ nhiều nguồn khác nhau.
- **Detection/Segmentation**: xác định vùng quan tâm (Region of Interest — ROI) trong ảnh — bounding box quanh đối tượng (detection) hoặc mask pixel-level (segmentation).
- **Recognition/Classification**: hiểu nội dung vùng ROI — đọc ký tự (OCR), phân loại đối tượng thuộc category nào, hoặc nhận diện danh tính.
- **Postprocessing**: lọc và tinh chỉnh kết quả — Non-Maximum Suppression (NMS) loại bounding box trùng, confidence thresholding, format validation, business logic filtering.

Trong thực tế, nhiều bài toán CV sử dụng mô hình **2 giai đoạn (two-stage)**: giai đoạn 1 detect/crop vùng quan tâm, giai đoạn 2 phân tích chi tiết vùng đó — ví dụ: detect biển số (stage 1) → đọc ký tự trên biển số (stage 2).

**Training Pipeline vs Inference Pipeline**

Hai pipeline riêng biệt phục vụ hai mục đích khác nhau:

- **Training Pipeline**: Thu thập dữ liệu → Gán nhãn (annotation) → Tăng cường dữ liệu (augmentation — lật, xoay, thay đổi sáng/tương phản để tăng đa dạng) → Huấn luyện model (forward + backward + weight update) → Đánh giá trên tập validation → Export model (ONNX, TorchScript, CoreML). **Transfer learning** là workflow phổ biến: lấy model pre-trained trên dataset lớn (ImageNet, COCO), thay lớp classification cuối, fine-tune trên dataset nhỏ chuyên biệt — tiết kiệm thời gian và dữ liệu huấn luyện.
- **Inference Pipeline**: Load model đã export → Preprocess input → Forward pass (chỉ tính toán, không cập nhật weight) → Postprocess output → Trả kết quả. Inference pipeline yêu cầu tối ưu latency và throughput — áp dụng kỹ thuật batch processing, model quantization (giảm precision từ FP32 → FP16/INT8), và hardware acceleration (GPU, TensorRT).

**Object Detection Paradigm**

Hai trường phái chính trong phát hiện đối tượng:

- **One-stage detectors** (YOLO, SSD, RetinaNet): xử lý ảnh trong một lần forward pass duy nhất — chia ảnh thành grid, dự đoán đồng thời bounding box và class probability tại mỗi cell. Ưu điểm: tốc độ nhanh (real-time capable). Nhược điểm: accuracy thấp hơn trên đối tượng nhỏ.
- **Two-stage detectors** (Faster R-CNN, Mask R-CNN): stage 1 sinh region proposals (vùng có khả năng chứa đối tượng), stage 2 phân loại và tinh chỉnh bounding box từng proposal. Ưu điểm: accuracy cao hơn. Nhược điểm: chậm hơn 5–10 lần, không phù hợp real-time.
- **Non-Maximum Suppression (NMS)**: bước postprocessing bắt buộc — khi detector sinh nhiều bounding box trùng lặp cho cùng một đối tượng, NMS loại bỏ box có confidence thấp hơn nếu IoU (Intersection over Union) với box confidence cao vượt ngưỡng.

**OCR Pipeline (Optical Character Recognition)**

OCR chuyển đổi hình ảnh chứa chữ thành chuỗi ký tự số, gồm hai cách tiếp cận:

- **Modular approach**: Text Detection (tìm vùng chứa chữ trong ảnh, ví dụ: CRAFT, EAST) → Text Recognition (đọc ký tự từ vùng đã crop, ví dụ: CRNN, Tesseract). Mỗi module tối ưu độc lập.
- **End-to-end approach**: Một model duy nhất nhận ảnh và trả ra chuỗi ký tự (ví dụ: TrOCR sử dụng Vision Transformer encoder + Text Transformer decoder). Đơn giản hóa pipeline nhưng yêu cầu model lớn hơn.

**Model Serving Patterns**

Các pattern phổ biến khi triển khai nhiều model AI:

- **Cascade/Fallback**: chạy model chính trước, nếu confidence thấp hoặc thất bại → chuyển sang model dự phòng. Ưu tiên reliability — hệ thống luôn trả kết quả trong mọi điều kiện.
- **Ensemble**: chạy song song nhiều model, kết hợp kết quả (voting, averaging) để tăng accuracy. Tốn tài nguyên hơn nhưng robust hơn.
- **Pipeline Chaining**: output model A là input model B — ví dụ: detection model crop vùng → recognition model đọc nội dung. Mô hình multi-stage phổ biến nhất trong CV thực tế.

### 2.2.11. Các kỹ thuật chính

Bên cạnh các mô hình và kiến trúc pipeline đã trình bày, ParkSmart áp dụng sáu kỹ thuật AI/CV cốt lõi xuyên suốt hệ thống:

- **Fine-tuning (Tinh chỉnh mô hình)**: Kỹ thuật transfer learning — lấy mô hình đã pre-trained trên tập dữ liệu lớn tổng quát, huấn luyện thêm trên tập dữ liệu nhỏ chuyên biệt để thích ứng với domain cụ thể. ParkSmart fine-tune YOLO cho biển số xe Việt Nam (khác biệt về font, kích thước, định dạng so với biển số quốc tế) và MobileNetV3 cho tiền giấy Việt Nam (8 mệnh giá với đặc điểm hình ảnh riêng).
- **Cascade fallback pattern**: Chuỗi nhiều phương pháp xử lý theo thứ tự ưu tiên — phương pháp chính xác nhất chạy trước, nếu thất bại thì phương pháp dự phòng tiếp quản. Pattern này được áp dụng nhất quán trong OCR (TrOCR → EasyOCR → Tesseract) và nhận dạng tiền (màu sắc → AI model), đảm bảo hệ thống luôn trả về kết quả trong mọi điều kiện.
- **IoU matching (Intersection over Union)**: Phương pháp đo mức độ trùng khớp giữa hai bounding box bằng cách tính tỷ lệ diện tích giao nhau chia cho diện tích hợp nhất. Giá trị IoU nằm trong khoảng 0 (không trùng) đến 1 (trùng hoàn toàn). Trong phát hiện trạng thái ô đỗ, IoU so khớp bounding box phương tiện phát hiện bởi YOLO với bounding box ô đỗ đã đăng ký, ngưỡng 0.15 đủ nhạy để phát hiện xe đỗ lệch tâm.
- **Multi-branch feature fusion**: Kỹ thuật kết hợp đặc trưng từ nhiều nguồn khác nhau — thay vì chỉ dựa vào một loại đặc trưng (CNN hoặc đặc trưng thủ công), mô hình tổng hợp đặc trưng từ cả deep learning (CNN backbone 960 chiều) và kỹ thuật xử lý ảnh cổ điển (Gabor 24 chiều + LBP 10 chiều + Edge 36 chiều) thành vector duy nhất, cho mô hình phân loại cuối cùng "nhìn" được nhiều khía cạnh khác nhau của hình ảnh.
- **Vietnamese plate format validation**: Hậu xử lý đặc thù cho biển số Việt Nam — kiểm tra chuỗi ký tự OCR có khớp với các mẫu biển số hợp lệ (biển xe máy, biển ô tô, biển ngoại giao) bằng regex pattern matching, kết hợp fuzzy matching cho phép tối đa 3 ký tự sai — bù đắp cho sai số OCR trong điều kiện ảnh kém.
- **HSV color analysis**: Phân tích phân bố màu sắc trong không gian HSV (Hue — sắc độ, Saturation — bão hòa, Value — độ sáng) trước khi gọi mô hình AI — bước lọc nhanh giúp phân loại ngay các trường hợp dễ (tiền mệnh giá có màu sắc đặc trưng rõ rệt) mà không cần inference AI tốn kém, giảm tải tính toán cho server.

**Ba pipeline AI cụ thể trong hệ thống ParkSmart:**

- **Pipeline nhận diện biển số (Plate Recognition)**: YOLO fine-tuned phát hiện vùng biển số → OCR cascade (TrOCR → EasyOCR → Tesseract) đọc ký tự → hậu xử lý chuẩn hóa (loại ký tự đặc biệt, chuyển chữ hoa) → xác thực định dạng biển số Việt Nam (regex + fuzzy matching tối đa 3 ký tự sai).
- **Pipeline phát hiện trạng thái ô đỗ (Slot Detection)**: YOLO11n phát hiện phương tiện trên ảnh bản đồ bãi xe → so khớp IoU giữa bounding box phương tiện và bounding box ô đỗ đã đăng ký (ngưỡng IoU ≥ 0.15) → cập nhật trạng thái "có xe" / "trống" real-time.
- **Pipeline nhận dạng tiền giấy (Banknote Recognition)**: Tiền xử lý + YOLOv8n phát hiện vùng tiền → phân loại nhanh bằng phân tích màu HSV → nếu không đủ tin cậy, chuyển sang MobileNetV3 multi-branch (CNN + Gabor + LBP + Edge features). Chiến lược "color-first, AI-second" giúp ~70–80% trường hợp được giải quyết nhanh mà không cần AI inference.

### 2.2.12. Ưu và nhược điểm tổng thể của giải pháp AI/CV

**Ưu điểm:**

- **Đa dạng pipeline, cascade fallback đảm bảo reliability**: Năm pipeline AI phục vụ bốn bài toán khác nhau, mỗi pipeline có cơ chế dự phòng đa tầng — hệ thống không phụ thuộc vào bất kỳ mô hình đơn lẻ nào, giảm thiểu rủi ro thất bại hoàn toàn.
- **Mô hình nano cho xử lý thời gian thực**: Biến thể nano của YOLO (chỉ ~6MB) đủ nhanh để phân tích từng frame từ camera stream mà không cần GPU chuyên dụng — phù hợp với hạ tầng server phổ thông.
- **Tiếp cận đa phương thức (multi-modal)**: Kết hợp nhiều kênh thông tin — hình ảnh (CNN features), màu sắc (HSV histogram), kết cấu bề mặt (Gabor, LBP), cấu trúc cạnh (edge histogram) — giúp mô hình robust hơn so với chỉ dựa vào một nguồn đặc trưng duy nhất.
- **Mô hình đã huấn luyện sẵn giảm yêu cầu dữ liệu huấn luyện**: Tất cả mô hình đều khởi đầu từ trọng số được huấn luyện sẵn trên tập dữ liệu lớn (ImageNet, COCO, text corpus) — chỉ cần lượng nhỏ dữ liệu chuyên biệt (biển số VN, tiền VN) để fine-tune, không cần xây dựng dataset hàng triệu mẫu từ đầu.

**Nhược điểm và cách khắc phục:**

- **Phụ thuộc chất lượng camera và điều kiện ánh sáng**: Mô hình AI hoạt động tốt nhất khi ảnh đầu vào rõ nét, đủ sáng — trong điều kiện ánh sáng yếu, ngược sáng, hoặc camera mờ, accuracy giảm đáng kể. → _Khắc phục_: Pipeline tiền xử lý ảnh (cân bằng sáng, giảm nhiễu) kết hợp cascade fallback nhiều engine — nếu engine chính không đọc được, engine phụ với thuật toán khác có thể bù đắp.
- **TrOCR yêu cầu GPU cho inference nhanh**: Trên CPU, TrOCR xử lý mỗi ảnh biển số mất 1–3 giây — chấp nhận được cho xe vào lẻ nhưng gây chậm khi nhiều xe cùng lúc. → _Khắc phục_: Cascade fallback sang EasyOCR (nhanh hơn trên CPU, accuracy vẫn khá) hoặc Tesseract (nhanh nhất) khi cần throughput cao; trên server có GPU, TrOCR chạy chỉ ~0.1–0.3 giây/ảnh.
- **Dữ liệu huấn luyện biển số Việt Nam còn hạn chế**: Biển số Việt Nam có nhiều biến thể (cũ/mới, xe máy/ô tô, biển vàng/xanh/đỏ) và chưa có tập dữ liệu chuẩn công khai quy mô lớn, khiến mô hình fine-tuned có thể gặp khó với biến thể chưa thấy trong training set. → _Khắc phục_: Fuzzy matching cho phép tối đa 3 ký tự sai trong kết quả OCR so với mẫu biển số hợp lệ — tăng recall mà không cần training data hoàn hảo; kết hợp Vietnamese plate format validation để loại bỏ false positive.
- **Quản lý phiên bản mô hình (model versioning) phức tạp**: Hệ thống sử dụng nhiều file mô hình AI (YOLO, MobileNetV3, ResNet50 weights) cần được đồng bộ đúng phiên bản giữa môi trường phát triển và sản xuất, và cần cập nhật khi re-train. → _Khắc phục_: Các file mô hình được tách riêng khỏi mã nguồn, deploy qua Docker volume mount — cho phép cập nhật mô hình mà không cần rebuild Docker image; đặt tên file có version tag để tránh nhầm lẫn.

---

## 2.3. Internet of Things (IoT)

### 2.3.1. Giới thiệu Internet of Things

Internet of Things (IoT — Internet Vạn Vật) là khái niệm chỉ mạng lưới các thiết bị vật lý được nhúng cảm biến, phần mềm, và công nghệ kết nối mạng, cho phép chúng thu thập và trao đổi dữ liệu với nhau cùng hệ thống trung tâm qua Internet. Thuật ngữ "Internet of Things" được đặt ra bởi **Kevin Ashton** vào năm **1999** tại Viện Công nghệ Massachusetts (MIT), trong bối cảnh nghiên cứu về RFID và chuỗi cung ứng.

Trong lĩnh vực bãi xe thông minh (Smart Parking), IoT đóng vai trò **cầu nối** giữa thế giới vật lý (barrier, camera, cảm biến, nút nhấn) và hệ thống phần mềm (server, AI, database). Thay vì con người trực tiếp vận hành từng thao tác (kiểm tra vé, mở barrier, ghi sổ), các thiết bị IoT tự động thu thập thông tin, gửi dữ liệu lên server để xử lý bằng AI, và thực thi hành động vật lý — toàn bộ quy trình diễn ra tự động trong vài giây.

**Danh sách thiết bị IoT trong hệ thống ParkSmart:**

| Thiết bị                      | Vai trò trong hệ thống                                                                                                 |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------------------- |
| **ESP32 DevKit V1**           | IoT Gateway — kết nối WiFi, gửi HTTP request đến AI server, nhận response, điều phối luồng check-in/out, hiển thị OLED |
| **Arduino Uno R3**            | Barrier Controller — nhận lệnh từ ESP32 qua UART, điều khiển 2 servo barrier (cổng vào + cổng ra)                      |
| **Servo Motor (SG90/MG996R)** | Mở/đóng barrier (thanh chắn) tại cổng vào và cổng ra                                                                   |
| **Camera DroidCam**           | Thu hình phục vụ quét mã QR booking (WiFi streaming từ smartphone)                                                     |
| **Camera EZVIZ (RTSP)**       | Thu hình biển số xe phục vụ OCR nhận dạng (camera IP outdoor)                                                          |
| **OLED SSD1306 (128×64px)**   | Hiển thị biển số nhận dạng, trạng thái check-in/out, thông báo hệ thống                                                |
| **Nút nhấn (Push Button)**    | Trigger thao tác check-in hoặc check-out                                                                               |
| **LED trạng thái**            | Chỉ thị: nhấp nháy = đang xử lý, sáng = thành công, tắt = idle                                                         |

Trên thế giới, IoT đang được ứng dụng rộng rãi trong Smart Parking: cảm biến siêu âm hoặc từ trường phát hiện trạng thái ô đỗ, camera AI nhận dạng biển số tại cổng, barrier tự động điều khiển bằng vi điều khiển, và bảng LED hiển thị chỗ trống. Dữ liệu từ các thiết bị được truyền về server qua WiFi, LoRa, NB-IoT, hoặc 4G/5G.

### 2.3.2. Kiến trúc hệ thống IoT

Kiến trúc hệ thống IoT được thiết kế theo nhiều mô hình tham chiếu, trong đó phổ biến nhất là **mô hình 3 lớp (Three-Layer Architecture)** — mô hình nền tảng được ITU-T và nhiều tổ chức tiêu chuẩn quốc tế áp dụng:

```
╔══════════════════════════════════════════════════════════╗
║  APPLICATION LAYER (Lớp Ứng dụng)                       ║
║  • Xử lý dữ liệu, logic nghiệp vụ                      ║
║  • Giao diện người dùng, dashboard, API                  ║
║  • AI/ML inference, analytics                            ║
╠══════════════════════════════════════════════════════════╣
║  NETWORK LAYER (Lớp Mạng)                                ║
║  • Truyền dẫn dữ liệu: WiFi, BLE, LoRa, 4G/5G          ║
║  • Giao thức: MQTT, HTTP, CoAP, AMQP                    ║
║  • IoT Gateway: chuyển đổi giao thức, tiền xử lý        ║
╠══════════════════════════════════════════════════════════╣
║  PERCEPTION LAYER (Lớp Cảm biến)                         ║
║  • Cảm biến (sensors): nhiệt độ, siêu âm, camera        ║
║  • Cơ cấu chấp hành (actuators): motor, relay, LED      ║
║  • Vi điều khiển: ESP32, Arduino, STM32, Raspberry Pi    ║
╚══════════════════════════════════════════════════════════╝
```

**Lớp Cảm biến (Perception Layer)** là tầng thấp nhất, bao gồm các thiết bị vật lý thu thập dữ liệu từ môi trường (cảm biến nhiệt độ, siêu âm, camera, gia tốc kế) và thực thi hành động vật lý (motor, relay, servo, LED). Vi điều khiển (microcontroller) đóng vai trò bộ não tại tầng này — đọc dữ liệu cảm biến, điều khiển actuator, và giao tiếp với tầng trên.

**Lớp Mạng (Network Layer)** chịu trách nhiệm truyền dẫn dữ liệu giữa thiết bị và server. Các giao thức phổ biến:

- **HTTP/HTTPS** — request-response, phù hợp cho tương tác event-driven (nhấn nút → gọi API), tương thích trực tiếp với REST API trên server.
- **MQTT** — publish-subscribe, lightweight (header chỉ 2 bytes), tối ưu cho thiết bị tài nguyên hạn chế cần gửi dữ liệu liên tục (streaming sensor data). Hỗ trợ QoS levels đảm bảo độ tin cậy.
- **CoAP (Constrained Application Protocol)** — tương tự HTTP nhưng trên UDP, thiết kế cho thiết bị cực kỳ hạn chế tài nguyên (RAM < 10KB).
- **UART / I2C / SPI** — giao thức giao tiếp cục bộ giữa các board/module trên cùng thiết bị: UART (nối tiếp, full-duplex, board-to-board), I2C (bus 2 dây, master-slave, kết nối nhiều sensor/display), SPI (tốc độ cao, full-duplex, short-distance).

**Lớp Ứng dụng (Application Layer)** xử lý dữ liệu, thực thi logic nghiệp vụ, cung cấp giao diện người dùng và API. Tầng này thường chạy trên cloud server hoặc edge server, tích hợp AI inference, database, dashboard real-time.

**IoT Gateway Pattern**

Trong thực tế, thiết bị cảm biến thường không kết nối trực tiếp đến cloud mà thông qua một **IoT Gateway** — thiết bị trung gian đặt tại biên (edge). Gateway đảm nhận:

- **Chuyển đổi giao thức (Protocol Translation)**: thiết bị giao tiếp UART/I2C/BLE với gateway, gateway chuyển thành HTTP/MQTT gửi lên cloud.
- **Tiền xử lý và lọc dữ liệu**: loại bỏ dữ liệu trùng lặp, nhiễu, chỉ gửi dữ liệu có ý nghĩa lên server — giảm băng thông và tải server.
- **Quản lý thiết bị cục bộ**: theo dõi trạng thái thiết bị con, điều phối luồng hoạt động, xử lý offline khi mất kết nối cloud.

**Edge Computing vs Cloud Computing**

Hai mô hình xử lý dữ liệu IoT:

- **Cloud Computing**: toàn bộ dữ liệu gửi lên cloud xử lý — tài nguyên tính toán mạnh mẽ, phù hợp AI inference nặng và lưu trữ lâu dài, nhưng phụ thuộc kết nối mạng và có thêm latency.
- **Edge Computing**: xử lý ngay tại thiết bị biên hoặc gateway — latency cực thấp, hoạt động được khi mất mạng, nhưng tài nguyên tính toán hạn chế.
- **Mô hình Hybrid** (phổ biến nhất): thiết bị biên xử lý tác vụ đơn giản và thời gian thực (điều khiển actuator, lọc dữ liệu), cloud xử lý tác vụ phức tạp (AI inference, analytics, storage). Đây là mô hình được đa số hệ thống IoT hiện đại áp dụng.

### 2.3.3. Lý do lựa chọn ESP32 + Arduino cho ParkSmart

Giải pháp IoT cho ParkSmart yêu cầu: kết nối WiFi giao tiếp HTTP với server, điều khiển barrier vật lý, hiển thị thông tin trên màn hình, và xử lý input từ người dùng. Dưới đây là các so sánh công nghệ đã cân nhắc:

**a) Vi điều khiển IoT Gateway:**

| Tiêu chí               |     **ESP32**      |    Raspberry Pi    |        STM32        |        ESP8266         |
| ---------------------- | :----------------: | :----------------: | :-----------------: | :--------------------: |
| WiFi tích hợp          |     ✅ Có sẵn      |     ✅ Có sẵn      | ❌ Cần module ngoài |       ✅ Có sẵn        |
| Chi phí                |     ~120.000₫      |     ~900.000₫      |      ~80.000₫       |        ~60.000₫        |
| GPIO đa dụng           |     ✅ 34 pins     |     ✅ 40 pins     |      ✅ Nhiều       |  ⚠️ 11 pins (hạn chế)  |
| I2C + UART đồng thời   |   ✅ Hỗ trợ tốt    |   ✅ Hỗ trợ tốt    |    ✅ Hỗ trợ tốt    | ⚠️ Chỉ 1 UART hardware |
| Tiêu thụ điện          |    Thấp (~80mA)    |  Cao (~500–700mA)  |      Rất thấp       |      Thấp (~80mA)      |
| Độ phức tạp triển khai | Thấp (Arduino IDE) | Cao (cần OS setup) |  Trung bình (HAL)   |   Thấp (Arduino IDE)   |

**ESP32 được chọn** vì: WiFi tích hợp kết nối trực tiếp server không cần module ngoài; chi phí thấp phù hợp quy mô đồ án; đủ GPIO cho OLED (I2C) + UART + nút nhấn + LED đồng thời; lập trình qua Arduino IDE quen thuộc [19]. Raspberry Pi bị loại vì chi phí cao gấp 7 lần và tiêu thụ điện nhiều — quá mức cần thiết khi ESP32 chỉ gửi HTTP request chứ không chạy AI inference. ESP8266 bị loại vì chỉ có 1 UART hardware — không đủ khi cần Serial debug + UART giao tiếp Arduino đồng thời. STM32 không có WiFi tích hợp và hệ sinh thái thư viện phức tạp hơn.

**b) Tại sao tách ESP32 + Arduino thay vì chỉ dùng ESP32?**

ESP32 hoàn toàn đủ GPIO để điều khiển servo trực tiếp. Tuy nhiên, ParkSmart tách thành 2 board vì lý do **phân tách trách nhiệm (Separation of Concerns)**: ESP32 chuyên networking (WiFi, HTTP) + hiển thị (OLED) + logic điều phối; Arduino [20] chuyên điều khiển actuator (servo barrier) + xử lý PWM chính xác. Sự phân tách này đem lại: **(1) Độ tin cậy** — nếu ESP32 crash do WiFi timeout, Arduino vẫn duy trì barrier ở trạng thái an toàn (đóng); **(2) Dễ debug** — test barrier độc lập qua Serial Monitor mà không cần kết nối server; **(3) Mở rộng** — thêm barrier chỉ cần thêm Arduino, không ảnh hưởng ESP32.

**c) Giao thức kết nối IoT Gateway — Cloud Server:**

| Tiêu chí               |           **HTTP REST**           |           MQTT           |          LoRa           |
| ---------------------- | :-------------------------------: | :----------------------: | :---------------------: |
| Mô hình giao tiếp      |         Request-Response          |    Publish-Subscribe     |    Long-range radio     |
| Phù hợp pattern        | Event-driven (nhấn nút → gọi API) | Streaming data liên tục  | Khoảng cách xa, outdoor |
| Tương thích backend    |     ✅ Trực tiếp với FastAPI      | ⚠️ Cần MQTT broker riêng |   ❌ Cần LoRa gateway   |
| Độ phức tạp triển khai |               Thấp                |        Trung bình        |           Cao           |

**HTTP REST được chọn** vì ParkSmart hoạt động theo mô hình **event-driven** (nhấn nút → gọi API → nhận kết quả), phù hợp request-response. AI Service đã có sẵn REST endpoints — ESP32 giao tiếp trực tiếp không cần broker trung gian. MQTT phù hợp hơn cho cảm biến streaming data liên tục (nhiệt độ, độ ẩm), không phải pattern check-in/check-out theo sự kiện. LoRa dành cho khoảng cách xa (km), không cần thiết khi bãi xe có WiFi.

**d) Màn hình hiển thị:**

| Tiêu chí                 |  **OLED SSD1306**   |          LCD 16×2          |      LED Matrix      |
| ------------------------ | :-----------------: | :------------------------: | :------------------: |
| Độ phân giải             |    128×64 pixels    |     16 ký tự × 2 dòng      |       8×8 dots       |
| Hiển thị biển số đầy đủ  |  ✅ Đồ họa + text   |     ⚠️ Giới hạn ký tự      | ❌ Không đủ chi tiết |
| Giao tiếp                |     I2C (2 dây)     | Parallel (6+ dây) hoặc I2C |     SPI hoặc I2C     |
| Độ tương phản ngoài trời | Cao (self-emitting) | Trung bình (cần backlight) |         Cao          |

**OLED SSD1306 được chọn** vì: hiển thị biển số xe đầy đủ (nhiều ký tự + formatting), hỗ trợ đồ họa cho icon trạng thái, giao tiếp I2C chỉ 2 dây tiết kiệm GPIO, tương phản cao dễ đọc ngoài trời. LCD 16×2 quá ít ký tự để hiển thị biển số + thông tin booking.

### 2.3.4. Các kỹ thuật chính áp dụng trong ParkSmart

Thay vì đi sâu vào chi tiết firmware (xem Phụ lục C cho sơ đồ kết nối và giao thức UART chi tiết), phần này tóm tắt các kỹ thuật IoT cốt lõi ở mức kiến trúc:

- **Giao tiếp UART giữa ESP32 và Arduino**: Giao thức nối tiếp 9600 baud với bộ lệnh text tùy chỉnh (OPEN/CLOSE + ACK) để điều khiển barrier. Arduino phản hồi xác nhận (ACK) mỗi lệnh, đảm bảo truyền thông tin cậy hai chiều. UART được chọn thay vì SPI hay I2C vì đơn giản, full-duplex, phù hợp giao tiếp lệnh text giữa 2 vi điều khiển.
- **Giao tiếp I2C cho màn hình OLED**: Bus 2 dây kết nối ESP32 với OLED SSD1306, hiển thị real-time biển số nhận dạng, trạng thái check-in/out, và thông báo hệ thống. I2C tiết kiệm GPIO đáng kể so với giao tiếp parallel truyền thống.
- **HTTP REST/JSON kết nối IoT Gateway với AI Server**: ESP32 gửi HTTP POST request kèm JSON payload đến AI Service, nhận response JSON chứa kết quả nhận dạng và lệnh điều khiển. Xác thực qua header `X-Gateway-Secret` và `X-Device-Token` đảm bảo chỉ thiết bị đã đăng ký mới giao tiếp được với server.
- **Device registration và heartbeat monitoring**: Khi khởi động, ESP32 tự đăng ký với AI Service (device_id, firmware_version, IP address). Sau đó gửi heartbeat mỗi 10 giây — nếu server không nhận heartbeat trong 30 giây, thiết bị được đánh dấu offline và cảnh báo admin. Auto-reconnect WiFi với exponential backoff khi mất kết nối.
- **Anti-noise UART filtering**: Servo motor hoạt động tạo nhiễu điện từ gây byte garbage trên đường UART. Firmware Arduino tích hợp bộ lọc: loại bỏ ký tự non-ASCII, trim whitespace, chỉ xử lý lệnh khớp với bảng lệnh — đảm bảo barrier không mở/đóng sai do tín hiệu nhiễu.
- **Auto-close barrier với dual-timer mechanism**: Sau khi mở barrier, ESP32 khởi động timer 5 giây rồi tự động gửi lệnh đóng. Arduino có timer backup độc lập — barrier luôn đóng ngay cả khi ESP32 gặp sự cố gửi lệnh, ngăn ngừa rủi ro an toàn.
- **Luồng check-in/check-out tổng quan**: Quy trình tự động diễn ra khi xe đến cổng: user nhấn nút → ESP32 gửi HTTP POST qua WiFi đến AI Service → server mở camera quét QR booking và chụp biển số + OCR → so khớp biển số với booking trong database → trả response cho ESP32 → ESP32 hiển thị kết quả trên OLED + gửi lệnh UART cho Arduino mở barrier → auto-close sau timeout. Luồng check-out tương tự qua cổng ra, kiểm tra trạng thái "checked_in" và tính phí.

**Ưu điểm nổi bật của giải pháp IoT ParkSmart:**

- Kiến trúc 3 lớp rõ ràng (Perception → Network → Application), dễ bảo trì và mở rộng từng lớp độc lập.
- Chi phí phần cứng thấp (ESP32 ~120K + Arduino ~80K + OLED ~50K ≈ 250.000₫/cổng) — phù hợp quy mô đồ án tốt nghiệp.
- Phân tách ESP32 (networking) và Arduino (actuator) tăng độ tin cậy: barrier vẫn an toàn khi ESP32 gặp sự cố.
- Device registration + heartbeat cho phép giám sát sức khỏe thiết bị real-time từ admin dashboard.
- Toàn bộ logic AI xử lý trên cloud (FastAPI), thiết bị IoT chỉ gửi/nhận — dễ cập nhật mô hình AI mà không cần flash lại firmware.

**Nhược điểm và cách khắc phục:**

- **Phụ thuộc WiFi**: Nếu mất WiFi, ESP32 không giao tiếp được server → barrier không mở. → _Khắc phục_: Auto-reconnect WiFi tích hợp; phiên bản sau có thể bổ sung chế độ offline fallback với local storage (SPIFFS) buffer request thất bại.
- **Servo motor giới hạn lực**: SG90/MG996R phù hợp mô hình demo, không đủ lực cho barrier thật. → _Khắc phục_: Production cần thay bằng motor DC/stepper với driver riêng — thiết kế UART command protocol không thay đổi.
- **HTTP thay vì HTTPS**: ESP32 giao tiếp HTTP do giới hạn tài nguyên vi điều khiển. → _Khắc phục_: Gateway secret + device token làm lớp xác thực; production nên nâng cấp HTTPS hoặc VPN nội bộ.

---

## 2.4. Django REST Framework

### 2.4.1. Giới thiệu Django REST Framework

**Django REST Framework (DRF)** là bộ công cụ mã nguồn mở được xây dựng trên nền tảng **Django** [1] — web framework phổ biến nhất của Python — nhằm đơn giản hóa việc xây dựng Web API theo kiến trúc RESTful [2]. DRF được phát triển bởi **Tom Christie** và cộng đồng mã nguồn mở từ năm 2011, trở thành một trong những lựa chọn hàng đầu cho Python API development.

Django là web framework theo triết lý **"batteries included"** — đi kèm sẵn ORM (Object-Relational Mapping), hệ thống migration, admin panel, authentication framework và middleware pipeline. DRF kế thừa toàn bộ hệ sinh thái này và bổ sung các thành phần chuyên biệt cho API: **Serializer** (chuyển đổi và validation dữ liệu), **ViewSet** (xử lý request tự động theo chuẩn REST), **Router** (sinh URL pattern tự động), **Authentication/Permission** (bảo mật đa tầng), **Browsable API** (giao diện test tương tác trên trình duyệt), cùng hệ thống **Filtering** và **Pagination** tích hợp sẵn.

### 2.4.2. Kiến trúc Django REST Framework

DRF tuân theo mô hình kiến trúc **Model – Serializer – View**, là biến thể chuyên biệt cho API development của mô hình MVT (Model–View–Template) truyền thống trong Django. Luồng xử lý một HTTP request đi qua các tầng:

```
HTTP Request (GET / POST / PUT / PATCH / DELETE)
  → URL Router — Ánh xạ URL pattern đến View/ViewSet
    → Middleware Chain — CORS, Logging, Exception handling
      → Authentication Backend — Xác minh danh tính
        → Permission Classes — Kiểm tra quyền truy cập
          → Throttle Classes — Kiểm tra rate limit
            → View / ViewSet — Xử lý logic nghiệp vụ
              → Serializer — Validate input / Serialize output
                → Model / Django ORM — Tương tác Database
                  → HTTP Response (JSON)
```

**Các thành phần chính:**

- **Model (Django ORM)** định nghĩa cấu trúc dữ liệu và quan hệ trong database. Django ORM tự động ánh xạ Model thành bảng SQL, cung cấp API truy vấn trừu tượng mà không cần viết SQL trực tiếp. Hệ thống migration theo dõi mọi thay đổi schema và tự động sinh scripts SQL, đảm bảo database luôn đồng bộ với mã nguồn.
- **Serializer** đảm nhận chuyển đổi và validation dữ liệu hai chiều: _Serialization_ (Model instances → JSON) và _Deserialization_ (JSON request → Python objects với validation). ModelSerializer tự động tạo fields từ Model definition; DRF còn hỗ trợ **nested serialization** cho các quan hệ ForeignKey và ManyToMany, cho phép serialize dữ liệu liên kết phức tạp trong một response duy nhất.
- **ViewSet + Router** là pattern cốt lõi của DRF. ViewSet chứa logic xử lý request, Router tự động sinh đầy đủ URL theo chuẩn RESTful — chỉ với vài dòng cấu hình, DRF tạo ra sáu endpoint chuẩn (list, create, retrieve, update, partial_update, destroy) cùng khả năng mở rộng bằng **custom actions** cho các endpoint nghiệp vụ đặc thù.
- **Authentication, Permission và Throttling** kiểm soát bảo mật đa tầng: xác minh danh tính, kiểm tra quyền truy cập ở cả mức view và mức object, và giới hạn tần suất yêu cầu theo người dùng hoặc địa chỉ IP.

### 2.4.3. So sánh với các framework thay thế

| Tiêu chí                        | **DRF (Django)** | Flask + Marshmallow         | Express.js (Node)       | Spring Boot (Java)           |
| ------------------------------- | :--------------: | :-------------------------: | :---------------------: | :--------------------------: |
| Tốc độ phát triển CRUD          |    ⭐⭐⭐⭐⭐    |           ⭐⭐⭐            |         ⭐⭐⭐          |             ⭐⭐             |
| ORM + Migration tích hợp        |    ✅ Có sẵn     | ❌ Cần SQLAlchemy + Alembic | ❌ Cần Sequelize/Prisma |       ✅ JPA + Flyway        |
| Admin Panel quản trị dữ liệu    | ✅ Django Admin  |         ❌ Không có         |       ❌ Không có       |  ⚠️ Spring Admin (hạn chế)   |
| Browsable API                   |    ✅ Có sẵn     |         ❌ Không có         |       ❌ Không có       | ⚠️ Swagger UI (cần cấu hình) |
| Hệ sinh thái ngôn ngữ           |     Python       |            Python           |       JavaScript        |             Java             |
| Async / Real-time native        |    ⚠️ Hạn chế    |         ⚠️ Hạn chế          |  ✅ Mạnh (Event-loop)   |        ⚠️ Trung bình         |
| Learning curve                  |    Trung bình    |            Thấp             |          Thấp           |             Cao              |

DRF là lựa chọn tối ưu cho các dự án có nhiều **CRUD-heavy services** trên hệ sinh thái Python: ModelViewSet kết hợp Router cho phép triển khai một dịch vụ hoàn chỉnh (validation, permission, pagination, filtering) chỉ trong vài dòng cấu hình, trong khi các phương án thay thế thường yêu cầu tích hợp nhiều thư viện rời rạc. Django Admin Panel cung cấp giao diện quản trị dữ liệu mặc định — tính năng mà Flask, Express.js và Spring Boot không có sẵn.

**Lý do ParkSmart sử dụng DRF:** đề tài có bốn dịch vụ backend nghiệp vụ (quản lý xác thực, đặt chỗ, bãi xe và phương tiện) đều là CRUD-heavy với mô hình dữ liệu quan hệ phức tạp giữa User, Vehicle, Booking, ParkingLot, Floor, Zone và Slot. DRF cho phép triển khai nhanh các dịch vụ này nhờ ViewSet + Router, đồng thời tận dụng Django Admin để quản trị dữ liệu mà không cần phát triển giao diện riêng. Chi tiết triển khai được trình bày tại **Chương 3**.

### 2.4.4. Ưu và nhược điểm

**Ưu điểm:**

- **Tốc độ phát triển cao**: ViewSet + Router pattern giảm mã lặp mẫu, cho phép triển khai một CRUD service hoàn chỉnh chỉ với Model, Serializer và cấu hình Router.
- **Django ORM và Migration System**: Quản lý schema database an toàn qua migration tự động; hỗ trợ rollback khi cần. Các quan hệ phức tạp được xử lý tự nhiên qua ForeignKey và ManyToMany.
- **Admin Panel tích hợp sẵn**: Giao diện quản trị dữ liệu có sẵn không cần phát triển thêm — tiết kiệm thời gian vận hành.
- **Browsable API**: Cho phép kiểm tra trực tiếp API trên trình duyệt mà không cần Postman, đẩy nhanh quá trình phát triển và gỡ lỗi.
- **Cộng đồng lớn**: Tài liệu phong phú, thư viện mở rộng đa dạng cho mọi nhu cầu đặc thù.

**Nhược điểm:**

- **Hiệu năng đồng bộ**: Django là synchronous framework — mỗi request chiếm một thread, không phù hợp cho tác vụ I/O-bound nặng như AI inference hoặc camera streaming.
- **Cấu trúc project phức tạp**: Mỗi Django app yêu cầu nhiều file cấu hình (settings, urls, admin, serializers, views, permissions) — có thể khiến cấu trúc nặng nề với các dịch vụ nhỏ.
- **Khởi động chậm**: Phải nạp toàn bộ Django stack khi khởi động container — ảnh hưởng thời gian cold start trong một số tình huống triển khai.

---

## 2.5. FastAPI

### 2.5.1. Giới thiệu FastAPI

**FastAPI** là một web framework hiện đại cho Python, được phát triển bởi **Sebastián Ramírez** và phát hành lần đầu vào năm 2018 [3]. Khác với các framework Python truyền thống như Flask (2010) hay Django (2005) vốn hoạt động trên giao thức **WSGI** (Web Server Gateway Interface) — xử lý đồng bộ, mỗi request chiếm một worker thread cho đến khi hoàn tất — FastAPI được xây dựng hoàn toàn trên nền **ASGI** (Asynchronous Server Gateway Interface). ASGI cho phép xử lý bất đồng bộ (async/await) ngay từ core framework: một worker có thể nhận request mới trong khi chờ I/O hoàn tất, tăng đáng kể throughput cho các tác vụ I/O-bound.

FastAPI được xây dựng trên hai thành phần nền tảng: **Starlette** — toolkit cung cấp HTTP routing, middleware, WebSocket và background tasks — và **Pydantic** — thư viện data validation sử dụng Python type hints. Triết lý thiết kế cốt lõi là **type hints vừa là tài liệu, vừa là validation, vừa là schema**: lập trình viên chỉ cần khai báo kiểu dữ liệu một lần trong function signature, framework tự động thực hiện validation input, serialization output và sinh tài liệu OpenAPI 3.0 tương tác qua Swagger UI và ReDoc.

### 2.5.2. Kiến trúc FastAPI

FastAPI kết hợp ba lớp chính: **Starlette** (web layer — HTTP routing, middleware, WebSocket), **Pydantic** (data layer — validation và serialization) và **OpenAPI auto-generation** (documentation layer). Luồng xử lý một HTTP request đi qua các tầng:

```
Client Request
  → ASGI Server (Uvicorn: event loop, HTTP parsing)
    → Middleware Chain (CORS, Logging, Error Handler)
      → Route Matching (Starlette router: path + method → endpoint)
        → Dependency Resolution (Depends(): DB session, auth, config)
          → Pydantic Validation (request body/query/path → 422 nếu sai)
            → Endpoint Function (business logic, async hoặc sync)
              → Response Model Serialization (Pydantic → JSON)
                → JSON Response
```

**Các thành phần kiến trúc chính:**

- **Dependency Injection System**: FastAPI cung cấp hệ thống DI tích hợp thông qua `Depends()`. Dependencies có thể là hàm sync hoặc async, trả về giá trị cần inject (database session, authenticated user, configuration). FastAPI xây dựng dependency graph và resolve đệ quy — cho phép tách biệt cross-cutting concerns (auth, DB, logging) khỏi business logic và dễ dàng override trong unit test.
- **Pydantic Validation và Response Model**: Mỗi endpoint khai báo schema đầu vào và đầu ra bằng Pydantic v2. Framework tự động validate request trước khi chạy hàm xử lý (trả 422 Unprocessable Entity nếu sai kiểu), serialize response theo đúng schema (loại bỏ các field không khai báo), và sinh OpenAPI schema từ cùng một định nghĩa — đảm bảo tài liệu luôn đồng bộ với mã nguồn.
- **Async/Await trên ASGI**: Uvicorn (ASGI server) sử dụng event loop **uvloop** (viết bằng Cython, thay thế asyncio event loop mặc định) và **httptools** (HTTP parser viết bằng C) để xử lý concurrent I/O. Khi một endpoint `await` database query hoặc HTTP call, event loop chuyển sang xử lý request khác — một worker process phục vụ hàng trăm request đồng thời mà không cần multi-threading. Endpoints đồng bộ được tự động chạy trong thread pool để tránh block event loop.

### 2.5.3. So sánh với các framework thay thế

| Tiêu chí                 | **FastAPI**      | Flask              | Django            | Express.js (Node) |
| ------------------------ | :--------------: | :----------------: | :---------------: | :---------------: |
| Async native (ASGI)      | ✅ Có            | ❌ Không (WSGI)    | ❌ Không (WSGI)   | ✅ Có             |
| Auto API docs (OpenAPI)  | ✅ Swagger+ReDoc | ❌ Cần extension   | ⚠️ DRF Browsable  | ❌ Cần extension  |
| Data validation tích hợp | ✅ Pydantic      | ❌ Cần Marshmallow | ✅ DRF Serializer | ❌ Cần thư viện   |
| Hệ sinh thái AI/ML       | ✅ Python đầy đủ | ✅ Python đầy đủ   | ✅ Python đầy đủ  | ❌ Không hỗ trợ   |
| Hiệu năng I/O-bound      | ⭐⭐⭐⭐⭐       | ⭐⭐               | ⭐⭐              | ⭐⭐⭐⭐          |
| Learning curve           | Trung bình       | Thấp               | Cao               | Thấp              |

FastAPI là lựa chọn tối ưu cho các dịch vụ có đặc thù **xử lý bất đồng bộ cao** như AI inference, streaming dữ liệu thời gian thực, và tích hợp nhiều lời gọi HTTP bên ngoài. Trên cùng hệ sinh thái Python, FastAPI cho phép sử dụng trực tiếp các thư viện AI/ML (PyTorch, OpenCV, transformers, ultralytics) mà không cần cầu nối ngôn ngữ — lợi thế mà Express.js không có.

**Lý do ParkSmart sử dụng FastAPI:** đề tài có bốn dịch vụ yêu cầu xử lý bất đồng bộ cao — AI Service chạy inference YOLO và TrOCR (mỗi lần ~300–500ms), Chatbot Service streaming phản hồi từ LLM, Payment Service chờ callback từ cổng thanh toán, và Notification Service push đa kênh. Django WSGI đồng bộ không phù hợp cho các tác vụ này do sẽ block worker thread khi chờ I/O. FastAPI đáp ứng cả bốn yêu cầu cốt lõi: async native, hệ sinh thái Python cho thư viện AI, tự động sinh tài liệu OpenAPI hỗ trợ tích hợp với firmware IoT, và kiểm tra kiểu dữ liệu nghiêm ngặt qua Pydantic. Chi tiết triển khai được trình bày tại **Chương 3**.

### 2.5.4. Ưu và nhược điểm

**Ưu điểm:**

- **Hiệu năng async cao**: Theo benchmark TechEmpower, FastAPI đạt ~15.000–20.000 requests/giây cho JSON serialization trên single process — ngang ngửa Node.js và Go, cao hơn ~4 lần so với Flask.
- **Type hints = validation = documentation**: Một khai báo type hint duy nhất tự động tạo ra bốn artifact — input validation, output serialization, OpenAPI schema và interactive docs — loại bỏ sự trùng lặp giữa validation code và tài liệu API.
- **Dependency Injection chuyên nghiệp**: Hệ thống DI tích hợp giúp tách biệt cross-cutting concerns khỏi business logic và hỗ trợ kiểm thử dễ dàng qua dependency override.
- **Tài liệu API tương tác tự động**: Swagger UI (`/docs`) và ReDoc (`/redoc`) có sẵn không cần cấu hình thêm — đặc biệt hữu ích khi tích hợp với các client khác (firmware IoT, mobile app, frontend).

**Nhược điểm:**

- **Hệ sinh thái nhỏ hơn Django**: Ít gói mở rộng bên thứ ba và middleware sẵn có hơn Django (đã phát triển từ 2005) — nhiều tính năng cần tự xây dựng.
- **Không có Admin Panel tích hợp**: Không có giao diện quản trị dữ liệu có sẵn như Django Admin — phải tự xây dựng hoặc dùng công cụ riêng.
- **SQLAlchemy + Alembic phức tạp hơn Django ORM**: Django ORM cung cấp migration tự động từ model changes; SQLAlchemy yêu cầu cấu hình Alembic riêng biệt và viết migration script thủ công hơn.

---

## 2.6. Ngôn ngữ Go và Framework Gin

Trong khi các mục trước đã trình bày Python (Django REST Framework và FastAPI) — ngôn ngữ chính cho business logic và AI trong ParkSmart — phần này giới thiệu Go, ngôn ngữ thứ hai được sử dụng trong hệ thống cho hai service đặc thù yêu cầu concurrency cao và latency thấp: API Gateway và Realtime WebSocket. Lựa chọn sử dụng hai ngôn ngữ (kiến trúc đa ngôn ngữ) là quyết định kiến trúc có chủ đích, và phần này trình bày lý do lựa chọn, đặc điểm kỹ thuật của Go, Gin Framework và Gorilla WebSocket, cùng cách áp dụng trong ParkSmart.

### 2.6.1. Giới thiệu ngôn ngữ Go

Go (còn gọi là Golang) là ngôn ngữ lập trình mã nguồn mở do Google phát triển [4], được thiết kế bởi Robert Griesemer, Rob Pike và Ken Thompson — ba kỹ sư với nền tảng sâu về hệ điều hành và ngôn ngữ lập trình hệ thống (Ken Thompson đồng sáng tạo UNIX và ngôn ngữ C, Rob Pike đồng sáng tạo UTF-8). Go ra mắt phiên bản đầu tiên vào năm 2009 với mục tiêu rõ ràng: giải quyết các vấn đề mà Google gặp phải khi xây dựng hệ thống phân tán quy mô lớn bằng C++ và Java — đặc biệt là thời gian biên dịch lâu, quản lý dependency phức tạp, và mô hình concurrency cồng kềnh.

Go là ngôn ngữ biên dịch — mã nguồn được biên dịch trực tiếp thành mã máy mà không cần trình thông dịch hay máy ảo trung gian. Điểm khác biệt cốt lõi so với Python (thông dịch) hay Java (JVM bytecode) là Go tạo ra **tệp thực thi đơn tĩnh** — một file thực thi duy nhất chứa toàn bộ thư viện phụ thuộc, không cần cài môi trường chạy trên máy đích. Đồng thời, Go có bộ thu gom rác tự động quản lý bộ nhớ (tương tự Java, Python) nhưng với thời gian tạm dừng cực thấp (~0.1ms từ Go 1.8+), phù hợp cho ứng dụng yêu cầu độ trễ thấp.

Đặc điểm quan trọng nhất của Go là mô hình concurrency dựa trên **Goroutines** và **Channels**, lấy cảm hứng từ lý thuyết CSP (Communicating Sequential Processes) của Tony Hoare. Goroutine là luồng nhẹ do Go runtime quản lý — mỗi goroutine chỉ chiếm khoảng 2KB bộ nhớ stack (so với ~1MB cho luồng hệ điều hành trong Java, hay ~100KB cho Python thread), và Go runtime có thể ghép kênh hàng triệu goroutines trên một số lượng nhỏ luồng hệ điều hành. Channel là cơ chế giao tiếp an toàn kiểu giữa các goroutines — cho phép truyền dữ liệu an toàn mà không cần khóa/mutex, tuân theo triết lý "Không giao tiếp bằng cách chia sẻ bộ nhớ; hãy chia sẻ bộ nhớ bằng cách giao tiếp" (Don't communicate by sharing memory; share memory by communicating).

Một đặc điểm thiết kế quan trọng khác của Go là cơ chế **error handling tường minh** (explicit error handling). Thay vì sử dụng ngoại lệ với try/catch như Python, Java, hay JavaScript — nơi lỗi có thể bị "nuốt" nếu lập trình viên quên bắt — Go buộc lập trình viên xử lý lỗi ngay tại mỗi lời gọi hàm qua giá trị trả về nhiều: hàm trả về `(result, error)`, và Go compiler cảnh báo nếu biến error không được kiểm tra. Triết lý này ban đầu gây khó chịu vì code dài hơn (nhiều `if err != nil` blocks), nhưng đảm bảo mọi error path đều được xử lý rõ ràng — đặc biệt quan trọng cho gateway service nơi một lỗi không được handle có thể ảnh hưởng toàn bộ hệ thống.

Nhờ hiệu năng gần C/C++ (trong benchmark xử lý JSON, HTTP routing, Go chỉ chậm hơn C khoảng 10–20%) kết hợp với cú pháp đơn giản (chỉ 25 từ khóa, không có class/inheritance), Go đã trở thành lựa chọn phổ biến cho infrastructure software và microservices. Các dự án nổi bật viết bằng Go bao gồm Docker (container runtime), Kubernetes (container orchestration), Prometheus (monitoring), Terraform (infrastructure as code), và Cloudflare Workers runtime — tất cả đều là hệ thống yêu cầu concurrency cao và latency thấp.

ParkSmart sử dụng Go phiên bản 1.22 — bản phát hành chính thức tháng 2/2024, bổ sung cải tiến quan trọng cho `for` range loops (hỗ trợ integers và function iterators), enhanced routing patterns trong standard library `net/http` (hỗ trợ HTTP method matching và wildcard trong route patterns), và profile-guided optimization (PGO) tự động — compiler sử dụng profiling data từ production để tối ưu binary. Phiên bản này ổn định, đã qua nhiều patch releases, phù hợp cho production deployment.

Ngoài ngôn ngữ, Go nổi bật với bộ công cụ phát triển tích hợp sẵn (toolchain) — không cần cài thêm công cụ bên thứ ba cho các tác vụ cơ bản: `go fmt` (định dạng mã thống nhất), `go vet` (phát hiện lỗi phổ biến tại thời điểm biên dịch), `go test` (framework kiểm thử tích hợp), `go build` (biên dịch đa nền tảng), và `go mod` (quản lý phụ thuộc). Triết lý "tích hợp sẵn đầy đủ" này giảm thiểu thời gian cấu hình môi trường phát triển — lập trình viên chỉ cần cài Go là đủ để bắt đầu viết mã, biên dịch, kiểm thử, và triển khai.

### 2.6.2. Giới thiệu Gin Framework

Gin là HTTP web framework cho Go, nổi tiếng với hiệu năng cao nhất trong hệ sinh thái Go framework [5]. Về mặt kiến trúc nội bộ, Gin xây dựng HTTP router dựa trên cấu trúc dữ liệu **radix tree** (prefix tree nén) — khi một request đến, router tra cứu route matching với độ phức tạp O(log n) dựa trên số ký tự trong URL path, thay vì O(n) quét tuần tự qua danh sách routes như nhiều framework khác. Điều này đảm bảo hiệu năng routing không suy giảm khi số lượng routes tăng lên — quan trọng cho API Gateway với hàng chục route patterns.

Gin cung cấp các tính năng cần thiết cho việc xây dựng RESTful API hiện đại: chuỗi phần mềm trung gian (mỗi yêu cầu đi qua: logging → CORS → xác thực → xử lý, có thể thêm/bớt linh hoạt), xuất JSON tối ưu, nhóm đường dẫn theo tiền tố (ví dụ: nhóm `/api/v1/` chứa tất cả endpoint có phiên bản), tự động ánh xạ tham số từ query/body/header vào cấu trúc dữ liệu Go, và phần mềm trung gian khôi phục lỗi (tự động bắt panic trong xử lý, trả về 500 thay vì crash toàn dịch vụ).

So với các Go framework khác — Echo (tương tự Gin nhưng ít phổ biến hơn), Fiber (lấy cảm hứng từ Express.js, dùng fasthttp thay vì net/http standard), hay net/http standard library (cung cấp HTTP server cơ bản nhưng cần viết nhiều mã lặp mẫu cho routing, middleware, JSON handling) — Gin cân bằng tốt giữa hiệu năng, tính năng sẵn có, và cộng đồng hỗ trợ lớn (76.000+ GitHub stars, top 3 Go projects trên GitHub). Trong benchmark, Gin xử lý ~40.000–60.000 requests/giây cho JSON serialization trên single core, nhanh hơn Flask (~3.000–5.000 req/s) khoảng 10 lần và nhanh hơn Express.js (~15.000–25.000 req/s) khoảng 2–3 lần.

Gin có thể hiểu như tương đương Express.js trong hệ sinh thái Node.js: đủ nhẹ để không gây overhead đáng kể, đủ đầy đủ để không cần viết lại các chức năng cơ bản. ParkSmart sử dụng Gin phiên bản 1.10.0 cùng gin-contrib/cors 1.7.2 cho CORS middleware.

### 2.6.3. Giới thiệu Gorilla WebSocket

WebSocket là giao thức truyền thông full-duplex (hai chiều đồng thời) hoạt động trên một TCP connection duy nhất, được chuẩn hóa trong RFC 6455 (2011). Khác với HTTP truyền thống theo mô hình request-response (client gửi request → server trả response → connection có thể đóng), WebSocket cho phép cả client và server gửi dữ liệu bất kỳ lúc nào sau khi connection được thiết lập — phù hợp cho ứng dụng real-time như live dashboard, chat, hay cập nhật trạng thái liên tục. Đây là sự khác biệt bản chất: HTTP là "client hỏi, server trả lời", còn WebSocket là "cả hai bên nói chuyện tự do".

Quy trình thiết lập WebSocket bắt đầu bằng **HTTP Upgrade handshake**: client gửi HTTP GET request với header `Connection: Upgrade` và `Upgrade: websocket`, kèm theo `Sec-WebSocket-Key` (random base64 string). Server xác nhận bằng response 101 Switching Protocols với `Sec-WebSocket-Accept` (hash của key + magic string). Sau khi handshake thành công, TCP connection được "nâng cấp" từ HTTP sang WebSocket protocol — connection duy trì mở (persistent) và hai bên trao đổi dữ liệu qua message frames nhỏ gọn (2–14 bytes header) mà không cần HTTP headers lặp lại — giảm đáng kể overhead so với polling (gửi HTTP request định kỳ, mỗi request ~800 bytes headers) hay long-polling (giữ HTTP request mở chờ data).

Gorilla WebSocket [6] (phiên bản 1.5.3) là thư viện WebSocket phổ biến và ổn định nhất trong hệ sinh thái Go, cung cấp API đầy đủ cho: connection upgrade (nâng cấp HTTP request thành WebSocket), ping/pong heartbeat (gửi ping frame định kỳ để giữ connection alive và phát hiện client mất kết nối — nếu không nhận pong trong thời gian quy định, server tự đóng connection và giải phóng tài nguyên), hỗ trợ text/binary message types (text cho JSON data, binary cho dữ liệu nhị phân), per-message compression (giảm bandwidth cho message lớn), và configurable buffer sizes. Gorilla WebSocket đã được dùng rộng rãi trong production bởi các công ty như Slack, Grafana, và HashiCorp. ParkSmart sử dụng Gorilla WebSocket trong Realtime Service để duy trì kết nối liên tục với frontend, phát sóng (broadcast) trạng thái bãi xe theo thời gian thực đến tất cả connected clients.

### 2.6.4. Lý do lựa chọn Go cho ParkSmart

Trong kiến trúc microservices của ParkSmart, phần lớn business logic (quản lý booking, vehicle, parking, AI inference, chatbot, payment) được xây dựng bằng Python — tận dụng hệ sinh thái phong phú của Django, FastAPI, PyTorch, và OpenCV. Tuy nhiên, hai service đặc thù — **API Gateway** (điểm vào duy nhất xử lý toàn bộ traffic) và **Realtime Service** (duy trì hàng trăm WebSocket connections đồng thời) — đặt ra yêu cầu về concurrency và latency mà Python không đáp ứng tối ưu.

Cụ thể, Python có hai hạn chế cơ bản cho loại workload này: (1) **Global Interpreter Lock (GIL)** — chỉ cho phép một thread thực thi Python bytecode tại một thời điểm, hạn chế khả năng tận dụng multi-core CPU cho concurrent requests; (2) **Interpreter overhead** — mỗi request phải đi qua bytecode interpretation, context switching giữa coroutines, tốn thêm 1–5ms latency mà không cần thiết cho một gateway chỉ cần routing + auth check. Node.js giải quyết vấn đề GIL bằng event loop nhưng lại single-threaded — một tác vụ CPU-bound (serialize message lớn) block toàn bộ event loop. Java giải quyết concurrency tốt nhưng chiếm nhiều bộ nhớ (~1MB/luồng) và khởi động chậm (~2 giây cho JVM warmup).

Bảng dưới so sánh Go với các ngôn ngữ/runtime phổ biến khác trên các tiêu chí quan trọng nhất cho API Gateway và Realtime service — hai loại service đặc thù yêu cầu concurrency cao, latency thấp, và khả năng duy trì nhiều kết nối đồng thời:

| Tiêu chí               | Go                          | Node.js                          | Python                    | Java              |
| ---------------------- | --------------------------- | -------------------------------- | ------------------------- | ----------------- |
| Mô hình concurrency    | Goroutines (M:N scheduling) | Event loop (single-threaded)     | Threading / asyncio       | OS Threads (1:1)  |
| Memory per connection  | ~2KB (goroutine stack)      | ~10KB (callback context)         | ~100KB (thread stack)     | ~1MB (OS thread)  |
| Binary deployment      | ✅ Single static binary     | ❌ Cần Node.js runtime           | ❌ Cần Python interpreter | ⚠️ Cần JVM + JAR  |
| Cold start time        | ~5ms                        | ~50ms                            | ~200ms                    | ~2000ms           |
| WebSocket native       | ✅ Gorilla (goroutine/conn) | ✅ ws / Socket.IO                | ⚠️ asyncio (event loop)   | ✅ Jetty / Netty  |
| Hệ sinh thái AI/ML     | ❌ Rất hạn chế              | ⚠️ Hạn chế                       | ✅ Phong phú nhất         | ⚠️ Trung bình     |
| Multi-core utilization | ✅ Tự động (GOMAXPROCS)     | ❌ Single-threaded (cần cluster) | ⚠️ GIL hạn chế            | ✅ Native threads |

Từ bảng so sánh, Go có lợi thế ở bốn tiêu chí quan trọng cho gateway/realtime: memory per connection (thấp nhất), binary deployment (đơn giản nhất), cold start (nhanh nhất), và multi-core utilization (tự động). Python dẫn đầu ở hệ sinh thái AI/ML — đây là lý do ParkSmart sử dụng cả hai ngôn ngữ: Go cho infrastructure layer, Python cho business/AI layer.

Ba lý do kỹ thuật quyết định lựa chọn Go cho Gateway và Realtime services:

**Thứ nhất — High concurrency cho API Gateway**: Gateway Service là điểm vào duy nhất (single entry point) của toàn hệ thống — mọi request từ frontend web, ứng dụng Unity simulator, và thiết bị ESP32 đều đi qua gateway trước khi được chuyển tiếp đến backend services. Điều này có nghĩa gateway phải xử lý tổng lượng traffic của toàn bộ hệ thống cộng lại. Mô hình goroutines của Go cho phép xử lý hàng ngàn concurrent connections với overhead cực thấp — mỗi goroutine chỉ chiếm khoảng 2KB stack (tự động grow khi cần), trong khi Python thread yêu cầu khoảng 100KB, và Java OS thread yêu cầu khoảng 1MB. Trên cùng một server 1GB RAM, Go có thể duy trì ~500.000 goroutines nhàn nhã, trong khi Python giới hạn ở ~10.000 threads.

**Thứ hai — Real-time WebSocket broadcasting**: Realtime Service cần duy trì hàng trăm WebSocket connections đồng thời — mỗi client (trình duyệt, Unity simulator) kết nối WebSocket để nhận cập nhật trạng thái slot bãi xe theo thời gian thực. Mô hình goroutine-per-connection của Go (mỗi WebSocket client được một goroutine riêng xử lý read/write) đơn giản về mặt code và hiệu quả về mặt tài nguyên. So sánh: Python asyncio WebSocket yêu cầu quản lý event loop thủ công hơn và không tận dụng được multi-core (GIL limitation), Node.js single-threaded event loop có thể bị block bởi tác vụ CPU-bound (serialization message lớn), trong khi Go goroutines được tự động phân phối trên tất cả CPU cores bởi Go scheduler.

**Thứ ba — Low latency tại API Gateway**: Gateway là "cửa ngõ" — mọi millisecond latency tại gateway đều cộng dồn vào response time của TẤT CẢ API calls trong hệ thống. Go compiled binary thực thi trực tiếp mã máy, cho latency routing + authentication check ở mức sub-millisecond. So sánh: Python Flask/FastAPI cần interpreter overhead cho mỗi request (bytecode interpretation, GIL acquisition), thêm 1–5ms latency; Java cần JVM warmup (JIT compilation) mất vài giây cho cold requests đầu tiên. Với Go, gateway thêm overhead gần như không đáng kể (<0.5ms) cho mỗi request được proxy.

Tóm lại, lựa chọn Go cho ParkSmart không phải thay thế Python, mà là bổ sung. Chiến lược **kiến trúc đa ngôn ngữ** — dùng đúng ngôn ngữ cho đúng loại tác vụ — là thực hành phổ biến trong kiến trúc microservices hiện đại: Go cho infrastructure layer (gateway, realtime) nơi concurrency và latency là ưu tiên, Python cho application layer (AI, business logic, CRUD) nơi hệ sinh thái thư viện và tốc độ phát triển là ưu tiên. Hai ngôn ngữ giao tiếp với nhau qua HTTP (gateway → backend proxy) và Redis pub/sub (backend → realtime events) — interface rõ ràng, không coupling ở mức code.

### 2.6.5. Kiến trúc Go Runtime và Gin Framework

**Go Runtime Architecture**

Go runtime quản lý goroutines theo mô hình **M:N scheduling** (M goroutines trên N OS threads), với ba thành phần chính: **G** (goroutine — đơn vị thực thi nhẹ, stack khởi tạo 2KB tự động grow khi cần), **M** (machine — OS thread thực thi code), và **P** (processor — logical processor, số lượng mặc định = GOMAXPROCS = số CPU cores). Mỗi P có **local run queue** chứa goroutines sẵn sàng chạy; khi queue cạn, P sử dụng **work-stealing algorithm** — lấy goroutines từ queue của P khác để cân bằng tải tự động.

Từ Go 1.14, scheduler hỗ trợ **preemptive scheduling** dựa trên asynchronous preemption — goroutine chạy quá 10ms bị tạm dừng nhường cho goroutine khác, ngăn một goroutine CPU-bound monopolize thread. Kết hợp với stack auto-growth (2KB → grow theo nhu cầu, có thể đến hàng MB), Go cho phép tạo hàng triệu goroutines trên một process mà không gây overhead đáng kể.

**Garbage Collector**

Go sử dụng **concurrent tri-color mark-and-sweep GC**. Ba màu (white — chưa xét, grey — đang xét, black — đã xét và reachable) cho phép GC chạy đồng thời với application code — không cần stop-the-world toàn bộ. Từ Go 1.8+, pause time trung bình ~0.1ms (sub-millisecond) — phù hợp cho ứng dụng latency-sensitive như API gateway và WebSocket server. Biến môi trường `GOGC` (mặc định 100) điều chỉnh tần suất GC: giá trị cao hơn giảm tần suất GC (ít CPU overhead, nhiều RAM hơn) và ngược lại.

**Gin Framework Architecture**

Gin tổ chức xử lý request theo kiến trúc phân tầng:

```
HTTP Request
    │
    ▼
┌──────────────────────┐
│  Gin Engine          │  Root router, global middleware
├──────────────────────┤
│  Router Groups       │  Nhóm routes theo prefix (/api/v1/...)
│  (Radix Tree)        │  Lookup O(log n) theo path characters
├──────────────────────┤
│  Middleware Chain     │  Logger → CORS → Auth → RateLimit
│  (Use → Next/Abort)  │  Mỗi middleware gọi Next() hoặc Abort()
├──────────────────────┤
│  Handler Function    │  Business logic, đọc/ghi gin.Context
├──────────────────────┤
│  gin.Context         │  Request state container: params, headers,
│                      │  body binding, JSON response, error list
└──────────────────────┘
    │
    ▼
HTTP Response
```

Các thành phần kiến trúc Gin:

- **Radix Tree Router**: Cấu trúc dữ liệu prefix tree nén lưu trữ route patterns. Mỗi request đến, router tra cứu path match với độ phức tạp O(log n) dựa trên số ký tự URL — hiệu năng routing không giảm khi số routes tăng, khác với linear scan O(n) của nhiều framework khác.
- **gin.Context**: Object trung tâm mang toàn bộ trạng thái request qua middleware chain — chứa tham số path/query, request body, response writer, danh sách errors, và key-value store tùy chỉnh. Context được tạo mới cho mỗi request và tái sử dụng qua sync.Pool để giảm GC pressure.
- **Middleware Chain**: Chuỗi hàm xử lý nối tiếp — mỗi middleware nhận Context, thực hiện logic (logging, auth check, CORS), rồi gọi `c.Next()` để chuyển sang middleware tiếp theo hoặc `c.Abort()` để dừng chain và trả response ngay lập tức. Pattern này cho phép thêm/bớt middleware linh hoạt mà không ảnh hưởng handler chính.

**WebSocket Model trong Go**

Go xử lý WebSocket theo mô hình **goroutine-per-connection**: mỗi client kết nối WebSocket được gán một cặp goroutine (read loop + write loop). Code viết dạng sequential blocking nhưng thực tế chạy concurrent nhờ Go scheduler — đơn giản hóa đáng kể so với callback-based (Node.js) hay async/await (Python).

Pattern phổ biến cho broadcast là **Hub pattern**: một goroutine trung tâm (Hub) quản lý danh sách connections qua 3 channels — register (client mới), unregister (client ngắt), broadcast (message cần gửi). Khi cần gửi message đến tất cả clients, Hub lặp qua danh sách và gửi qua write channel của từng connection. Channel-based communication giữa goroutines đảm bảo thread-safety mà không cần mutex — tuân theo triết lý Go: "share memory by communicating".

### 2.6.6. Các kỹ thuật chính sử dụng trong Go Services

Phần này tóm tắt các kỹ thuật Go cốt lõi được áp dụng trong ParkSmart ở mức kiến trúc — giải thích tại sao mỗi kỹ thuật được chọn và nó giải quyết vấn đề gì:

- **Goroutine-per-connection cho WebSocket**: Mỗi client kết nối WebSocket được gán một goroutine riêng biệt xử lý read loop (nhận message từ client) và write loop (gửi broadcast đến client). Mô hình này đơn giản hóa code so với callback-based (Node.js) hay async/await (Python) — mỗi goroutine viết như sequential code nhưng chạy concurrently, Go scheduler tự động phân phối trên các CPU cores. Khi client ngắt kết nối, goroutine tự kết thúc và giải phóng ~2KB stack — không bị rò rỉ bộ nhớ.
- **Redis session store lookup cho authentication**: Gateway Service tra cứu session từ Redis (DB 1) cho mỗi incoming request — thay vì sử dụng JWT (stateless token). Lựa chọn session-based authentication cho phép server-side session invalidation tức thì (khi user logout hoặc bị ban, session bị xóa khỏi Redis, request tiếp theo bị từ chối ngay lập tức) — điều không thể làm với JWT cho đến khi token hết hạn. Go-redis v9 cung cấp cơ chế dùng chung kết nối (connection pooling) tự động và pipeline support, giảm latency Redis lookup xuống sub-millisecond. Session data lưu trong Redis cũng cho phép mở rộng theo chiều ngang — nhiều thực thể gateway chia sẻ cùng session store.
- **Middleware chain pattern**: Request đi qua chuỗi middleware tuần tự: Logging (ghi lại method, path, status, response duration) → CORS (kiểm tra origin, headers cho phép, preflight OPTIONS handling) → Authentication (tra cứu Redis session, inject user info) → Rate Limiting (giới hạn request/phút theo IP hoặc user, bảo vệ backend khỏi abuse) → Reverse Proxy (chuyển tiếp đến backend service tương ứng). Gin framework hỗ trợ middleware chain native — mỗi middleware là một function nhận context và gọi `Next()` để chuyển sang middleware tiếp theo, hoặc `Abort()` để dừng chain (ví dụ: auth fail → trả 401 ngay, không proxy). Pattern này cho phép thêm/bớt middleware dễ dàng mà không ảnh hưởng logic xử lý chính.
- **WebSocket Hub pattern cho broadcast**: Central Hub là goroutine chạy vĩnh viễn, quản lý 3 channels: register (client mới kết nối), unregister (client ngắt kết nối), và broadcast (message cần gửi đến tất cả clients). Khi nhận message từ Redis pub/sub, Hub gửi vào broadcast channel, và lặp qua danh sách connected clients để gửi message — đảm bảo tất cả clients nhận được cùng một cập nhật trạng thái. Pattern này tập trung quản lý connections tại một điểm duy nhất, tránh xung đột đồng thời khi nhiều goroutines cùng truy cập danh sách clients. Hub cũng xử lý dừng dịch vụ an toàn — khi service khởi động lại, đóng tất cả kết nối sạch sẽ.
- **Redis Pub/Sub subscription cho event ingestion**: Realtime Service subscribe Redis channel và chạy một goroutine listener liên tục — khi Parking Service (Python) publish event `slot_updated` vào Redis (DB 5), listener goroutine nhận message gần như tức thời và chuyển vào Hub broadcast channel. Kiến trúc pub/sub này decouple hoàn toàn producer (Python services) và consumer (Go realtime) — hai bên không cần biết nhau tồn tại, chỉ cần đồng thuận format message qua Redis channel. Điều này giúp thêm/sửa/xóa subscriber mà không ảnh hưởng publisher, và ngược lại.
- **Header injection cho internal service communication**: Sau khi xác thực session thành công, gateway inject headers `X-User-ID`, `X-User-Email`, và `X-Gateway-Secret` vào request trước khi proxy đến backend. Backend services kiểm tra `X-Gateway-Secret` để đảm bảo request đến từ gateway (không phải direct access bypass) và đọc `X-User-ID` để biết user đang thao tác — tránh mỗi service phải tự tra cứu session Redis lặp lại. Cơ chế này tuân theo Zero Trust principle: backend services không expose public ports, chỉ gateway có thể truy cập, và mọi request phải có gateway secret hợp lệ.

Tổng hợp lại, 6 kỹ thuật trên phản ánh chiến lược sử dụng Go trong ParkSmart: tập trung vào concurrency (goroutine-per-connection), communication (Redis pub/sub, WebSocket Hub), và security (session-based auth, header injection) — ba yếu tố mà Go có lợi thế rõ rệt so với Python. Toàn bộ business logic phức tạp (AI inference, booking rules, payment processing) vẫn nằm trong Python services, Go chỉ đóng vai trò "infrastructure layer" — nhận, xác thực, chuyển tiếp, và phát sóng.

**Ưu điểm thực tế của Go trong ParkSmart:**

- **Triển khai đơn giản (tệp thực thi đơn, không cần môi trường chạy)**: File thực thi Go chạy trực tiếp trên Linux container mà không cần cài Go runtime, pip, hay trình quản lý gói. Kích thước Docker image cho Go service chỉ ~10–20MB (Alpine-based), so với ~500MB–1GB cho Python AI service.
- **An toàn kiểu dữ liệu tại thời điểm biên dịch**: Lỗi kiểu, thiếu giá trị trả về, biến không sử dụng, lỗi chưa xử lý được phát hiện tại thời điểm biên dịch — không cần chạy để phát hiện. Quan trọng đặc biệt cho gateway (một lỗi nhỏ ảnh hưởng toàn hệ thống). Go compiler còn có bộ phát hiện data race tích hợp (`go build -race`).

**Nhược điểm và cách khắc phục:**

- **Hệ sinh thái nhỏ hơn Node.js/Python**: Go có ít thư viện bên thứ ba hơn, đặc biệt trong lĩnh vực AI/ML, xử lý dữ liệu, và web tooling — khó tìm giải pháp sẵn có cho các tác vụ phức tạp. → _Khắc phục_: ParkSmart chỉ sử dụng Go cho đúng 2 service (gateway + realtime) nơi Go có thế mạnh rõ rệt; toàn bộ business logic, AI inference, và data processing vẫn dùng Python — tận dụng đúng thế mạnh của từng ngôn ngữ.
- **Không có ORM mạnh tương đương Django ORM hay SQLAlchemy**: Các Go ORM (GORM, sqlx) có tính năng hạn chế hơn, query builder kém linh hoạt, và migration tooling chưa mature bằng Alembic hay Django migrations. → _Khắc phục_: Go services trong ParkSmart không truy cập database trực tiếp — gateway proxy request đến Python services (nơi có Django ORM / SQLAlchemy), realtime service chỉ giao tiếp qua Redis pub/sub. Kiến trúc này loại bỏ hoàn toàn nhu cầu ORM trong Go.
- **Đường cong học tập dốc hơn cho nhóm quen Python/JavaScript**: Go có concepts khác biệt (goroutines, channels, interfaces implicit, error handling explicit qua return value thay vì try/catch) đòi hỏi thời gian thích nghi. → _Khắc phục_: Go có cú pháp đơn giản (chỉ 25 từ khóa, không có class, inheritance, hay generics phức tạp); nhóm chỉ cần nắm vững goroutines + channels + interfaces là đủ cho phạm vi 2 dịch vụ; phần còn lại của hệ thống vẫn dùng Python — giảm thiểu diện tích tiếp xúc với Go.
- **Verbose error handling**: Go yêu cầu kiểm tra error tại mỗi function call (`if err != nil`), dẫn đến code dài hơn so với Python try/catch bao trùm nhiều dòng. → _Khắc phục_: Đối với gateway và realtime service — nơi error handling chính xác là ưu tiên (một lỗi silently ignored có thể gây security breach hoặc connection leak) — explicit error handling thực tế là ưu điểm chứ không phải nhược điểm. Convention đặt tên error types nhất quán và hàm phụ trợ giúp giảm mã lặp mẫu.

---

## 2.7. ReactJS

### 2.7.1. Giới thiệu ReactJS

ReactJS (thường gọi tắt là React) là thư viện JavaScript mã nguồn mở do **Meta (Facebook)** phát triển, ra mắt năm **2013** bởi kỹ sư **Jordan Walke**. React được thiết kế để xây dựng giao diện người dùng (UI) theo hướng **component-based** cho các ứng dụng web Single Page Application (SPA). Tính đến nay, React là thư viện frontend phổ biến nhất thế giới theo khảo sát Stack Overflow Developer Survey, với hệ sinh thái đồ sộ và cộng đồng phát triển lớn nhất trong các frontend frameworks [7].

**Các đặc điểm cốt lõi của React:**

- **Virtual DOM**: React duy trì bản sao nhẹ của DOM thật trong bộ nhớ. Khi state thay đổi, thuật toán **Reconciliation** tính toán diff và chỉ cập nhật những phần DOM thực sự thay đổi. React 18 bổ sung **Concurrent Features** cho phép ưu tiên render phần quan trọng trước, đảm bảo giao diện mượt mà khi có nhiều cập nhật đồng thời.
- **Component-Based Architecture**: UI được chia thành các component độc lập, có thể tái sử dụng, mỗi component quản lý state và lifecycle riêng.
- **JSX (JavaScript XML)**: Cho phép viết cú pháp HTML-like trong JavaScript, kết hợp logic và giao diện trong cùng một file component.
- **One-Way Data Flow**: Dữ liệu chảy từ component cha xuống con qua props, giúp dễ theo dõi nguồn gốc dữ liệu và debug.
- **Hooks System (React 16.8+)**: Cho phép sử dụng state, lifecycle, và các tính năng React trong functional components, loại bỏ nhu cầu viết class components phức tạp.

**Trong dự án ParkSmart**, frontend được phát triển bằng **React 18.3.1** kết hợp **TypeScript 5.8.3** [28], build bằng **Vite 5.4.19** [8]. Đây là ứng dụng SPA thuần túy — **không sử dụng Next.js** — routing được xử lý hoàn toàn phía client bằng React Router v6 [29]. Vite được chọn vì tốc độ khởi động dev server nhanh (dưới 1 giây) nhờ native ES Modules và Hot Module Replacement (HMR) tức thì.

### 2.7.2. Lý do lựa chọn React cho ParkSmart

Giao diện ParkSmart yêu cầu: hiển thị bản đồ bãi xe real-time (hàng trăm ô đỗ cập nhật liên tục qua WebSocket), quản lý nhiều luồng dữ liệu đồng thời (booking, payment, notifications), và hỗ trợ cả giao diện người dùng lẫn admin dashboard phức tạp. Bảng dưới đây so sánh các framework frontend đã được cân nhắc:

| Tiêu chí                      |    **React**     |   Angular   |          Vue.js          |       Svelte       |
| ----------------------------- | :--------------: | :---------: | :----------------------: | :----------------: |
| Hệ sinh thái thư viện         |    ⭐⭐⭐⭐⭐    |  ⭐⭐⭐⭐   |          ⭐⭐⭐          |        ⭐⭐        |
| Component library (shadcn/ui) | ✅ Hỗ trợ đầy đủ | ❌ Không có | ⚠️ Port không chính thức |    ❌ Không có     |
| TypeScript support            |   ✅ Excellent   |  ✅ Native  |          ✅ Tốt          | ⚠️ Đang phát triển |
| Real-time UI performance      |    ⭐⭐⭐⭐⭐    |   ⭐⭐⭐    |         ⭐⭐⭐⭐         |     ⭐⭐⭐⭐⭐     |
| State management options      |    ⭐⭐⭐⭐⭐    |   ⭐⭐⭐    |         ⭐⭐⭐⭐         |       ⭐⭐⭐       |
| Cộng đồng và tài liệu         |    ⭐⭐⭐⭐⭐    |  ⭐⭐⭐⭐   |         ⭐⭐⭐⭐         |       ⭐⭐⭐       |
| Learning curve                |    Trung bình    |     Cao     |           Thấp           |        Thấp        |
| Tuyển dụng (thị trường VN)    |    ⭐⭐⭐⭐⭐    |   ⭐⭐⭐    |         ⭐⭐⭐⭐         |        ⭐⭐        |

**React được lựa chọn cho ParkSmart vì các lý do chính:**

1. **Hệ sinh thái phong phú nhất**: React sở hữu ecosystem lớn nhất trong các frontend frameworks — Redux Toolkit (state management), React Query (server state caching), React Router (routing), React Hook Form (form handling), cùng hàng nghìn thư viện chất lượng. Điều này đặc biệt quan trọng khi ParkSmart là ứng dụng phức tạp cần tích hợp nhiều tính năng đa dạng. Angular tuy có ecosystem tốt nhưng tất cả đều "Angular way" — ít linh hoạt hơn. Vue.js và Svelte có ecosystem nhỏ hơn đáng kể, đặc biệt thiếu các thư viện chuyên biệt cho real-time maps và complex dashboards.
2. **shadcn/ui — Component library hiện đại**: ParkSmart sử dụng **51 component** từ shadcn/ui (73 tổng UI components bao gồm 22 custom), một bộ thư viện chỉ khả dụng chính thức cho React. shadcn/ui xây dựng trên Radix UI (headless, WAI-ARIA accessible) và TailwindCSS, cho phép tùy biến hoàn toàn vì code được copy trực tiếp vào dự án (copy-paste approach) thay vì dependency npm — cho phép modify bất kỳ component nào mà không bị giới hạn bởi API của thư viện. Angular có Angular Material nhưng ít tùy biến hơn; Vue có Vuetify/Quasar nhưng không đạt mức accessibility và tùy biến của shadcn/ui; Svelte chưa có giải pháp tương đương.
3. **Virtual DOM tối ưu cho real-time dashboard**: Bản đồ bãi xe ParkSmart hiển thị hàng trăm ô đỗ với trạng thái cập nhật liên tục qua WebSocket. Virtual DOM và Concurrent Features của React 18 đảm bảo chỉ re-render những ô đỗ thực sự thay đổi, duy trì hiệu năng mượt mà ngay khi nhận hàng chục events/giây. Svelte tuy có hiệu năng compile-time tốt nhưng ecosystem cho complex real-time UIs còn non trẻ.
4. **Hỗ trợ TypeScript toàn diện**: React kết hợp TypeScript cung cấp kiểm tra kiểu dữ liệu toàn bộ mã nguồn — từ component props, kiểu dữ liệu API response, đến cấu trúc Redux state — giúp phát hiện lỗi tại thời điểm biên dịch thay vì lúc chạy. Đây là yếu tố quan trọng khi ParkSmart có nhiều data models phức tạp (User, Booking, ParkingSlot, Vehicle) cần tính nhất quán cao giữa frontend và backend.
5. **DevTools mạnh mẽ và cộng đồng**: React Developer Tools cho inspect component tree, state, props theo thời gian thực; Redux DevTools theo dõi state changes theo timeline với khả năng time-travel debugging — đặc biệt hữu ích khi debug luồng dữ liệu real-time phức tạp trong bản đồ bãi xe. Ngoài ra, cộng đồng React lớn nhất trong các frontend frameworks đảm bảo dễ tìm kiếm giải pháp, tuyển dụng nhân sự, và duy trì dự án dài hạn — đặc biệt trong thị trường Việt Nam.

### 2.7.3. Kiến trúc ReactJS

ReactJS (thường gọi tắt là React) là thư viện JavaScript cho xây dựng giao diện người dùng, được thiết kế xoay quanh mô hình **component-based** và cơ chế cập nhật DOM hiệu quả. Kiến trúc nội tại của React bao gồm năm trụ cột chính:

**Virtual DOM và Reconciliation**

React duy trì một **Virtual DOM** — bản sao nhẹ của DOM thật trong bộ nhớ JavaScript. Khi state hoặc props thay đổi, React tạo cây Virtual DOM mới, chạy thuật toán **Reconciliation** (còn gọi là "diffing") so sánh cây cũ và cây mới để xác định tập thay đổi tối thiểu, sau đó áp dụng (commit) chỉ những thay đổi đó lên DOM thật. Thuật toán diff hoạt động với độ phức tạp O(n) nhờ hai heuristics: (1) hai element khác type tạo cây con hoàn toàn mới, (2) developer cung cấp `key` prop để React nhận diện element nào di chuyển/thêm/xóa trong danh sách. Cơ chế này giảm thiểu thao tác DOM — vốn là bottleneck hiệu năng lớn nhất trong ứng dụng web.

```
State/Props thay đổi
    │
    ▼
┌─────────────────────────┐     ┌─────────────────────────┐
│ Virtual DOM (cây mới)   │────▶│  Diff Algorithm (O(n))  │
└─────────────────────────┘     └────────────┬────────────┘
                                             │
┌─────────────────────────┐     ┌────────────▼────────────┐
│ Virtual DOM (cây cũ)    │────▶│  Minimal Change Set     │
└─────────────────────────┘     └────────────┬────────────┘
                                             │
                                ┌────────────▼────────────┐
                                │  Commit → Real DOM      │
                                └─────────────────────────┘
```

**Component Model: Functional Components + Hooks**

React hiện đại sử dụng **Functional Components** — hàm JavaScript nhận props và trả về JSX mô tả UI. Toàn bộ lifecycle và side effects được quản lý qua hệ thống **Hooks**:

- `useState` — khai báo state cục bộ, trigger re-render khi state thay đổi.
- `useEffect` — thực thi side effects (gọi API, subscribe event, cleanup) sau mỗi render, thay thế componentDidMount/componentDidUpdate/componentWillUnmount của class components.
- `useContext` — truy cập giá trị từ Context mà không cần prop drilling qua nhiều tầng component.
- `useRef` — tham chiếu đến DOM element hoặc lưu giá trị mutable không trigger re-render.
- `useMemo` / `useCallback` — ghi nhớ (memoize) giá trị tính toán hoặc hàm callback để tránh re-computation không cần thiết, tối ưu hiệu năng.

Custom Hooks cho phép đóng gói logic stateful phức tạp (fetch data, form handling, WebSocket connection) thành hàm tái sử dụng — tách biệt hoàn toàn business logic khỏi UI rendering.

**One-way Data Flow (Luồng dữ liệu một chiều)**

React áp dụng mô hình **unidirectional data flow**: dữ liệu chảy từ component cha xuống component con thông qua props (read-only). Component con muốn thay đổi dữ liệu phải gọi callback function do cha truyền xuống — không được mutate props trực tiếp. Khi state cần chia sẻ giữa nhiều component:

- **State lifting** — đưa state lên component cha chung gần nhất.
- **Context API** — cung cấp giá trị cho toàn bộ subtree mà không cần truyền props qua từng tầng.
- **External state managers** (Redux, Zustand, Jotai) — quản lý global state bên ngoài component tree, phù hợp cho ứng dụng phức tạp.

Mô hình một chiều giúp luồng dữ liệu dễ theo dõi, dễ debug — biết chính xác state thay đổi ở đâu và ảnh hưởng component nào.

**JSX — JavaScript XML**

JSX là phần mở rộng cú pháp cho JavaScript, cho phép viết markup dạng HTML-like trực tiếp trong code JavaScript. Trình biên dịch (Babel, SWC, hoặc TypeScript compiler) chuyển đổi JSX thành lời gọi `React.createElement(type, props, ...children)` — tạo ra các JavaScript object mô tả cấu trúc UI. JSX không phải template engine — nó là biểu thức JavaScript hợp lệ, hỗ trợ đầy đủ logic điều kiện, vòng lặp, và composition thông qua cú pháp JavaScript thuần.

**React Fiber Architecture và Concurrent Features**

Từ React 16, kiến trúc nội tại được viết lại hoàn toàn với **Fiber** — cấu trúc dữ liệu dạng linked list biểu diễn mỗi unit of work trong quá trình render. Fiber cho phép React chia nhỏ render work thành các đơn vị nhỏ, tạm dừng và tiếp tục render giữa các frame — gọi là **time-slicing**. React 18 mở rộng Fiber thành **Concurrent Features**:

- **Suspense** — khai báo trạng thái loading cho component chờ dữ liệu async, hiển thị fallback UI trong khi chờ.
- **startTransition** — đánh dấu state update là "không khẩn cấp" (non-urgent), cho phép React ưu tiên render UI tương tác (typing, clicking) trước, hoãn render nội dung nặng — giữ UI luôn mượt mà ngay khi xử lý dữ liệu lớn.
- **Automatic batching** — gom nhiều state updates trong cùng event handler, Promise, hoặc timeout thành một lần re-render duy nhất, giảm số lần render không cần thiết.

Concurrent Features đặc biệt quan trọng cho ứng dụng có real-time updates liên tục hoặc danh sách dữ liệu lớn — đảm bảo giao diện không bị đơ (jank) ngay khi nhận nhiều cập nhật đồng thời.

### 2.7.4. Các kỹ thuật chính áp dụng trong ParkSmart

Các kỹ thuật frontend trong ParkSmart được lựa chọn để giải quyết các bài toán cụ thể của hệ thống quản lý bãi xe thông minh — đặc biệt là yêu cầu real-time, quản lý dữ liệu phức tạp, và trải nghiệm người dùng mượt mà:

- **Component-based Architecture và Custom Hooks**: UI được chia thành components độc lập, tái sử dụng. Logic stateful phức tạp (xác thực, đặt chỗ, kết nối WebSocket, dữ liệu bãi xe) được đóng gói trong custom hooks — mỗi hook encapsulate cả state, side effects, và derived data, cung cấp API đơn giản cho components sử dụng. Pattern này cho phép tách biệt UI rendering khỏi business logic, giúp code dễ test và bảo trì.
- **State management đa tầng**: Ba cấp độ state được quản lý bằng công cụ phù hợp nhất — **local state** (useState cho form inputs, UI toggles, loading indicators), **global client state** (Redux Toolkit cho cross-component data như auth status, notifications, WebSocket connection), và **server state** (React Query cho API data với automatic caching, background sync, và optimistic updates). Mô hình 3 tầng này đảm bảo mỗi loại dữ liệu có lifecycle riêng và được quản lý tối ưu, tránh over-engineering khi dùng Redux cho mọi thứ.
- **Real-time data flow qua WebSocket**: Kết nối WebSocket native đến realtime-service-go với auto-reconnect (exponential backoff khi mất kết nối). Khi trạng thái ô đỗ thay đổi (xe vào/ra thông qua cảm biến IoT), realtime-service broadcast event → frontend nhận message và dispatch vào Redux store → React tự động re-render chỉ những ô đỗ thay đổi nhờ Virtual DOM diff. Toàn bộ quá trình từ cảm biến đến màn hình diễn ra trong vài trăm milliseconds, đem lại bản đồ bãi xe "sống" cho người dùng.
- **Kiểm tra kiểu dữ liệu toàn diện với TypeScript**: Mọi cấu trúc dữ liệu (User, Booking, ParkingSlot, Vehicle, Notification, ChatMessage) được định nghĩa bằng TypeScript interfaces, đảm bảo tính nhất quán giữa kiểu dữ liệu frontend và API schema backend. Zod validation schemas tự động suy luận kiểu TypeScript, tạo "nguồn thông tin duy nhất" cho cả validation lẫn kiểu dữ liệu — một thay đổi trong schema tự động lan truyền đến cả form validation và component props.
- **Xác thực form theo schema**: React Hook Form (tối ưu hiệu năng, dùng uncontrolled components — chỉ re-render field thay đổi thay vì toàn bộ form) kết hợp Zod (định nghĩa lược đồ ưu tiên TypeScript) đảm bảo: kiểm tra kiểu dữ liệu tự động từ schema, quy tắc xác thực tập trung tại một nơi, hiệu năng cao cho các form phức tạp (đặt chỗ, đăng ký, cài đặt), và thông báo lỗi hiển thị theo thời gian thực giúp người dùng sửa lỗi nhanh chóng.

**Ưu điểm nổi bật trong thực tế ParkSmart:**

- Hiệu năng render cao nhờ Virtual DOM và Concurrent Features, đặc biệt quan trọng cho bản đồ bãi xe real-time với hàng trăm slot cập nhật liên tục qua WebSocket.
- Hệ sinh thái phong phú cho phép tích hợp nhanh các tính năng phức tạp (real-time maps, charts, QR codes, dark mode, form validation) mà không cần phát triển từ đầu.
- TypeScript phát hiện lỗi sớm tại compile time, giảm runtime bugs đáng kể trong ứng dụng quy mô lớn với nhiều data flows.
- shadcn/ui cung cấp UI components chất lượng cao, tuân thủ WAI-ARIA accessibility, và tùy biến hoàn toàn theo design system của dự án.
- DevTools mạnh mẽ (React DevTools + Redux DevTools) hỗ trợ debug hiệu quả các luồng dữ liệu phức tạp.

**Nhược điểm và cách khắc phục:**

- **Decision fatigue**: React không quy định cấu trúc project, routing, hay state management — nhà phát triển phải tự chọn. → _Khắc phục_: ParkSmart thiết lập convention rõ ràng với feature-based architecture, Service Layer Pattern, và hybrid state management strategy từ đầu dự án.
- **Build tooling phức tạp**: Cần Vite để biên dịch JSX và TypeScript. → _Khắc phục_: Vite cung cấp cấu hình mặc định tốt, dev server khởi động dưới 1 giây, HMR tức thì — trải nghiệm phát triển mượt mà.
- **Không có SSR/SSG**: SPA thuần túy không hỗ trợ Server-Side Rendering. → _Khắc phục_: ParkSmart là ứng dụng quản lý bãi xe nội bộ, không cần SEO — SPA là lựa chọn phù hợp, đơn giản hơn Next.js, và hiệu năng client-side đáp ứng tốt nhu cầu real-time.

---

## 2.8. Chatbot

### 2.8.1. Giới thiệu Chatbot

Chatbot (hay chương trình hội thoại tự động) là phần mềm mô phỏng cuộc trò chuyện của con người thông qua giao diện text hoặc voice. Chatbot có thể chia thành hai loại chính: **Rule-based chatbot** (hoạt động dựa trên tập luật if-then cố định, chỉ trả lời được các câu hỏi đã được lập trình sẵn) và **AI-powered chatbot** (sử dụng trí tuệ nhân tạo, đặc biệt là Natural Language Understanding — NLU, để hiểu ý định người dùng và phản hồi linh hoạt).

Trong hệ thống ParkSmart, chatbot đóng vai trò **trợ lý ảo thông minh (Virtual Assistant)**, cho phép người dùng tương tác bằng **tiếng Việt tự nhiên** để thực hiện các tác vụ liên quan đến bãi xe: tra cứu chỗ trống, đặt chỗ qua hội thoại, kiểm tra trạng thái booking, hỏi đáp về giá cả, quy định, giờ hoạt động, và báo sự cố. Chatbot hoạt động 24/7, giảm tải đáng kể cho nhân viên tư vấn, đồng thời cải thiện trải nghiệm người dùng.

**Công nghệ LLM sử dụng:**

ParkSmart Chatbot sử dụng mô hình ngôn ngữ lớn **Google Gemini** [14] phiên bản **gemini-3-flash-preview** thông qua API `google-generativeai` SDK. Gemini là mô hình đa phương thức (multimodal) do Google DeepMind phát triển, hỗ trợ hiểu và sinh văn bản đa ngôn ngữ bao gồm tiếng Việt. Phiên bản "Flash" được tối ưu cho **tốc độ phản hồi nhanh** với chi phí thấp, phù hợp cho ứng dụng chatbot cần response time dưới 2 giây. Cấu hình: `temperature=0.3` (ưu tiên độ chính xác, giảm sáng tạo ngẫu nhiên), `max_tokens=1024` (giới hạn độ dài phản hồi). LLM được sử dụng cho hai mục đích: **(1) Intent Classification** — phân loại ý định người dùng, và **(2) Response Generation** — sinh câu trả lời tự nhiên bằng tiếng Việt.

**Ưu điểm:**

- Hoạt động 24/7 không cần nhân viên trực, xử lý đồng thời nhiều user conversation.
- Hiểu ngôn ngữ tự nhiên tiếng Việt nhờ LLM, không cần người dùng nhập đúng format.
- Có thể thực hiện hành động (action execution) — không chỉ trả lời mà còn thao tác trực tiếp trên hệ thống (đặt chỗ, hủy booking, thanh toán) thông qua API calls.
- Booking Wizard multi-step cho phép đặt chỗ hoàn chỉnh qua hội thoại với dẫn dắt từng bước.
- Proactive notifications — chủ động thông báo cho user (nhắc hẹn, khuyến mãi) không cần user hỏi trước.

**Nhược điểm:**

- **Hiểu sai ý định**: Tiếng Việt có nhiều từ đa nghĩa, lối viết không dấu, viết tắt, biến thể vùng miền — LLM có thể phân loại sai intent, đặc biệt với câu hỏi mập mờ.
- **Phụ thuộc LLM provider**: Hệ thống phụ thuộc vào Google Gemini API. Nếu API down hoặc thay đổi policy, chatbot mất khả năng hoạt động. Chi phí API tăng theo lượng sử dụng.
- **Latency**: Mỗi API call đến Gemini mất 0,5–2 giây tùy tải, ảnh hưởng đến trải nghiệm real-time.
- **Hallucination**: LLM có thể sinh thông tin sai (ví dụ: đưa giá sai, thông tin bãi xe không chính xác) nếu không có cơ chế safety validation kiểm tra.
- **Cần safety rules**: Phải có lớp bảo vệ (permission check, rate limiting, action validation) để ngăn chatbot thực hiện hành động trái phép hoặc bị lạm dụng.

### 2.8.2. Kiến trúc hệ thống Chatbot AI tích hợp LLM

#### a) Kiến trúc tổng quan Chatbot AI

Một hệ thống Chatbot AI hoàn chỉnh thường được xây dựng theo kiến trúc pipeline (đường ống xử lý tuần tự) gồm 4 thành phần chính, mỗi thành phần đảm nhận một giai đoạn trong quá trình chuyển đổi từ đầu vào ngôn ngữ tự nhiên sang phản hồi có ý nghĩa:

```
User Input (ngôn ngữ tự nhiên)
  │
  ▼
┌──────────────────────────────────────────────────────────┐
│  NLU (Natural Language Understanding)                    │
│  • Intent Classification — phân loại ý định              │
│  • Entity Extraction — trích xuất thực thể               │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│  Dialog Management (DM)                                  │
│  • Dialog State Tracking — theo dõi trạng thái           │
│  • Policy Decision — quyết định hành động tiếp theo      │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│  Action Execution                                        │
│  • Gọi API, truy vấn database, kích hoạt quy trình      │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────────────────┐
│  NLG (Natural Language Generation)                       │
│  • Sinh phản hồi ngôn ngữ tự nhiên                       │
└──────────────────────┬───────────────────────────────────┘
                       │
                       ▼
Bot Response → User
```

- **NLU — Natural Language Understanding** (Hiểu ngôn ngữ tự nhiên): Tầng đầu tiên phân tích đầu vào của người dùng, thực hiện hai tác vụ chính: *Intent Classification* (phân loại ý định — xác định người dùng muốn gì) và *Entity Extraction* (trích xuất thực thể — nhận diện thông tin cụ thể như tên, số, ngày giờ, địa điểm). Trong hệ thống truyền thống, NLU dùng mô hình phân loại văn bản (SVM, Random Forest) kết hợp Named Entity Recognition (NER). Với LLM hiện đại, cả hai tác vụ có thể thực hiện trong một lần gọi mô hình qua prompt engineering.

- **Dialog Management — DM** (Quản lý hội thoại): Tầng quản lý trạng thái hội thoại qua nhiều lượt trao đổi (multi-turn conversation), thực hiện *Dialog State Tracking* (lưu trữ thông tin đã thu thập) và *Policy Decision* (quyết định hành động tiếp theo — hỏi thêm, thực thi, hay trả lời). Hai kiểu DM phổ biến: *rule-based* (kịch bản định trước, phù hợp domain hẹp) và *data-driven* (dựa trên mô hình học máy, linh hoạt hơn).

- **Action Execution** (Thực thi hành động): Khi DM quyết định cần hành động cụ thể (đặt chỗ, truy vấn thông tin), tầng này gọi API bên ngoài, truy vấn cơ sở dữ liệu, hoặc kích hoạt quy trình nghiệp vụ — đóng vai trò cầu nối giữa chatbot và hệ thống backend.

- **NLG — Natural Language Generation** (Sinh ngôn ngữ tự nhiên): Tầng cuối chuyển đổi kết quả xử lý thành phản hồi tự nhiên. Phương pháp truyền thống dùng template-based generation (mẫu câu định sẵn); LLM cho phép sinh phản hồi linh hoạt, tự nhiên hơn, điều chỉnh được giọng điệu và ngữ cảnh.

#### b) Kiến trúc Transformer — nền tảng của LLM hiện đại

Large Language Model (Mô hình ngôn ngữ lớn — LLM) là nền tảng công nghệ cốt lõi cho chatbot AI thế hệ mới, được xây dựng trên kiến trúc **Transformer** do Vaswani và cộng sự giới thiệu năm 2017 trong bài báo "Attention Is All You Need". Các đặc điểm kiến trúc cốt lõi:

- **Self-Attention** (Tự chú ý): Cơ chế cho phép mỗi token (đơn vị từ/ký tự) trong chuỗi đầu vào tính toán mức độ liên quan với mọi token khác. Mỗi token được biểu diễn thành 3 vector: Query (truy vấn), Key (khóa), và Value (giá trị). Điểm attention được tính theo công thức:

$$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right)V$$

  Trong đó $d_k$ là chiều của vector Key; phép chia cho $\sqrt{d_k}$ ngăn tích vô hướng quá lớn khi chiều cao, giúp gradient ổn định trong quá trình huấn luyện.

- **Multi-Head Attention** (Chú ý đa đầu): Thay vì một phép Self-Attention duy nhất, Transformer chạy song song nhiều "head" — mỗi head học cách chú ý đến khía cạnh ngữ nghĩa khác nhau (cú pháp, ngữ nghĩa, quan hệ xa). Kết quả các head được nối (concatenate) và chiếu tuyến tính, cho phép mô hình nắm bắt đa dạng mối quan hệ trong ngôn ngữ.

- **Kiến trúc Encoder-Decoder và các biến thể**: Transformer gốc gồm Encoder (mã hóa chuỗi đầu vào thành biểu diễn ngữ cảnh) và Decoder (sinh chuỗi đầu ra tự hồi quy — autoregressive). Các biến thể hiện đại phát triển theo 3 hướng: *Encoder-only* (BERT — chuyên phân loại, NER, hiểu ngữ nghĩa hai chiều), *Decoder-only* (GPT, Gemini — sinh văn bản tự hồi quy, nền tảng hầu hết LLM hiện đại), và *Encoder-Decoder* (T5, BART — kết hợp cả hai, phù hợp dịch thuật và tóm tắt).

- **Pre-training → Fine-tuning → Prompt Engineering**: Ba giai đoạn phát triển LLM. *Pre-training* (Tiền huấn luyện) trên tập dữ liệu văn bản khổng lồ để học biểu diễn ngôn ngữ tổng quát. *Fine-tuning* (Tinh chỉnh) trên dữ liệu chuyên biệt cho tác vụ cụ thể. *Prompt Engineering* (Kỹ thuật thiết kế prompt) — viết hướng dẫn (system prompt, few-shot examples) để điều khiển hành vi LLM mà không cần huấn luyện lại, là phương pháp chủ đạo khi sử dụng LLM qua API.

#### c) Google Gemini — LLM đa phương thức

Google Gemini là dòng LLM đa phương thức (multimodal) do Google DeepMind phát triển, có khả năng xử lý đồng thời nhiều loại dữ liệu: văn bản (text), hình ảnh (image), âm thanh (audio), và video. Khác với các LLM thuần văn bản như GPT-3, Gemini được thiết kế đa phương thức ngay từ kiến trúc nền tảng (natively multimodal), không phải ghép nối module riêng lẻ.

Gemini cung cấp nhiều phiên bản phục vụ các nhu cầu khác nhau: **Ultra** — mô hình lớn nhất, hiệu năng cao nhất cho tác vụ phức tạp (suy luận đa bước, phân tích code); **Pro** — cân bằng giữa hiệu năng và chi phí, phù hợp đa số ứng dụng doanh nghiệp; **Flash** — tối ưu tốc độ phản hồi và chi phí API, thiết kế cho ứng dụng cần low-latency (độ trễ thấp) như chatbot real-time.

Giao diện lập trình (API) của Gemini hỗ trợ ba chế độ tương tác chính: *Prompt-based interaction* — giao tiếp qua system prompt (hướng dẫn hành vi) kết hợp user prompt (đầu vào người dùng), hỗ trợ multi-turn conversation natively; *Structured output (JSON mode)* — yêu cầu mô hình trả kết quả theo JSON schema cụ thể, quan trọng cho tích hợp backend khi cần parse output có cấu trúc; *Streaming response* — trả kết quả từng phần ngay khi sinh được, giảm perceived latency (độ trễ cảm nhận) cho ứng dụng real-time.

#### d) Kiến trúc Hexagonal (Ports & Adapters) cho Chatbot Service

Hexagonal Architecture (Kiến trúc lục giác), còn gọi là Ports and Adapters, là pattern kiến trúc phần mềm do Alistair Cockburn đề xuất. Pattern này đặc biệt phù hợp cho hệ thống chatbot tích hợp LLM — nơi các phụ thuộc bên ngoài (LLM provider, database, external APIs) thay đổi thường xuyên theo thị trường và công nghệ:

```
                    ┌──────────────────────────┐
    Inbound         │    Application Layer     │         Outbound
    Ports           │  ┌────────────────────┐  │         Ports
                    │  │                    │  │
  ┌──────────┐     │  │   Domain Layer     │  │     ┌──────────┐
  │ HTTP API ├────►│  │  (Business Rules)  │  ├────►│LLM Client│
  └──────────┘     │  │  Intent policies   │  │     └──────────┘
  ┌──────────┐     │  │  Confidence rules  │  │     ┌──────────┐
  │ Message  ├────►│  │  Safety policies   │  ├────►│ Database │
  │  Queue   │     │  │  Dialog state      │  │     └──────────┘
  └──────────┘     │  │                    │  │     ┌──────────┐
                    │  └────────────────────┘  ├────►│ External │
                    │    Use Cases / Services  │     │   APIs   │
                    └──────────────────────────┘     └──────────┘
                           Adapters                    Adapters
```

Kiến trúc gồm 3 tầng đồng tâm:

- **Domain Layer** (Tầng miền — Ports): Chứa business rules thuần túy — định nghĩa các loại intent, quy tắc tính confidence, chính sách an toàn, exceptions — hoàn toàn độc lập với framework và infrastructure bên ngoài.

- **Application Layer** (Tầng ứng dụng): Chứa use cases và orchestration logic — điều phối luồng xử lý từ nhận tin nhắn đến trả phản hồi, gọi các port để tương tác với thế giới bên ngoài.

- **Infrastructure Layer** (Tầng hạ tầng — Adapters): Chứa implementation cụ thể cho các port: LLM client (kết nối Gemini, OpenAI), database access, message queue consumer, external API clients.

Lợi ích chính của kiến trúc này cho chatbot service: **Thay thế LLM provider không ảnh hưởng logic nghiệp vụ** — LLM client chỉ là một adapter, chuyển provider chỉ cần thay adapter mà không chạm pipeline xử lý; **Testability cao** — Domain layer thuần túy, kiểm thử đơn vị cho confidence scoring hay safety validation mà không cần kết nối LLM thật; **Phân tách rõ ràng** — quy tắc nghiệp vụ nằm trong Domain, kết nối bên ngoài nằm trong Infrastructure, dễ kiểm soát và thay đổi độc lập.


### 2.8.3. Lý do lựa chọn Google Gemini cho ParkSmart

Chatbot là thành phần phụ thuộc nặng vào LLM — việc lựa chọn provider ảnh hưởng trực tiếp đến chất lượng NLU, tốc độ phản hồi, chi phí vận hành, và khả năng xử lý tiếng Việt. Bảng dưới đây so sánh các LLM provider đã cân nhắc:

**a) So sánh LLM providers:**

| Tiêu chí                    | **Google Gemini Flash** |  OpenAI GPT-4   | Anthropic Claude |  Llama (Open-source)  |
| --------------------------- | :---------------------: | :-------------: | :--------------: | :-------------------: |
| Tốc độ phản hồi             |       ⭐⭐⭐⭐⭐        |     ⭐⭐⭐      |      ⭐⭐⭐      | ⭐⭐⭐⭐ (on-premise) |
| Chi phí API                 |          Thấp           | Cao (gấp 3–5×)  |  Cao (gấp 2–3×)  | Free (nhưng cần GPU)  |
| Hỗ trợ tiếng Việt           |        ⭐⭐⭐⭐         |   ⭐⭐⭐⭐⭐    |     ⭐⭐⭐⭐     |        ⭐⭐⭐         |
| Streaming response          |          ✅ Có          |      ✅ Có      |      ✅ Có       |         ✅ Có         |
| Free tier / Education       |       ✅ Generous       |   ⚠️ Hạn chế    |    ⚠️ Hạn chế    |        ✅ Free        |
| JSON structured output      |         ✅ Tốt          |   ✅ Rất tốt    |      ✅ Tốt      |   ⚠️ Không ổn định    |
| Đa phương thức (multimodal) |     ✅ Text + Image     | ✅ Text + Image | ✅ Text + Image  |     ⚠️ Tùy model      |

**Gemini Flash được chọn cho ParkSmart vì các lý do:**

1. **Tốc độ phản hồi nhanh nhất**: Phiên bản "Flash" được Google tối ưu cho low-latency, response time trung bình 0,5–1 giây — quan trọng cho chatbot cần phản hồi real-time. GPT-4 và Claude có latency cao hơn (1–3 giây) do model size lớn hơn.
2. **Chi phí thấp, phù hợp đồ án**: Gemini cung cấp free tier generous và pricing thấp nhất trong các LLM thương mại. GPT-4 có chất lượng output tổng thể tốt nhất nhưng chi phí API cao gấp 3–5 lần — không phù hợp ngân sách đồ án tốt nghiệp. Anthropic Claude tương tự về chi phí cao.
3. **Hỗ trợ tiếng Việt đủ tốt**: Gemini hiểu và sinh tiếng Việt tự nhiên, đủ cho bài toán phân loại ý định và tạo phản hồi trong domain bãi xe. Tuy GPT-4 xử lý tiếng Việt tốt hơn ở các trường hợp ngoại biên, sự khác biệt không đáng kể khi ParkSmart hoạt động trong domain hẹp với 16 loại ý định cụ thể, vốn từ chuyên biệt.
4. **Cloud LLM thay vì tự triển khai**: ParkSmart chọn cloud API thay vì tự host Llama (mã nguồn mở) vì: không cần đầu tư GPU server (chi phí ~$1.000+/tháng cho GPU cloud), không cần quản lý hạ tầng phục vụ mô hình, và chất lượng đầu ra của Gemini vượt trội so với Llama ở tiếng Việt. Đánh đổi: phụ thuộc tính khả dụng của nhà cung cấp — được giảm thiểu nhờ Kiến trúc Lục giác cho phép thay thế bộ kết nối LLM khi cần.

**b) Lý do chọn Hexagonal Architecture cho Chatbot:**

Chatbot service sử dụng Hexagonal Architecture — phân tách rõ ràng Domain (business rules), Application (orchestration), và Infrastructure (LLM, APIs, database) — thay vì layered architecture truyền thống. Lý do:

- **Thay đổi LLM provider không ảnh hưởng business logic**: Gemini client là một adapter trong Infrastructure layer. Nếu cần chuyển sang OpenAI hoặc Claude (do pricing thay đổi, chất lượng, etc.), chỉ cần viết adapter mới mà không chạm vào pipeline logic.
- **Testability cao**: Domain layer không phụ thuộc external services → unit test thuần túy cho confidence scoring, safety validation, wizard state machine mà không cần mock LLM.
- **Phân tách rõ ràng**: Intent classification policies, confidence thresholds, rate limiting rules nằm trong Domain — dễ audit và điều chỉnh. LLM calls, API calls, database queries nằm trong Infrastructure — dễ thay thế hoặc mock.

### 2.8.4. Các kỹ thuật chính áp dụng trong ParkSmart

Thay vì đi sâu vào chi tiết implementation, phần này tóm tắt các kỹ thuật chatbot cốt lõi ở mức kiến trúc:

- **Natural Language Understanding đa tầng**: NLU pipeline kết hợp 3 tác vụ: Intent Classification (phân loại 16 loại ý định qua LLM), Entity Extraction (trích xuất floor, zone, plate, time bằng LLM + regex pattern matching), và Sentiment Analysis (phát hiện frustration để kích hoạt human handoff khi cần). Ba tác vụ hoạt động bổ trợ, tăng độ chính xác tổng thể so với chỉ dùng LLM đơn thuần.
- **Hybrid Confidence Scoring kết hợp 3 nguồn tin cậy**: Confidence không chỉ dựa vào LLM (dễ hallucinate) mà kết hợp entity extraction và conversation context (xem công thức chi tiết bên dưới). Cơ chế Confidence Gate 3 mức (Execute ≥ 0.75, Confirm 0.50–0.75, Clarify < 0.50) với ngưỡng cao hơn (≥ 0.85) cho high-stakes actions (hủy booking, thanh toán) — ngăn chatbot thực hiện hành động sai khi chưa đủ chắc chắn.
- **Multi-step Booking Wizard qua hội thoại tự nhiên**: Luồng đặt chỗ 3 bước (chọn tầng → chọn zone → xác nhận) với state machine lưu trong conversation memory. User có thể nhập tự nhiên hoặc chọn từ gợi ý, hỗ trợ cancel/back tại mọi bước, tự động timeout sau 5 phút không phản hồi.
- **Safety validation đa lớp**: Trước mỗi action execution, 3 lớp kiểm tra: Permission Check (user có quyền? đã đăng nhập?), Rate Limiting (giới hạn actions/phút chống spam), và Action Validation (dữ liệu hợp lệ? biển số đúng format?). Chỉ khi cả 3 lớp pass, action mới được thực thi — đảm bảo chatbot không bị lạm dụng.
- **Proactive notifications qua message queue**: Chatbot service subscribe RabbitMQ để nhận events hệ thống (booking sắp hết hạn, thanh toán thành công, slot thay đổi) và chủ động gửi thông báo đến user qua chat interface mà không cần user hỏi trước. Cơ chế cooldown và priority system ngăn spam notifications, ưu tiên thông báo quan trọng (booking expiration) hơn thông báo thường.
- **AI observability metrics**: Hệ thống giám sát chất lượng chatbot qua các chỉ số: intent mismatch rate (tỷ lệ hiểu sai), clarification rate (tỷ lệ cần hỏi lại), response time P95, wizard completion rate, và human handoff rate. Metrics được log structured JSON, cho phép phát hiện sớm suy giảm chất lượng NLU và cải thiện liên tục.

**Pipeline 7 giai đoạn xử lý tin nhắn:**

Mỗi tin nhắn của người dùng được xử lý tuần tự qua 7 giai đoạn (stages):

1. **Stage 0 — Wizard Handler**: Kiểm tra xem user có đang trong luồng multi-step (Booking Wizard) không. Nếu có, xử lý input theo bước hiện tại và bỏ qua Stage 1.
2. **Stage 1 — Intent Detection**: Pipeline 3 bước: (1) LLM phân loại intent từ 16 loại, (2) trích xuất entities bằng LLM + regex, (3) tính Hybrid Confidence kết hợp 3 nguồn.
3. **Stage 2 — Confidence Gate**: Cổng quyết định dựa trên Hybrid Confidence — thực thi ngay (≥ 0.75), hỏi xác nhận (0.50–0.75), hoặc yêu cầu làm rõ (< 0.50). High-stakes actions (hủy, thanh toán) yêu cầu ≥ 0.85.
4. **Stage 3 — Safety Validation**: Kiểm tra an toàn 3 lớp: Permission Check (quyền truy cập), Rate Limiting (chống spam), Action Validation (dữ liệu hợp lệ).
5. **Stage 4 — Action Execution**: Gọi backend APIs qua HTTP — Booking Service, Parking Service, Vehicle Service, Payment Service — để thực thi hành động.
6. **Stage 5 — Response Generation**: LLM (Gemini) sinh phản hồi tự nhiên bằng tiếng Việt từ action result + user context + system prompt, kèm gợi ý câu hỏi tiếp theo.
7. **Stage 6 — Memory**: Lưu toàn bộ turn vào conversation memory (sliding window N turns gần nhất), cập nhật context score cho Hybrid Confidence ở Stage 1, persist vào database cho analytics.

**Công thức Hybrid Confidence:**

Hệ thống sử dụng công thức **Hybrid Confidence** (Độ tin cậy kết hợp) để quyết định mức chắc chắn khi phân loại intent:

$$\text{Hybrid Confidence} = 0.5 \times C_{\text{LLM}} + 0.3 \times C_{\text{entity}} + 0.2 \times C_{\text{context}}$$

Trong đó:

- $C_{\text{LLM}}$ (0.0–1.0): Độ tin cậy từ LLM khi phân loại intent — xác suất mà LLM "tin" rằng intent đã phân loại là đúng.
- $C_{\text{entity}}$ (0.0–1.0): Tỷ lệ entity bắt buộc được trích xuất thành công. Ví dụ: intent "BOOKING_CREATE" yêu cầu `floor`, `plate` — trích xuất được cả hai thì $C_{\text{entity}} = 1.0$, chỉ được một thì $C_{\text{entity}} = 0.5$.
- $C_{\text{context}}$ (0.0–1.0): Điểm ngữ cảnh hội thoại — nếu user đã hỏi về booking ở tin nhắn trước và tiếp tục hỏi liên quan, context score cao hơn (intent consistent).

Ý nghĩa: LLM hiểu ngữ nghĩa (trọng số 50%), entity extraction xác nhận qua dữ liệu cụ thể (30%), context đảm bảo tính nhất quán hội thoại (20%). Nếu LLM phân loại đúng intent nhưng không trích xuất được entity nào, hybrid confidence sẽ thấp hơn, kích hoạt bước clarify thay vì execute sai.

**16 loại Intent:**

Chatbot ParkSmart nhận diện **16 loại intent** (ý định) khác nhau:

_Bảng 2.1: Danh sách 16 loại intent của Chatbot ParkSmart_

| #   | Intent Type         | Mô tả            | Ví dụ câu nói                     |
| --- | ------------------- | ---------------- | --------------------------------- |
| 1   | `GREETING`          | Chào hỏi         | "Xin chào", "Hello"               |
| 2   | `FAREWELL`          | Tạm biệt         | "Cảm ơn, tạm biệt"                |
| 3   | `SLOT_INQUIRY`      | Hỏi chỗ trống    | "Còn chỗ trống không?"            |
| 4   | `BOOKING_CREATE`    | Đặt chỗ mới      | "Tôi muốn đặt chỗ tầng 1"         |
| 5   | `BOOKING_CHECK`     | Kiểm tra booking | "Booking của tôi thế nào?"        |
| 6   | `BOOKING_CANCEL`    | Hủy booking      | "Hủy booking giúp tôi"            |
| 7   | `PRICING_INQUIRY`   | Hỏi giá          | "Giá gửi xe bao nhiêu?"           |
| 8   | `HOURS_INQUIRY`     | Giờ hoạt động    | "Bãi xe mở cửa mấy giờ?"          |
| 9   | `DIRECTION_INQUIRY` | Hỏi đường        | "Bãi xe ở đâu?"                   |
| 10  | `PAYMENT_INQUIRY`   | Hỏi thanh toán   | "Thanh toán bằng gì?"             |
| 11  | `CHECKIN_INQUIRY`   | Hỏi check-in     | "Check-in như thế nào?"           |
| 12  | `CHECKOUT_INQUIRY`  | Hỏi check-out    | "Tôi muốn ra, làm sao?"           |
| 13  | `INCIDENT_REPORT`   | Báo sự cố        | "Xe tôi bị trầy"                  |
| 14  | `FEEDBACK`          | Góp ý            | "Bãi xe sạch quá!"                |
| 15  | `HELP`              | Trợ giúp         | "Giúp tôi với"                    |
| 16  | `UNKNOWN`           | Không xác định   | Fallback khi không nhận diện được |

**Booking Wizard (Multi-step flow):**

Booking Wizard là luồng hội thoại đặc biệt cho phép người dùng **đặt chỗ hoàn chỉnh qua chatbot** với dẫn dắt từng bước:

1. **Bước 1 — Chọn tầng (Floor)**: Bot hỏi "Bạn muốn đỗ tầng nào?" → Hiển thị danh sách tầng + số chỗ trống mỗi tầng.
2. **Bước 2 — Chọn khu vực (Zone)**: Bot hiển thị các zone của tầng đã chọn + số chỗ trống mỗi zone.
3. **Bước 3 — Xác nhận và đặt chỗ (Book)**: Bot gọi Booking Service API để tạo booking, trả về thông tin booking + mã QR.

Tại bất kỳ bước nào, user có thể nói "hủy" hoặc "quay lại" để cancel/resume wizard. Trạng thái wizard được lưu trong conversation memory, cho phép user thoát rồi quay lại tiếp tục từ bước đã dừng. Wizard tự động timeout sau 5 phút không phản hồi.

**Ưu điểm nổi bật của Chatbot ParkSmart:**

- Pipeline 7 giai đoạn (Wizard → Intent → Confidence Gate → Safety → Action → Response → Memory) đảm bảo mỗi message được xử lý tuần tự, có kiểm soát, không thực hiện action sai.
- Hybrid Confidence giảm thiểu hallucination — không chỉ tin LLM mà cross-verify bằng entity extraction và conversation context.
- Hexagonal Architecture cho phép thay đổi LLM provider mà không ảnh hưởng business logic — quan trọng khi thị trường LLM thay đổi nhanh.
- Booking Wizard biến quy trình đặt chỗ phức tạp thành hội thoại tự nhiên, dẫn dắt user từng bước.
- Tích hợp sẵn safety validation và rate limiting — ngăn lạm dụng chatbot để spam actions.

**Nhược điểm và cách khắc phục:**

- **Phụ thuộc Google Gemini API**: Nếu API down hoặc thay đổi pricing, chatbot mất khả năng NLU. → _Khắc phục_: Hexagonal Architecture cho phép swap sang LLM khác (OpenAI, Claude); có thể bổ sung rule-based fallback cho các intent phổ biến khi LLM không khả dụng.
- **Latency kép (2 lần gọi LLM/message)**: Mỗi message gọi LLM 2 lần (intent classification + response generation), tổng ~1–3 giây. → _Khắc phục_: Gemini Flash tối ưu latency; Redis cache cho intent patterns phổ biến; streaming response cải thiện perceived latency.
- **Trường hợp ngoại biên tiếng Việt**: Viết không dấu, viết tắt, biến thể vùng miền có thể gây phân loại sai ý định. → _Khắc phục_: Hybrid Confidence tự động kích hoạt làm rõ ngữa khi trích xuất thực thể không khớp; ngữ cảnh hội thoại giúp suy luận ý định từ lịch sử.
- **Hallucination risk**: LLM có thể sinh thông tin sai về giá, giờ, quy định bãi xe. → _Khắc phục_: Action execution luôn gọi API lấy dữ liệu thật từ backend (không dựa vào LLM memory); safety validation kiểm tra trước khi trả lời.

---

## 2.9. Unity — Game Engine và Mô phỏng 3D

Một hệ thống bãi xe thông minh với nhiều thành phần phức tạp (camera nhận diện biển số, cổng barrier tự động, WebSocket real-time, IoT sensors) đòi hỏi một **môi trường mô phỏng** để kiểm thử toàn bộ pipeline trước khi triển khai phần cứng thực tế. Phần này trình bày Unity — game engine được sử dụng làm nền tảng xây dựng bộ mô phỏng 3D (Digital Twin) cho bãi giữ xe ParkSmart.

### 2.9.1. Giới thiệu Unity

Unity là game engine đa nền tảng được phát triển bởi Unity Technologies [31] từ năm 2005, hiện là một trong những công cụ phát triển ứng dụng 3D phổ biến nhất thế giới với hơn 1.5 triệu nhà phát triển hoạt động hàng tháng. Mặc dù khởi đầu là engine phát triển trò chơi, Unity đã mở rộng phạm vi ứng dụng sang nhiều lĩnh vực chuyên nghiệp: mô phỏng kỹ thuật (engineering simulation), Digital Twin cho nhà máy và đô thị, thực tế ảo và thực tế tăng cường (VR/AR), trực quan hóa kiến trúc (architectural visualization), và mô phỏng phương tiện tự hành (autonomous vehicle simulation).

Unity sử dụng ngôn ngữ lập trình **C#** chạy trên nền tảng .NET Standard 2.1, kết hợp trình biên dịch **IL2CPP** (Intermediate Language To C++) chuyển đổi mã C# thành mã C++ native khi build — tăng hiệu năng thực thi đáng kể so với trình thông dịch Mono truyền thống. Phiên bản sử dụng trong ParkSmart là **Unity 2022.3.62f3 LTS** (Long Term Support) — phiên bản hỗ trợ dài hạn được Unity Technologies cam kết duy trì ổn định trong vòng 2 năm, đảm bảo không có breaking changes ảnh hưởng đến dự án đang phát triển.

Kiến trúc cốt lõi của Unity dựa trên mô hình **Component-based**: mỗi đối tượng trong thế giới 3D là một **GameObject** (thực thể rỗng), và hành vi của nó được định nghĩa bởi các **Component** gắn vào — ví dụ: Transform (vị trí, xoay, co giãn), MeshRenderer (hiển thị hình dạng 3D), Rigidbody (vật lý), Collider (va chạm), và các script C# kế thừa lớp **MonoBehaviour** (định nghĩa logic tùy chỉnh). MonoBehaviour cung cấp vòng đời (lifecycle) rõ ràng với các phương thức Awake() → Start() → Update() → FixedUpdate() → OnDestroy(), cho phép lập trình viên kiểm soát chính xác thời điểm khởi tạo, cập nhật mỗi frame, và dọn dẹp tài nguyên.

### 2.9.2. Lý do lựa chọn Unity cho ParkSmart

**Khái niệm Digital Twin và vai trò trong ParkSmart:**

Digital Twin (bản sao kỹ thuật số) là khái niệm tạo một mô hình ảo phản ánh trung thực hệ thống vật lý thực, có khả năng nhận dữ liệu real-time và mô phỏng hành vi của hệ thống gốc. Trong lĩnh vực sản xuất và logistics, Digital Twin được sử dụng rộng rãi bởi các tập đoàn lớn như BMW (mô phỏng dây chuyền sản xuất), Hyundai (mô phỏng đô thị thông minh), và NASA (mô phỏng tàu vũ trụ) — trong đó Unity là một trong những nền tảng được lựa chọn phổ biến nhất nhờ khả năng kết hợp rendering 3D chất lượng cao, hệ thống vật lý, và networking trong một môi trường tích hợp.

ParkSmart sử dụng Unity làm **Digital Twin cho bãi giữ xe**: mô phỏng 3D toàn bộ bãi xe 158 ô đỗ trên 2 tầng, xe ra vào qua cổng barrier, 6 camera ảo streaming hình ảnh, và hệ thống IoT mô phỏng — tất cả kết nối real-time với hệ thống backend microservices thông qua HTTP và WebSocket. Vai trò chính của Digital Twin trong dự án là **Development và Testing environment**: cho phép kiểm tra toàn bộ pipeline AI (nhận diện biển số từ camera ảo, phát hiện trạng thái ô đỗ), luồng check-in/check-out (xe đến cổng → nhận diện biển số → xác minh booking → mở barrier), và đồng bộ real-time (WebSocket slot status updates) — tất cả mà không cần phần cứng camera, barrier, hay ESP32 thực tế.

**So sánh Unity với các lựa chọn thay thế:**

| Tiêu chí                  | Unity        | Unreal Engine | Godot 4      | Three.js (Web) |
| ------------------------- | ------------ | ------------- | ------------ | -------------- |
| Ngôn ngữ lập trình        | C#           | C++/Blueprint | GDScript/C#  | JavaScript     |
| Chất lượng rendering 3D   | ⭐⭐⭐⭐     | ⭐⭐⭐⭐⭐    | ⭐⭐⭐       | ⭐⭐⭐         |
| Độ dốc học tập            | ⭐⭐⭐⭐     | ⭐⭐          | ⭐⭐⭐⭐⭐   | ⭐⭐⭐         |
| Tích hợp HTTP/WebSocket   | ⭐⭐⭐⭐     | ⭐⭐          | ⭐⭐⭐       | ⭐⭐⭐⭐⭐     |
| RenderTexture → xuất ảnh  | ✅ Native    | ✅ Phức tạp   | ⚠️ Hạn chế   | ✅ Canvas API  |
| Digital Twin / Simulation | ⭐⭐⭐⭐⭐   | ⭐⭐⭐⭐      | ⭐⭐         | ⭐⭐⭐         |
| Cộng đồng và thư viện     | ⭐⭐⭐⭐⭐   | ⭐⭐⭐⭐      | ⭐⭐⭐       | ⭐⭐⭐⭐       |
| Hỗ trợ đa nền tảng        | 25+ nền tảng | PC/Console    | 10+ nền tảng | Chỉ Web        |

**Các lý do kỹ thuật lựa chọn Unity:**

1. **Hệ sinh thái Digital Twin phong phú**: Unity là lựa chọn hàng đầu trong ngành cho simulation và Digital Twin — cung cấp rendering, physics, và networking trong một nền tảng duy nhất. Unreal Engine có chất lượng đồ họa vượt trội nhưng tích hợp HTTP/WebSocket phức tạp hơn đáng kể; Godot 4 dễ học nhưng hệ sinh thái simulation còn non trẻ; Three.js mạnh về tích hợp web nhưng thiếu hệ thống physics và scene management chuyên dụng.
2. **Tích hợp HTTP và WebSocket tốt**: UnityWebRequest (HTTP client tích hợp sẵn) kết hợp NativeWebSocket (package WebSocket cho Unity) cho phép ứng dụng Unity giao tiếp trực tiếp với các microservices backend — thiết yếu cho Digital Twin real-time, nơi trạng thái bãi xe phải đồng bộ liên tục giữa mô phỏng và hệ thống thực.
3. **Pipeline RenderTexture native**: Unity hỗ trợ sẵn việc render output của camera vào texture (RenderTexture), sau đó đọc pixel ngược lại (ReadPixels), encode thành ảnh JPEG hoặc PNG, và gửi qua HTTP. Đây chính xác là workflow cần thiết để streaming frame từ camera ảo đến AI Service — mô phỏng hoàn toàn hành vi của camera RTSP thực tế.
4. **C# type-safe kết hợp Newtonsoft.Json**: So với Blueprint (Unreal) hay GDScript (Godot), C# cho phép định nghĩa API contracts chặt chẽ với annotation `[JsonProperty]`, đảm bảo tương thích kiểu dữ liệu khi giao tiếp với backend Python (FastAPI/Django) và Go (Gin) — giảm thiểu lỗi serialization/deserialization trong quá trình trao đổi dữ liệu giữa Unity và microservices.
5. **Phiên bản LTS đảm bảo ổn định**: Unity 2022.3 LTS (hỗ trợ từ 2022 đến 2025) được chọn vì đảm bảo stability trong suốt chu kỳ phát triển dự án — không có breaking changes. Mặc dù vòng đời LTS đã kết thúc, phiên bản vẫn ổn định và phù hợp cho mục đích phát triển ParkSmart. Đây là yếu tố quan trọng khi dự án phụ thuộc vào nhiều Unity packages (NativeWebSocket, Newtonsoft.Json, URP) cần tương thích ổn định.

### 2.9.3. Universal Render Pipeline (URP)

ParkSmart sử dụng **Universal Render Pipeline (URP) phiên bản 14.0.12** — pipeline rendering tối ưu cho hiệu năng, thay thế Built-in Render Pipeline truyền thống của Unity. URP là một trong ba Scriptable Render Pipelines (SRP) mà Unity cung cấp: Built-in (legacy, không tùy biến), URP (cân bằng hiệu năng và chất lượng), và HDRP — High Definition Render Pipeline (đồ họa photorealistic, yêu cầu phần cứng cao).

URP được lựa chọn cho ParkSmart vì ba lý do: (1) **lightweight hơn HDRP** — phù hợp cho ứng dụng simulation không yêu cầu đồ họa photorealistic, giảm yêu cầu phần cứng cho máy phát triển; (2) **SRP Batcher** — kỹ thuật tối ưu giảm draw calls (lệnh vẽ gửi đến GPU) bằng cách gộp (batch) các materials sử dụng cùng shader variant, tăng hiệu năng rendering đáng kể khi scene có nhiều đối tượng cùng loại (ô đỗ xe, cột trụ, xe cộ); (3) **shader properties có thể điều khiển bằng script** — các thuộc tính material như `_BaseColor` (màu sắc), `_Surface` (Opaque hoặc Transparent), `_Smoothness` (độ bóng) có thể thay đổi runtime từ C# code, cho phép hiệu ứng chuyển màu ô đỗ xe mượt mà (xanh → vàng → đỏ) phản ánh trạng thái real-time.

ParkSmart cấu hình ba quality profiles cho URP: **Balanced** (sử dụng trong quá trình phát triển — cân bằng chất lượng và hiệu năng), **HighFidelity** (sử dụng khi demo — bật đầy đủ hiệu ứng ánh sáng và shadow), và **Performant** (sử dụng khi chạy test tải nặng — giảm tối đa hiệu ứng đồ họa để tối ưu FPS).

### 2.9.4. Kỹ thuật chủ yếu sử dụng trong ParkSmart

**Procedural Generation — Tạo bãi xe tại runtime:**

Thay vì bố trí từng ô đỗ, cột trụ, và làn đường thủ công trong Unity Editor, ParkSmart áp dụng kỹ thuật **Procedural Generation** — cho phép toàn bộ cấu trúc bãi xe được dựng lên tự động khi chương trình khởi động, dựa trên bộ tham số cấu hình như số hàng, số cột, khoảng cách giữa các ô, và số tầng. Module sinh bãi xe (ParkingLotGenerator) chịu trách nhiệm tạo ra các thành phần hạ tầng (sàn, cột trụ, làn đường, điểm dẫn đường) và gán mã định danh cho từng ô đỗ theo quy ước nhất quán, phân biệt theo loại phương tiện và khu vực. Ưu điểm cốt lõi của cách tiếp cận này là tính linh hoạt: khi cần thử nghiệm một cấu hình bãi xe khác, người phát triển chỉ cần điều chỉnh tham số đầu vào mà không phải thiết kế lại scene thủ công — rút ngắn đáng kể vòng lặp thử nghiệm.

**Virtual Camera Pipeline — Camera ảo streaming đến AI Service:**

ParkSmart bố trí nhiều camera ảo trong môi trường 3D, mỗi camera phụ trách một góc quan sát khác nhau: camera tổng quan khu bãi, camera tại cổng ra/vào, và camera theo dõi từng khu vực. Mỗi camera được cấu hình để render hình ảnh vào một RenderTexture, sau đó hệ thống đọc dữ liệu pixel, mã hóa thành định dạng ảnh JPEG, và gửi đến AI Service qua HTTP POST. Quá trình này được lặp đi lặp lại theo chu kỳ với cơ chế kiểm soát lỗi (backoff logic) — khi AI Service không phản hồi liên tục, hệ thống tự tạm dừng và thử lại sau một khoảng thời gian, tránh gây quá tải không cần thiết. Một kỹ thuật đáng chú ý là **layer exclusion**: vỏ bọc vật lý của camera được gán vào một lớp (layer) riêng, bị loại khỏi trường nhìn của chính camera đó — đảm bảo camera không "nhìn thấy" bản thân mình trong khung hình. Đối với camera tại cổng, hệ thống sử dụng Physics.OverlapSphere để phát hiện xe tiếp cận và tự động kích hoạt luồng capture → nhận diện biển số → xác minh booking → mở barrier, mô phỏng hoàn chỉnh quy trình check-in tự động.

**Vehicle State Machine — Máy trạng thái phương tiện:**

Mỗi phương tiện trong mô phỏng được điều khiển bởi một **máy trạng thái hữu hạn (Finite State Machine — FSM)**, đi qua một chuỗi trạng thái nghiệp vụ tuần tự: từ chờ khởi động, tiếp cận cổng, chờ tại cổng, di chuyển vào bãi, tìm đường đến ô đỗ, thực hiện thao tác đỗ, chờ rời đi, rồi thoát ra khỏi bãi. Chuyển động của phương tiện được nội suy mượt mà theo từng điểm dẫn đường (waypoint), sử dụng các phép tính toán vector và xoay chiều chuẩn của Unity. Để xác định đường đi từ cổng đến ô đỗ, hệ thống dùng thuật toán **BFS (Breadth-First Search)** chạy trên đồ thị waypoint — đảm bảo tìm ra con đường ngắn nhất. Hoạt cảnh lùi xe vào ô được thực hiện qua Coroutine, cho phép căn chỉnh vị trí và hướng xe một cách uyển chuyển mà không làm gián đoạn luồng thực thi chính.

**NativeWebSocket — Kết nối real-time:**

Bộ mô phỏng Unity duy trì kết nối WebSocket liên tục đến Realtime Service của hệ thống backend, lắng nghe các sự kiện phát sinh trong thực tế như cập nhật trạng thái ô đỗ, xác nhận check-in thành công, hoặc thông báo lỗi. Khi nhận được sự kiện thay đổi trạng thái ô đỗ, màu sắc của ô trong mô hình 3D được chuyển đổi mượt mà thông qua phép nội suy Lerp — phản ánh trực quan bốn trạng thái: trống (xanh lá), đã đặt trước (vàng), đang có xe (đỏ), và bảo trì (xám). Trong trường hợp mất kết nối WebSocket, hệ thống tự động chuyển sang chế độ polling định kỳ — gọi API để lấy trạng thái mới nhất — đảm bảo bản đồ bãi xe luôn được đồng bộ ngay cả khi mạng không ổn định.

**ESP32 Simulator — Mô phỏng thiết bị IoT:**

Để kiểm thử toàn bộ luồng IoT mà không cần phần cứng thực tế, ParkSmart tích hợp một bảng điều khiển mô phỏng thiết bị ESP32 ngay trong môi trường Unity, xây dựng bằng hệ thống IMGUI (Immediate Mode GUI). Bảng điều khiển này cho phép người phát triển thao tác trực tiếp các hành động check-in, check-out, và thanh toán tiền mặt — mỗi hành động gọi đúng các API endpoint của AI Service kèm header xác thực, giống hệt cách thiết bị IoT thực tế vận hành. Nhờ đó, toàn bộ luồng từ xe vào cổng đến nhận diện biển số, tính phí, thanh toán, và xe ra có thể được kiểm thử và debug ngay trong quá trình phát triển.

**Assembly-based Architecture — Kiến trúc phân tách module:**

Mã nguồn Unity của ParkSmart được tổ chức theo mô hình phân tầng với nhiều assembly riêng biệt, mỗi assembly đảm nhận một nhóm trách nhiệm rõ ràng: tầng networking (HTTP client, WebSocket client, định nghĩa API contract), tầng logic nghiệp vụ (máy trạng thái phương tiện, sinh bãi xe, tìm đường, quản lý ô đỗ), tầng giao diện (IMGUI panels, overlay camera, hiển thị trạng thái), công cụ dành riêng cho môi trường phát triển (chỉ tồn tại trong Unity Editor, không được đóng gói vào sản phẩm cuối), và bộ kiểm thử tự động. Đồ thị phụ thuộc giữa các assembly tuân thủ nguyên tắc một chiều — tầng trên phụ thuộc vào tầng dưới nhưng không ngược lại, loại bỏ hoàn toàn phụ thuộc vòng (circular dependency). Điều này đảm bảo thay đổi ở tầng giao diện không làm ảnh hưởng đến logic nghiệp vụ, và bộ kiểm thử có thể chạy độc lập để xác minh các hành vi cốt lõi như tìm đường, chuyển trạng thái ô đỗ, và tính đúng đắn của dữ liệu trao đổi với backend.

### 2.9.5. Ưu và nhược điểm của Unity trong ParkSmart

**Ưu điểm:**

| STT | Ưu điểm                         | Giải thích                                                                                                                                                               |
| --- | ------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | Digital Twin toàn diện          | Mô phỏng đầy đủ bãi xe, phương tiện, camera, cổng barrier, và thiết bị IoT — cho phép kiểm thử end-to-end toàn bộ pipeline mà không cần phần cứng thực tế                |
| 2   | Virtual camera pipeline độc đáo | 6 camera ảo streaming ảnh JPEG đến AI Service để nhận diện biển số và phát hiện trạng thái ô đỗ — API endpoint giống hệt camera RTSP thật, backend không phân biệt nguồn |
| 3   | Tạo mẫu thử nhanh             | Procedural generation cho phép thay đổi layout bãi xe (số ô, số tầng, khoảng cách) trong vài giây thay vì hàng giờ thiết kế thủ công                                     |
| 4   | API-first design                | Sử dụng cùng API endpoints như ứng dụng thật — phát hiện bug backend sớm trong quá trình phát triển, trước khi tích hợp với phần cứng và ứng dụng mobile                 |

**Nhược điểm và cách khắc phục:**

| STT | Nhược điểm                                                      | Cách khắc phục                                                                                                                                                           |
| --- | --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | Physics không 100% chính xác so với thực tế                     | Chấp nhận giới hạn — mục đích chính là testing pipeline AI và WebSocket, không phải mô phỏng vật lý chính xác; kết quả kiểm thử luồng dữ liệu vẫn hoàn toàn đáng tin cậy |
| 2   | Chất lượng ảnh JPEG từ RenderTexture thấp hơn camera thật       | Sử dụng chất lượng encode 75% và huấn luyện mô hình AI với cả ảnh từ Unity lẫn ảnh camera thật — mô hình trở nên robust hơn, hoạt động tốt trong cả hai môi trường       |
| 3   | Unity Editor yêu cầu cấu hình phần cứng cao (tối thiểu 8GB RAM) | Hỗ trợ headless mode cho CI/CD testing (chạy test không cần giao diện đồ họa); Unity Editor chỉ cần thiết cho quá trình phát triển, không phải vận hành production       |
| 4   | IMGUI là hệ thống giao diện cũ, không phù hợp production UI     | Chấp nhận — bộ mô phỏng là công cụ nội bộ phục vụ phát triển và kiểm thử, không phải sản phẩm cuối dành cho người dùng; IMGUI đủ chức năng cho mục đích này              |

---

# Chương 3. HỆ THỐNG PHÁT TRIỂN BÃI GIỮ XE THÔNG MINH ỨNG DỤNG IOT VÀ NHẬN DIỆN BIỂN SỐ TỰ ĐỘNG

---

## 3.1. Giới thiệu hệ thống

Hệ thống bãi giữ xe thông minh ParkSmart được xây dựng trên nền tảng kiến trúc **Microservices** gồm 10 dịch vụ backend độc lập, giao tiếp thông qua một API Gateway duy nhất, kết hợp giao diện người dùng Single Page Application (SPA) và hệ thống phần cứng IoT tại cổng ra/vào. Hệ thống được thiết kế hướng đến tính mở rộng (scalability), khả năng chịu lỗi (fault tolerance), và tính linh hoạt trong lựa chọn công nghệ (technology diversity) cho từng thành phần.

### 3.1.1. Sơ đồ kiến trúc tổng quan

_Hình 3.1: Sơ đồ kiến trúc tổng quan hệ thống ParkSmart_

```

┌──────────────────────────────────────────────────────────────────────┐

│                     FRONTEND (React 18.3.1 + Vite 5.4.19)           │

│   spotlove-ai/ (frontend SPA) — 28 trang (19 root + 9 admin)        │

│   TypeScript 5.8.3 │ Redux Toolkit 2.11.2 │ React Query 5.83.0      │

│   shadcn/ui 51 components (73 tổng) │ TailwindCSS 3.4.17 │ Dark/Light│

└───────────────────────────────┬──────────────────────────────────────┘

                                │ HTTP/REST + WebSocket

┌───────────────────────────────▼──────────────────────────────────────┐

│              API GATEWAY (Go 1.22 + Gin 1.10.0) — Port 8000         │

│   Session-based Auth │ Reverse Proxy │ Rate Limiting │ CORS          │

│   X-User-ID + X-Gateway-Secret injection                             │

└──┬────┬────┬────┬────┬────┬────┬────┬────────────────────────────────┘

   │    │    │    │    │    │    │    │

   ▼    ▼    ▼    ▼    ▼    ▼    ▼    ▼

┌──────────────────── BACKEND SERVICES ────────────────────────────────┐

│                                                                       │

│  ╔═══════════════════ Django 5.2.12 + DRF 3.15.2 ════════════════╗   │

│  ║ Auth      Booking        Parking       Vehicle                 ║   │

│  ║ :8001     :8002          :8003         (internal)              ║   │

│  ║           + Celery 5.4.0                                       ║   │

│  ║           (3 containers)                                       ║   │

│  ╚════════════════════════════════════════════════════════════════╝   │

│                                                                       │

│  ╔═══════════════════ FastAPI 0.134.0 ═══════════════════════════╗   │

│  ║ AI         Chatbot        Payment       Notification          ║   │

│  ║ :8009      :8008          :8007         :8005                  ║   │

│  ╚════════════════════════════════════════════════════════════════╝   │

│                                                                       │

│  ╔═══════════════════ Go 1.22 ═══════════════════════════════════╗   │

│  ║ Realtime (Gorilla WebSocket 1.5.3) — :8006                    ║   │

│  ╚════════════════════════════════════════════════════════════════╝   │

└──────────────────────────────────────────────────────────────────────┘

┌───────────────────── INFRASTRUCTURE ─────────────────────────────────┐

│  MySQL 8.0 (:3307)    │  Redis 7 (7 DBs, :6379)  │  RabbitMQ 3 (:5672) │

└──────────────────────────────────────────────────────────────────────┘

┌───────────────────── HARDWARE / IoT ─────────────────────────────────┐

│  ESP32 (WiFi, GPIO4/5 Buttons, GPIO21/22 I2C OLED SSD1306 128×64)   │

│       ↕ UART 9600bps (GPIO16 TX / GPIO17 RX)                        │

│  Arduino (Pin10 Servo Entry, Pin9 Servo Exit, PWM 1500μs→3000μs)    │

│  Camera DroidCam (QR) │ Camera RTSP EZVIZ (Biển số)                 │

└──────────────────────────────────────────────────────────────────────┘

┌───────────────────── SIMULATION / DIGITAL TWIN ──────────────────────┐

│  Unity 2022.3 LTS (C#, URP 14.0.12) — Parking Simulator 3D          │

│  6 Virtual Cameras (JPEG → AI :8009) │ NativeWebSocket (→ :8006)     │

│  158 slots procedural │ Vehicle 11-state FSM │ ESP32 Simulator       │

│  API: Gateway :8000 + AI :8009 direct │ WS: Realtime :8006           │

└──────────────────────────────────────────────────────────────────────┘

```

Sơ đồ trên minh họa luồng dữ liệu chính của hệ thống: (1) Người dùng tương tác qua giao diện React SPA, mọi request đều đi qua API Gateway; (2) Gateway xác thực session-based cookie, inject header `X-User-ID` và `X-Gateway-Secret` rồi proxy đến dịch vụ đích; (3) Các dịch vụ backend xử lý nghiệp vụ và trả kết quả; (4) Realtime Service broadcast cập nhật qua WebSocket; (5) Thiết bị IoT ESP32 giao tiếp trực tiếp với AI Service qua HTTP REST.

### 3.1.2. Danh sách 10 Microservices

_Bảng 3.2: Danh sách 10 microservices của hệ thống ParkSmart_

| #   | Service                      | Framework                                 | Port     | Ngôn ngữ | Containers | Chức năng chính                                                                                   |
| --- | ---------------------------- | ----------------------------------------- | -------- | -------- | ---------- | ------------------------------------------------------------------------------------------------- |
| 1   | auth-service                 | Django 5.2.12 + DRF 3.15.2                | 8001     | Python   | 1          | Đăng ký, đăng nhập session-based, OAuth Google/Facebook, quản lý user, admin dashboard stats      |
| 2   | booking-service              | Django 5.2.12 + DRF 3.15.2 + Celery 5.4.0 | 8002     | Python   | 3          | CRUD booking, check-in/out, QR code generation, package pricing, incidents, auto-expire bookings  |
| 3   | parking-service              | Django 5.2.12 + DRF 3.15.2                | 8003     | Python   | 1          | Quản lý ParkingLot, Floor, Zone, CarSlot (với bbox AI), Camera                                    |
| 4   | vehicle-service              | Django 5.2.12 + DRF 3.15.2                | internal | Python   | 1          | CRUD vehicle per user (biển số, loại, màu, mặc định)                                              |
| 5   | ai-service-fastapi           | FastAPI 0.134.0                           | 8009     | Python   | 1          | Plate OCR (YOLO+TrOCR), slot detection (YOLO11n), QR reader, banknote/cash recognition, ESP32 API |
| 6   | chatbot-service-fastapi      | FastAPI 0.134.0                           | 8008     | Python   | 1          | NLU pipeline v3.0, booking wizard, Gemini LLM, proactive notifications                            |
| 7   | payment-service-fastapi      | FastAPI 0.134.0                           | 8007     | Python   | 1          | Xử lý thanh toán, cash detection session                                                          |
| 8   | notification-service-fastapi | FastAPI 0.134.0                           | 8005     | Python   | 1          | Push notifications, email alerts qua RabbitMQ consumer                                            |
| 9   | gateway-service-go           | Go 1.22 + Gin 1.10.0                      | 8000     | Go       | 1          | API Gateway, session auth, reverse proxy, rate limiting, CORS                                     |
| 10  | realtime-service-go          | Go 1.22 + Gorilla WebSocket 1.5.3         | 8006     | Go       | 1          | WebSocket hub, real-time broadcasts slot updates, pub/sub Redis                                   |

**Tổng cộng: 15 Docker containers** (10 services + booking-celery-worker + booking-celery-beat + MySQL + Redis + RabbitMQ).

### 3.1.3. Bảng công nghệ theo layer

_Bảng 3.3: Tổng hợp công nghệ theo layer_

| Layer              | Công nghệ              | Phiên bản                    | Vai trò                                       |
| ------------------ | ---------------------- | ---------------------------- | --------------------------------------------- |
| **Frontend**       | React                  | 18.3.1                       | Thư viện UI, component-based SPA              |
|                    | TypeScript             | 5.8.3                        | Kiểm tra kiểu dữ liệu cho JavaScript          |
|                    | Vite                   | 5.4.19                       | Build tool, dev server HMR                    |
|                    | TailwindCSS            | 3.4.17                       | Utility-first CSS framework                   |
|                    | shadcn/ui + Radix UI   | 51 components (73 tổng)      | Component library accessible                  |
|                    | Redux Toolkit          | 2.11.2                       | Global state management                       |
|                    | React Query (TanStack) | 5.83.0                       | Server state caching, refetch                 |
|                    | Axios                  | —                            | HTTP client, cookie-based auth                |
| **Backend Python** | Django                 | 5.2.12                       | Web framework (4 services)                    |
|                    | Django REST Framework  | 3.15.2                       | RESTful API toolkit                           |
|                    | FastAPI                | 0.134.0                      | Async web framework (4 services)              |
|                    | Celery                 | 5.4.0                        | Distributed task queue                        |
|                    | SQLAlchemy             | —                            | ORM cho FastAPI services                      |
|                    | Pydantic               | v2                           | Data validation                               |
| **Backend Go**     | Go                     | 1.22                         | Compiled language, high concurrency           |
|                    | Gin                    | 1.10.0                       | HTTP web framework                            |
|                    | Gorilla WebSocket      | 1.5.3                        | WebSocket library                             |
| **Database**       | MySQL                  | 8.0                          | RDBMS chính, UUID CHAR(36) PKs                |
| **Cache / Queue**  | Redis                  | 7                            | Cache (7 DBs), session store, pub/sub         |
|                    | RabbitMQ               | 3                            | Message broker (AMQP), event-driven messaging |
| **AI / ML**        | YOLOv8 (fine-tuned)    | ultralytics                  | Phát hiện biển số xe                          |
|                    | YOLO11n                | ultralytics                  | Phát hiện xe trong ô đỗ (nano)                |
|                    | TrOCR                  | microsoft/trocr-base-printed | OCR chính cho biển số                         |
|                    | EasyOCR                | 1.7.2                        | OCR fallback                                  |
|                    | Tesseract              | —                            | OCR fallback cuối cùng                        |
|                    | MobileNetV3-Large      | custom multi-branch          | Nhận dạng tiền giấy (4 branches, 1088-dim)    |
|                    | ResNet50               | custom                       | Nhận dạng mệnh giá tiền mặt                   |
|                    | OpenCV                 | —                            | QR decode, image processing                   |
| **LLM**            | Google Gemini          | gemini-3-flash-preview       | Chatbot NLU, response generation              |
| **IoT**            | ESP32                  | —                            | WiFi gateway, I2C OLED, GPIO buttons          |
|                    | Arduino                | —                            | Servo barrier control, UART slave             |
|                    | OLED SSD1306           | 128×64                       | Hiển thị biển số, trạng thái                  |
|                    | Servo Motor            | SG90                         | Barrier cổng vào/ra                           |
| **Deploy**         | Docker                 | —                            | Containerization                              |
|                    | Docker Compose         | —                            | Multi-container orchestration                 |
|                    | Nginx                  | —                            | Reverse proxy cho production                  |
|                    | Cloudflare Tunnel      | —                            | Expose local to internet                      |
| **Testing**        | Playwright             | —                            | E2E browser testing                           |
|                    | Vitest                 | —                            | Unit test React/TypeScript                    |
|                    | pytest                 | —                            | Unit/integration test Python                  |
| **Simulator**      | Unity                  | 2022.3.62f3 LTS              | 3D parking simulation, Digital Twin           |
|                    | C# (.NET Standard 2.1) | —                            | Unity scripting language                      |
|                    | URP                    | 14.0.12                      | Universal Render Pipeline                     |
|                    | NativeWebSocket        | git#upm                      | WebSocket client (real-time slot updates)     |
|                    | Newtonsoft.Json        | 3.2.1                        | JSON serialization (API communication)        |
|                    | NUnit                  | via Test Framework 1.1.33    | Unit/PlayMode testing                         |

---

## 3.2. Phân tích hệ thống

### 3.2.1. Sơ đồ Use Case

Hệ thống ParkSmart được phân tích với **5 tác nhân (Actors)** và **16 ca sử dụng (Use Cases)** chính.

**Bảng Actors:**

| Actor                     | Loại            | Mô tả                                                                                                                                      |
| ------------------------- | --------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| **User** (Người dùng)     | Primary         | Người sử dụng bãi xe: đăng ký tài khoản, đăng ký phương tiện, đặt chỗ trực tuyến, check-in/check-out tại cổng, thanh toán, sử dụng chatbot |
| **Admin** (Quản trị viên) | Primary         | Người quản lý bãi xe: quản lý users, bãi xe, zones, slots, cameras, ESP32 devices, xem báo cáo doanh thu, xử lý sự cố                      |
| **ESP32 Device**          | External System | Vi điều khiển IoT tại cổng ra/vào, trigger check-in/check-out, giao tiếp HTTP với AI server, điều khiển barrier qua UART                   |
| **AI System**             | External System | Hệ thống trí tuệ nhân tạo: nhận dạng biển số (LPR), phát hiện trạng thái ô đỗ, đọc QR code, nhận dạng tiền giấy                            |
| **Chatbot**               | External System | Trợ lý ảo AI tích hợp Gemini LLM: xử lý hội thoại tiếng Việt, đặt chỗ qua hội thoại, tra cứu thông tin                                     |

**Sơ đồ Use Case (text representation):**

_Hình 3.2: Sơ đồ Use Case hệ thống ParkSmart_

```

                              ┌─────────────────────────────────────┐

                              │          HỆ THỐNG PARKSMART         │

    ┌──────┐                  │                                     │

    │ User │──────────────────┤  UC01: Đăng ký tài khoản            │

    │      │──────────────────┤  UC02: Đăng nhập                    │

    │      │──────────────────┤  UC03: Quản lý xe                   │

    │      │──────────────────┤  UC04: Đặt chỗ online               │

    │      │──────────────────┤  UC05: Xem bản đồ bãi xe            │

    │      │──────────────────┤  UC08: Thanh toán online             │

    │      │──────────────────┤  UC09: Thanh toán tiền mặt          │

    │      │──────────────────┤  UC10: Chatbot hỗ trợ               │

    │      │──────────────────┤  UC11: Báo sự cố (Panic)            │

    └──────┘                  │                                     │

                              │                                     │

    ┌──────┐                  │                                     │

    │Admin │──────────────────┤  UC12: Quản lý bãi xe               │

    │      │──────────────────┤  UC13: Quản lý ESP32                │

    │      │──────────────────┤  UC14: Xem camera                   │

    │      │──────────────────┤  UC15: Báo cáo doanh thu            │

    └──────┘                  │                                     │

                              │                                     │

    ┌──────┐                  │                                     │

    │ESP32 │──────────────────┤  UC06: Check-in tại cổng            │

    │Device│──────────────────┤  UC07: Check-out tại cổng           │

    └──────┘                  │                                     │

                              │                                     │

    ┌──────┐                  │                                     │

    │  AI  │··················┤  «include» UC06, UC07, UC09          │

    │System│                  │                                     │

    └──────┘                  │                                     │

                              │                                     │

    ┌───────┐                 │                                     │

    │Chatbot│·················┤  «include» UC10                     │

    └───────┘                 │                                     │

                              │                                     │

    ┌──────┐                  │                                     │

    │Public│──────────────────┤  UC16: Xem kiosk (không cần auth)   │

    └──────┘                  │                                     │

                              └─────────────────────────────────────┘

```

**Danh sách 16 Use Cases:**

| Mã   | Use Case            | Actor chính | Actor phụ | Mô tả chức năng                                                               |
| ---- | ------------------- | ----------- | --------- | ----------------------------------------------------------------------------- |
| UC01 | Đăng ký tài khoản   | User        | —         | Đăng ký bằng email/password hoặc OAuth Google/Facebook                        |
| UC02 | Đăng nhập           | User        | —         | Xác thực session-based (cookie), quản lý session                              |
| UC03 | Quản lý xe          | User        | —         | Thêm/sửa/xóa phương tiện (biển số, loại xe, màu sắc), đặt xe mặc định         |
| UC04 | Đặt chỗ online      | User        | —         | Đặt chỗ multi-step: lot → floor → zone → slot → vehicle → package → payment   |
| UC05 | Xem bản đồ bãi xe   | User        | Realtime  | Xem trạng thái ô đỗ real-time (xanh/đỏ/vàng), filter theo tầng/zone           |
| UC06 | Check-in tại cổng   | ESP32       | AI System | Nhấn nút → QR scan → plate OCR → validate booking → mở barrier                |
| UC07 | Check-out tại cổng  | ESP32       | AI System | Nhấn nút → QR scan → verify payment → plate OCR → mở barrier                  |
| UC08 | Thanh toán online   | User        | —         | Thanh toán booking trước khi check-out                                        |
| UC09 | Thanh toán tiền mặt | User        | AI System | Đưa tiền trước camera → AI detect mệnh giá → tích lũy đến đủ                  |
| UC10 | Chatbot hỗ trợ      | User        | Chatbot   | Hỏi đáp tiếng Việt, đặt chỗ qua hội thoại (wizard), kiểm tra booking          |
| UC11 | Báo sự cố (Panic)   | User        | —         | Báo khẩn cấp: emergency, theft, vehicle_damage, accident, suspicious_activity |
| UC12 | Quản lý bãi xe      | Admin       | —         | CRUD parking lots, floors, zones, slots (với bbox AI coordinates)             |
| UC13 | Quản lý ESP32       | Admin       | —         | Monitor thiết bị IoT: trạng thái online/offline, logs, heartbeat              |
| UC14 | Xem camera          | Admin       | AI System | Live camera feeds, xem kết quả AI detection trực tiếp                         |
| UC15 | Báo cáo doanh thu   | Admin       | —         | Revenue analytics: theo ngày/tuần/tháng, biểu đồ Recharts                     |
| UC16 | Xem kiosk           | Public      | —         | Thông tin bãi xe công khai (số chỗ trống, giá), không cần đăng nhập           |

### 3.2.2. Đặc tả Use Case chi tiết

#### UC04 — Đặt chỗ online (Online Booking)

| Mục                | Nội dung                                                                                                                                      |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------- |
| **Mã Use Case**    | UC04                                                                                                                                          |
| **Tên**            | Đặt chỗ online                                                                                                                                |
| **Actor chính**    | User (Người dùng)                                                                                                                             |
| **Tiền điều kiện** | (1) User đã đăng nhập thành công; (2) User đã đăng ký ít nhất 1 phương tiện (vehicle) với biển số hợp lệ                                      |
| **Hậu điều kiện**  | Booking được tạo (status = `not_checked_in`), slot status chuyển sang `reserved`, mã QR được sinh tự động, realtime broadcast cập nhật bản đồ |

**Luồng chính (Main Flow):**

| Bước | Actor                                  | Hệ thống                                                                                      |
| ---- | -------------------------------------- | --------------------------------------------------------------------------------------------- |
| 1    | User truy cập trang Booking (/booking) | Hiển thị giao diện đặt chỗ multi-step                                                         |
| 2    | User chọn bãi xe                       | Frontend gọi `GET /parking/lots/` → hiển thị danh sách bãi xe với thông tin chỗ trống         |
| 3    | User chọn tầng                         | Frontend gọi `GET /parking/floors/?lot_id={id}` → hiển thị danh sách tầng                     |
| 4    | User chọn zone                         | Frontend gọi `GET /parking/zones/?floor_id={id}` → hiển thị zones với số chỗ trống            |
| 5    | User chọn ô đỗ trống (màu xanh)        | Frontend hiển thị slot grid, WebSocket cập nhật realtime                                      |
| 6    | User chọn xe từ danh sách              | Frontend gọi `GET /vehicles/` → hiển thị xe đã đăng ký                                        |
| 7    | User chọn gói thời gian                | Hiển thị 4 gói: hourly, daily, weekly, monthly với giá tương ứng                              |
| 8    | User chọn phương thức thanh toán       | online (trả trước) hoặc on_exit (trả khi ra)                                                  |
| 9    | User nhấn "Xác nhận đặt chỗ"           | Frontend gọi `POST /bookings/` với toàn bộ thông tin                                          |
| 10   | —                                      | Gateway xác thực session → inject X-User-ID → proxy đến booking-service                       |
| 11   | —                                      | Booking-service validate: slot còn trống? vehicle thuộc user? package_pricing tồn tại?        |
| 12   | —                                      | Booking-service gọi parking-service `PATCH /slots/{id}/` → cập nhật status = reserved         |
| 13   | —                                      | Booking-service lưu bản ghi booking (denormalized: copy user_email, vehicle_plate, slot_code) |
| 14   | —                                      | Tự động sinh QR code chứa booking_id (UUID)                                                   |
| 15   | —                                      | Gọi notification-service gửi thông báo qua RabbitMQ                                           |
| 16   | —                                      | Broadcast WebSocket event cập nhật slot status trên bản đồ                                    |
| 17   | User nhận QR code                      | Hiển thị QR code trên giao diện, sẵn sàng cho check-in                                        |

**Luồng ngoại lệ (Exception Flow):**

| Mã  | Điều kiện                                          | Xử lý                                                                             |
| --- | -------------------------------------------------- | --------------------------------------------------------------------------------- |
| E1  | Slot đã bị user khác đặt (race condition)          | Trả lỗi 409 Conflict, frontend thông báo "Ô đỗ đã được đặt, vui lòng chọn ô khác" |
| E2  | Vehicle không thuộc user                           | Trả lỗi 403 Forbidden                                                             |
| E3  | Package pricing không tồn tại                      | Trả lỗi 400 Validation Error                                                      |
| E4  | User bị force_online_payment (do no-show trước đó) | Bắt buộc thanh toán online, không cho chọn on_exit                                |
| E5  | Kết nối mạng bị gián đoạn                          | Frontend hiển thị retry, dữ liệu form không bị mất                                |

---

#### UC06 — Check-in tại cổng (IoT Check-in)

| Mục                | Nội dung                                                                                                                                                                          |
| ------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Mã Use Case**    | UC06                                                                                                                                                                              |
| **Tên**            | Check-in tại cổng                                                                                                                                                                 |
| **Actor chính**    | ESP32 Device                                                                                                                                                                      |
| **Actor phụ**      | AI System, User (tương tác vật lý)                                                                                                                                                |
| **Tiền điều kiện** | (1) User có booking hợp lệ (status = `not_checked_in`); (2) Thời gian hiện tại nằm trong time window ±15 phút so với start_time; (3) ESP32 đã đăng ký và online (heartbeat < 30s) |
| **Hậu điều kiện**  | Booking status = `checked_in`, slot status = `occupied`, barrier tự động mở rồi đóng sau 5s, thông tin biển số hiển thị trên OLED                                                 |

**Luồng chính (Main Flow):**

| Bước | Actor                                     | Hệ thống                                                                                      |
| ---- | ----------------------------------------- | --------------------------------------------------------------------------------------------- |
| 1    | User nhấn nút Check-in trên ESP32 (GPIO4) | ESP32 debounce 300ms, bắt đầu check-in flow                                                   |
| 2    | —                                         | ESP32 gửi `POST /ai/esp32/check-in/` (kèm X-Device-Token + X-Gateway-Secret)                  |
| 3    | —                                         | AI Service mở camera QR (DroidCam), bắt đầu scan loop (timeout 30 giây)                       |
| 4    | User đưa QR code trước camera             | Camera capture frame → OpenCV QRCodeDetector decode                                           |
| 5    | —                                         | Giải mã QR → lấy booking_id (UUID)                                                            |
| 6    | —                                         | AI Service gọi `GET /bookings/{booking_id}/` → lấy thông tin booking                          |
| 7    | —                                         | Validate: booking status = not_checked_in? payment hợp lệ? thời gian đúng window?             |
| 8    | —                                         | Mở camera biển số (RTSP EZVIZ), capture frame                                                 |
| 9    | —                                         | **AI Pipeline**: YOLOv8 detect vùng biển số → crop → TrOCR OCR (fallback EasyOCR → Tesseract) |
| 10   | —                                         | Vietnamese plate format validation (regex: `\d{2}[A-Z]-\d{3}\.\d{2}`)                         |
| 11   | —                                         | Fuzzy matching: so sánh OCR result vs booking.vehicle_license_plate (cho phép ≤3 ký tự sai)   |
| 12   | —                                         | Gọi booking-service `POST /bookings/{id}/check-in/` → cập nhật status = checked_in            |
| 13   | —                                         | Gọi parking-service `PATCH /slots/{id}/` → cập nhật status = occupied                         |
| 14   | —                                         | Broadcast WebSocket event → realtime bản đồ cập nhật                                          |
| 15   | —                                         | Trả response JSON: `{barrierAction: "open", plateText: "51A-224.56", gateType: "entry"}`      |
| 16   | —                                         | ESP32 gửi UART `"OPEN_1\n"` → Arduino servo entry (Pin10) từ 1500μs→3000μs                    |
| 17   | —                                         | ESP32 hiển thị biển số trên OLED SSD1306 (128×64)                                             |
| 18   | User lái xe vào bãi                       | —                                                                                             |
| 19   | —                                         | Sau 5 giây: ESP32 gửi UART `"CLOSE_1\n"` → Arduino đóng barrier                               |

**Luồng ngoại lệ (Exception Flow):**

| Mã  | Điều kiện                                    | Xử lý                                                    |
| --- | -------------------------------------------- | -------------------------------------------------------- |
| E1  | QR scan timeout (30s)                        | Trả lỗi, OLED hiển thị "QR Timeout", barrier giữ đóng    |
| E2  | Booking không tồn tại hoặc đã check-in       | Trả lỗi 400, OLED hiển thị "Invalid Booking"             |
| E3  | Biển số OCR không khớp (fuzzy > 3 ký tự sai) | Trả cảnh báo, barrier giữ đóng, log incident             |
| E4  | Camera biển số không khả dụng                | Fallback: chỉ validate QR, skip plate check, log warning |
| E5  | Arduino không ACK lệnh UART                  | ESP32 retry 2 lần, nếu fail → log error, báo admin       |

---

## 3.3. Thiết kế hệ thống

### 3.3.1. Thiết kế sơ đồ tuần tự (Sequence Diagrams)

#### Flow 1: Đặt chỗ Online (Online Booking)

_Hình 3.3: Sơ đồ tuần tự — Quy trình đặt chỗ online_

```

User        React FE       Gateway(:8000)   Parking(:8003)  Booking(:8002)  Vehicle(int)  Notif(:8005)  Realtime(:8006)

 │            │                  │                │               │              │             │              │

 │──truy cập──►│                  │                │               │              │             │              │

 │            │──GET /lots/──────►│──proxy─────────►│               │              │             │              │

 │            │◄──200 lot list───│◄────────────────│               │              │             │              │

 │            │                  │                │               │              │             │              │

 │──chọn slot─►│                  │                │               │              │             │              │

 │            │──GET /slots/?────►│──proxy─────────►│               │              │             │              │

 │            │◄──200 slots──────│◄────────────────│               │              │             │              │

 │            │                  │                │               │              │             │              │

 │──xác nhận──►│                  │                │               │              │             │              │

 │            │──POST /bookings/─►│                │               │              │             │              │

 │            │                  │──auth + inject──►               │              │             │              │

 │            │                  │  X-User-ID      │               │              │             │              │

 │            │                  │──proxy──────────────────────────►│              │             │              │

 │            │                  │                │               │──GET vehicle─►│             │              │

 │            │                  │                │               │◄──vehicle ok──│             │              │

 │            │                  │                │               │──PATCH slot──►│             │              │

 │            │                  │                │◄──reserved────│              │             │              │

 │            │                  │                │               │──generate QR  │             │              │

 │            │                  │                │               │──notify────────────────────►│              │

 │            │                  │                │               │──broadcast───────────────────────────────►│

 │            │◄──201 booking+QR─│◄───────────────────────────────│              │             │              │

 │◄──show QR──│                  │                │               │              │             │              │

```

#### Flow 2: Check-in IoT + AI (Autonomous Gate Control)

_Hình 3.4: Sơ đồ tuần tự — Quy trình check-in tự động_

```

User     ESP32     AI Service(:8009)  QR Camera  Plate Camera  Booking(:8002) Parking(:8003) Realtime(:8006) Arduino

 │        │              │               │            │              │             │              │            │

 │─press──►│              │               │            │              │             │              │            │

 │        │──POST /ci/──►│               │            │              │             │              │            │

 │        │              │──open cam────►│            │              │             │              │            │

 │─show──────────────────────────────────►│            │              │             │              │            │

 │  QR    │              │◄──QR frame────│            │              │             │              │            │

 │        │              │ decode → booking_id        │              │             │              │            │

 │        │              │──GET /bookings/{id}/─────────────────────►│             │              │            │

 │        │              │◄──booking data────────────────────────────│             │              │            │

 │        │              │ validate status + time window ±15min      │             │              │            │

 │        │              │──capture plate────────────►│              │             │              │            │

 │        │              │◄──plate frame──────────────│              │             │              │            │

 │        │              │ YOLO detect → TrOCR → "51A-224.56"       │             │              │            │

 │        │              │ fuzzy match OCR vs booking plate (≤3)     │             │              │            │

 │        │              │──POST /checkin/──────────────────────────►│             │              │            │

 │        │              │──PATCH /slots/{id}/ occupied──────────────────────────►│              │            │

 │        │              │──broadcast slot update──────────────────────────────────────────────►│            │

 │        │◄──{open}─────│               │            │              │             │              │            │

 │        │──UART "OPEN_1"──────────────────────────────────────────────────────────────────────────────────►│

 │        │──I2C OLED────►Display: "51A-224.56"       │              │             │              │            │

 │        │              │               │            │              │             │              │            │

 │        │──5s delay────│               │            │              │             │              │            │

 │        │──UART "CLOSE_1"─────────────────────────────────────────────────────────────────────────────────►│

```

#### Flow 3: Chatbot Booking Wizard (Đặt chỗ qua hội thoại)

_Hình 3.5: Sơ đồ tuần tự — Chatbot Booking Wizard_

```

User       React FE      Gateway(:8000)  Chatbot(:8008)       Parking(:8003)   Booking(:8002)

 │           │                │                │                    │                │

 │─"đặt ô tô"►│                │                │                    │                │

 │           │──POST /chat/──►│──proxy──────────►│                    │                │

 │           │                │                │──Intent Detection    │                │

 │           │                │                │  intent=booking_car  │                │

 │           │                │                │  confidence=0.92     │                │

 │           │                │                │──Wizard: INIT────────│                │

 │           │                │                │──GET /floors/───────►│                │

 │           │                │                │◄──floors list────────│                │

 │           │◄─"Chọn tầng:──│◄────────────────│                    │                │

 │           │  1. Tầng 1     │                │                    │                │

 │           │  2. Tầng 2"    │                │                    │                │

 │           │                │                │                    │                │

 │─"Tầng 1"──►│                │                │                    │                │

 │           │──POST /chat/──►│──proxy──────────►│                    │                │

 │           │                │                │──Wizard: FLOOR_SELECTED                │

 │           │                │                │──GET /zones/?floor=1►│                │

 │           │                │                │◄──zones list─────────│                │

 │           │◄─"Chọn zone:──│◄────────────────│                    │                │

 │           │  A. Zone A     │                │                    │                │

 │           │  B. Zone B"    │                │                    │                │

 │           │                │                │                    │                │

 │─"Zone A"───►│                │                │                    │                │

 │           │──POST /chat/──►│──proxy──────────►│                    │                │

 │           │                │                │──Wizard: ZONE_SELECTED                │

 │           │                │                │──POST /bookings/────────────────────►│

 │           │                │                │◄──booking + QR───────────────────────│

 │           │◄─"✅ Đã đặt────│◄────────────────│                    │                │

 │           │  thành công!   │                │                    │                │

 │           │  Mã QR: ..."   │                │                    │                │

```

### 3.3.2. Thiết kế cơ sở dữ liệu (Database Design)

Hệ thống ParkSmart sử dụng **MySQL 8.0** làm cơ sở dữ liệu chính. Theo pattern **Database-per-Service** trong kiến trúc microservices, mỗi service sở hữu bộ bảng riêng trong cùng một database instance `parksmartdb`. Tất cả primary key sử dụng **UUID CHAR(36)** để đảm bảo tính duy nhất trong hệ thống phân tán.

#### Entity Relationship Diagram (ERD)

_Hình 3.6: Sơ đồ Entity Relationship (ERD) hệ thống ParkSmart_

```

┌─── Auth Service ──────────────────────────────────────────────────────┐

│                                                                        │

│  ┌─────────────────────────────┐     ┌──────────────────────────────┐ │

│  │      users_user             │     │   users_oauth_account        │ │

│  │─────────────────────────────│     │──────────────────────────────│ │

│  │ PK id         UUID CHAR(36)│◄──┐ │ PK id        UUID CHAR(36)  │ │

│  │    email      VARCHAR(255) │    │ │ FK user_id   UUID CHAR(36)  │─┘

│  │    username   VARCHAR(150) │    │ │    provider  VARCHAR(20)    │

│  │    password   VARCHAR(128) │    │ │    provider_uid VARCHAR(255)│

│  │    phone      VARCHAR(20)  │    │ │    access_token  TEXT       │

│  │    address    TEXT         │    │ │    refresh_token TEXT       │

│  │    avatar     VARCHAR(500) │    │ │    token_expires_at DATETIME│

│  │    role       ENUM(user,   │    │ │    created_at   DATETIME   │

│  │               admin)       │    │ └──────────────────────────────┘

│  │    no_show_count INT       │    │

│  │    force_online_payment    │    │ ┌──────────────────────────────┐

│  │               BOOLEAN      │    │ │  users_password_reset        │

│  │    is_active  BOOLEAN      │    │ │──────────────────────────────│

│  │    created_at DATETIME     │    └─│ PK id       UUID CHAR(36)   │

│  │    updated_at DATETIME     │      │ FK user_id  UUID CHAR(36)   │

│  └─────────────────────────────┘      │    token    VARCHAR(255)    │

│                                       │    expires_at DATETIME      │

│                                       │    used      BOOLEAN        │

│                                       └──────────────────────────────┘

└────────────────────────────────────────────────────────────────────────┘

┌─── Parking Service ───────────────────────────────────────────────────┐

│                                                                        │

│  ┌─────────────────────┐  1    N  ┌────────────────────┐              │

│  │    parking_lot       │─────────│      floor          │              │

│  │─────────────────────│          │────────────────────│              │

│  │ PK id    UUID       │          │ PK id    UUID      │              │

│  │    name  VARCHAR    │          │ FK lot_id UUID     │  1    N      │

│  │    address VARCHAR  │          │    level  INT      │──────┐       │

│  │    latitude DECIMAL │          │    name   VARCHAR  │      │       │

│  │    longitude DECIMAL│          └────────────────────┘      │       │

│  │    total_slots INT  │                                      ▼       │

│  │    avail_slots INT  │          ┌────────────────────┐              │

│  │    price_per_hour   │          │      zone           │              │

│  │    is_open BOOLEAN  │          │────────────────────│              │

│  └─────────────────────┘          │ PK id       UUID   │  1    N      │

│                                   │ FK floor_id UUID   │──────┐       │

│  ┌──────────────────────┐         │    name     VARCHAR│      │       │

│  │infrastructure_camera │         │    vehicle_type    │      │       │

│  │──────────────────────│         │    ENUM(Car,Moto)  │      │       │

│  │ PK id     UUID       │         │    capacity  INT   │      ▼       │

│  │    name   VARCHAR    │         │    avail_slots INT │              │

│  │    ip_address VARCHAR│         └────────────────────┘              │

│  │    port   INT        │                                             │

│  │ FK zone_id UUID      │         ┌───────────────────────┐          │

│  │    stream_url VARCHAR│         │      car_slot          │          │

│  │    is_active BOOLEAN │         │───────────────────────│          │

│  └──────────────────────┘         │ PK id      UUID       │          │

│           │                       │ FK zone_id UUID       │          │

│           └───────────────────────│ FK camera_id UUID NULL│          │

│                                   │    code     VARCHAR   │          │

│                                   │    status   ENUM      │          │

│                                   │    (available,reserved│          │

│                                   │     occupied,disabled)│          │

│                                   │    x1,y1,x2,y2 FLOAT │◄─ AI bbox│

│                                   └───────────────────────┘          │

└────────────────────────────────────────────────────────────────────────┘

┌─── Vehicle Service ───────────────────────────────────────────────────┐

│  ┌──────────────────────────────┐                                     │

│  │        vehicle                │                                     │

│  │──────────────────────────────│                                     │

│  │ PK id             UUID       │                                     │

│  │    user_id        UUID (ref) │  ← Tham chiếu user qua X-User-ID   │

│  │    license_plate  VARCHAR    │  ← UNIQUE constraint                │

│  │    vehicle_type   ENUM       │                                     │

│  │    brand          VARCHAR    │                                     │

│  │    model          VARCHAR    │                                     │

│  │    color          VARCHAR    │                                     │

│  │    is_default     BOOLEAN    │                                     │

│  │    created_at     DATETIME   │                                     │

│  └──────────────────────────────┘                                     │

└────────────────────────────────────────────────────────────────────────┘

┌─── Booking Service (DENORMALIZED) ────────────────────────────────────┐

│                                                                        │

│  ┌──────────────────────────────────────────────────────────────────┐ │

│  │                        booking                                    │ │

│  │──────────────────────────────────────────────────────────────────│ │

│  │ PK id                   UUID CHAR(36)                             │ │

│  │                                                                    │ │

│  │ ── User Info (copy từ auth-service) ──                            │ │

│  │    user_id              UUID                                      │ │

│  │    user_email           VARCHAR(255)                               │ │

│  │                                                                    │ │

│  │ ── Vehicle Info (copy từ vehicle-service) ──                      │ │

│  │    vehicle_id           UUID                                      │ │

│  │    vehicle_license_plate VARCHAR(20)                               │ │

│  │    vehicle_type         ENUM(Car, Motorbike)                      │ │

│  │                                                                    │ │

│  │ ── Parking Info (copy từ parking-service) ──                      │ │

│  │    parking_lot_id       UUID                                      │ │

│  │    parking_lot_name     VARCHAR(255)                               │ │

│  │    floor_id             UUID                                      │ │

│  │    zone_id              UUID                                      │ │

│  │    zone_name            VARCHAR(255)                               │ │

│  │    slot_id              UUID                                      │ │

│  │    slot_code            VARCHAR(20)                                │ │

│  │                                                                    │ │

│  │ ── Booking Details ──                                             │ │

│  │    package_type         ENUM(hourly, daily, weekly, monthly)      │ │

│  │    start_time           DATETIME                                  │ │

│  │    end_time             DATETIME                                  │ │

│  │    payment_method       ENUM(online, on_exit)                     │ │

│  │    payment_status       ENUM(pending, paid, refunded)             │ │

│  │    price                DECIMAL(10,2)                              │ │

│  │    check_in_status      ENUM(not_checked_in, checked_in,         │ │

│  │                              checked_out, cancelled, expired)     │ │

│  │    checked_in_at        DATETIME NULL                             │ │

│  │    checked_out_at       DATETIME NULL                             │ │

│  │    qr_code_data         TEXT                                      │ │

│  │    hourly_start         DATETIME NULL                             │ │

│  │    hourly_end           DATETIME NULL                             │ │

│  │    extended_until       DATETIME NULL                             │ │

│  │    late_fee_applied     BOOLEAN DEFAULT FALSE                     │ │

│  │    created_at           DATETIME                                  │ │

│  │    updated_at           DATETIME                                  │ │

│  └──────────────────────────────────────────────────────────────────┘ │

│                                                                        │

│  ┌──────────────────────────┐     ┌──────────────────────────────────┐│

│  │   package_pricing         │     │         incident                 ││

│  │──────────────────────────│     │──────────────────────────────────││

│  │ PK id       UUID         │     │ PK id              UUID          ││

│  │    package_type ENUM     │     │    user_id          UUID          ││

│  │    vehicle_type ENUM     │     │    type  ENUM(emergency, theft,  ││

│  │    price    DECIMAL(10,2)│     │         vehicle_damage, accident,││

│  │    duration_days INT     │     │         suspicious_activity)     ││

│  └──────────────────────────┘     │    description      TEXT          ││

│                                   │    status ENUM(open, in_progress,││

│                                   │           resolved, closed)      ││

│                                   │    booking_id       UUID NULL     ││

│                                   │    parking_lot_id   UUID NULL     ││

│                                   │    zone_id          UUID NULL     ││

│                                   │    slot_id          UUID NULL     ││

│                                   │    latitude         DECIMAL NULL  ││

│                                   │    longitude        DECIMAL NULL  ││

│                                   │    security_notified BOOLEAN      ││

│                                   │    resolved_at      DATETIME NULL ││

│                                   │    resolution_notes TEXT NULL     ││

│                                   │    created_at       DATETIME      ││

│                                   └──────────────────────────────────┘│

└────────────────────────────────────────────────────────────────────────┘

┌─── Chatbot / AI Tables (init-mysql.sql) ──────────────────────────────┐

│                                                                        │

│  chatbot_conversations    — Phiên hội thoại (user_id, started_at)     │

│  chatbot_messages         — Tin nhắn (conversation_id, role, content) │

│  chatbot_user_behavior    — Hành vi người dùng (preferences, stats)   │

│  chatbot_intents          — Intent definitions và training data       │

│  chatbot_entities         — Entity types và values                    │

│  chatbot_wizard_sessions  — Booking wizard state (multi-step)         │

│  chatbot_feedback         — User feedback trên chatbot responses      │

│  ai_predictions           — Kết quả AI predictions (plate, slot)      │

│  ai_metrics               — Metrics: latency, accuracy, error rates   │

│                                                                        │

└────────────────────────────────────────────────────────────────────────┘

```

#### Giải thích Denormalization trong Booking

Trong kiến trúc microservices, nguyên tắc **Database-per-Service** đòi hỏi mỗi service chỉ truy cập trực tiếp database của chính nó. Tuy nhiên, bảng `booking` cần thông tin từ nhiều service khác (user email từ auth, biển số xe từ vehicle, mã ô đỗ từ parking). Thay vì thực hiện **network call** qua API đến các service khác mỗi khi cần hiển thị thông tin booking (gây N+1 query, tăng latency, phụ thuộc vào availability của service khác), giải pháp được chọn là **data denormalization** — sao chép (copy) một bản các thông tin cần thiết vào bảng booking tại thời điểm tạo.

**Ưu điểm:**

- Giảm thiểu network round-trip: booking-service trả đầy đủ thông tin trong 1 query
- Tăng tính độc lập: booking-service vẫn hoạt động ngay cả khi auth/vehicle/parking-service tạm ngừng
- Cải thiện hiệu năng đọc (read-heavy workload)

**Đánh đổi:**

- Dữ liệu sao chép có thể trở nên không đồng bộ (stale) khi source data thay đổi
- Tăng dung lượng lưu trữ (trùng lặp dữ liệu)
- Cần cơ chế sync khi user đổi email hoặc biển số xe

### 3.3.3. Thiết kế giao diện

Giao diện người dùng ParkSmart được xây dựng dưới dạng Single Page Application (SPA) sử dụng React 18.3.1, hỗ trợ **responsive design** (desktop + tablet + mobile) và **dark/light mode** chuyển đổi tức thời. Hệ thống gồm **28 trang** chia thành 2 nhóm chính:

#### Trang Root (19 trang)

| #   | Tên trang              | Route                 | Mô tả chức năng                                                                    |
| --- | ---------------------- | --------------------- | ---------------------------------------------------------------------------------- |
| 1   | **Login**              | `/login`              | Đăng nhập email/password, nút OAuth Google/Facebook, remember me                   |
| 2   | **Register**           | `/register`           | Đăng ký tài khoản mới: email, password, tên, SĐT, đồng ý điều khoản                |
| 3   | **Dashboard**          | `/`                   | Tổng quan: booking hiện tại, thông báo, thống kê cá nhân                           |
| 4   | **Booking**            | `/booking`            | Đặt chỗ multi-step wizard: lot → floor → zone → slot → vehicle → package → confirm |
| 5   | **History**            | `/history`            | Lịch sử booking: bảng paginated, filter theo status/date, chi tiết từng booking    |
| 6   | **Map**                | `/map`                | Bản đồ bãi xe realtime: slot grid (xanh/đỏ/vàng), filter tầng/zone, WebSocket live |
| 7   | **Cameras**            | `/cameras`            | Live camera feeds: grid view, fullscreen, AI detection overlay                     |
| 8   | **Check-in/out**       | `/check-in-out`       | Giao diện QR check-in/out, hướng dẫn sử dụng tại cổng                              |
| 9   | **Payment**            | `/payment`            | Thanh toán online: chọn booking, phương thức, xác nhận                             |
| 10  | **Banknote Detection** | `/banknote-detection` | AI nhận dạng tiền giấy: camera preview, detect mệnh giá, tích lũy                  |
| 11  | **Settings**           | `/settings`           | Profile: thông tin cá nhân, đổi mật khẩu, quản lý xe (CRUD vehicle)                |
| 12  | **Support**            | `/support`            | Chatbot AI: giao diện chat, FAQ, booking wizard qua hội thoại                      |
| 13  | **Panic**              | `/panic`              | Báo sự cố khẩn cấp: chọn loại, mô tả, gửi vị trí GPS                               |
| 14  | **Kiosk**              | `/kiosk`              | Chế độ kiosk (public, không cần auth): hiển thị chỗ trống, giá, hướng dẫn          |
| 15  | **Forgot Password**    | `/forgot-password`    | Quên mật khẩu: nhập email, gửi link reset                                          |
| 16  | **Reset Password**     | `/reset-password`     | Đặt lại mật khẩu từ link email                                                     |
| 17  | **Vehicle Management** | `/vehicles`           | Quản lý phương tiện riêng: thêm/sửa/xóa xe, đặt xe mặc định                        |
| 18  | **Notifications**      | `/notifications`      | Danh sách thông báo: booking updates, reminders, proactive alerts                  |
| 19  | **Auth Callback**      | `/auth/callback`      | Xử lý OAuth callback: nhận token, redirect sau đăng nhập social                    |

#### Trang Admin (9 trang)

| #   | Tên trang             | Route               | Mô tả chức năng                                                         |
| --- | --------------------- | ------------------- | ----------------------------------------------------------------------- |
| 1   | **Admin Dashboard**   | `/admin/dashboard`  | Thống kê tổng quan: tổng user, booking hôm nay, doanh thu, biểu đồ      |
| 2   | **User Management**   | `/admin/users`      | CRUD users: bảng paginated, search, filter role, lock/unlock account    |
| 3   | **Zone Management**   | `/admin/zones`      | Quản lý zones: CRUD, gán vào floor, cấu hình capacity, vehicle_type     |
| 4   | **Slot Management**   | `/admin/slots`      | Quản lý ô đỗ: CRUD, cấu hình bbox AI (x1,y1,x2,y2), assign camera       |
| 5   | **Camera Management** | `/admin/cameras`    | CRUD cameras: IP, port, stream URL, gán zone, test connection           |
| 6   | **System Config**     | `/admin/config`     | Cấu hình hệ thống: giá gói, thời gian mặc định, thông số hệ thống       |
| 7   | **Violations**        | `/admin/violations` | Quản lý sự cố: danh sách incidents, assign, resolve, notes              |
| 8   | **ESP32 Monitor**     | `/admin/esp32`      | Monitor IoT devices: trạng thái online/offline, logs, heartbeat history |
| 9   | **Revenue Analytics** | `/admin/revenue`    | Phân tích doanh thu: biểu đồ theo ngày/tuần/tháng, export, top users    |

---

## 3.4. Kiến trúc hệ thống

### 3.4.1. Mô hình Client-Server và API Gateway Pattern

Hệ thống ParkSmart áp dụng mô hình **Client-Server** kết hợp **API Gateway Pattern**. Toàn bộ communication giữa client (React SPA, ESP32 Device) và backend services đều đi qua một điểm vào duy nhất — **Gateway Service** chạy trên Go Gin framework tại port 8000.

**Vai trò của API Gateway:**

1. **Single Entry Point**: Client chỉ cần biết 1 địa chỉ (gateway:8000), không cần biết địa chỉ từng service.
2. **Session-based Authentication**: Gateway validate session cookie, tra cứu Redis để lấy user session, inject `X-User-ID` header vào request trước khi proxy.
3. **Internal Security**: Mọi request proxy đều kèm header `X-Gateway-Secret` — backend services chỉ chấp nhận request có secret hợp lệ.
4. **Rate Limiting**: Giới hạn request/phút theo IP, sử dụng Redis sliding window counter.
5. **CORS Handling**: Cấu hình Cross-Origin Resource Sharing cho phép React SPA trên domain khác gọi API.
6. **Reverse Proxy**: Routing request đến đúng service dựa trên URL prefix.

**Bảng routing Gateway:**

_Bảng 3.1: Bảng routing của API Gateway_

| URL Prefix         | Service đích                 | Port     | Ghi chú                               |
| ------------------ | ---------------------------- | -------- | ------------------------------------- |
| `/auth/*`          | auth-service                 | 8001     | Login/register bypass auth middleware |
| `/bookings/*`      | booking-service              | 8002     | Yêu cầu authenticated session         |
| `/parking/*`       | parking-service              | 8003     | Một số endpoint public (lots list)    |
| `/vehicles/*`      | vehicle-service              | internal | Yêu cầu authenticated session         |
| `/ai/*`            | ai-service-fastapi           | 8009     | ESP32 dùng X-Device-Token riêng       |
| `/chatbot/*`       | chatbot-service-fastapi      | 8008     | Yêu cầu authenticated session         |
| `/payments/*`      | payment-service-fastapi      | 8007     | Yêu cầu authenticated session         |
| `/notifications/*` | notification-service-fastapi | 8005     | Yêu cầu authenticated session         |
| `/ws/*`            | realtime-service-go          | 8006     | WebSocket upgrade                     |
| `/health/*`        | gateway-service-go           | 8000     | Health check (bypass auth)            |

### 3.4.2. Luồng xử lý dữ liệu tổng quát

Hệ thống ParkSmart có **3 luồng dữ liệu chính** tương ứng với 3 loại client:

**Luồng 1: Browser → Gateway → Services → Database**

```

React SPA (Browser)

  │  Cookie: session_id=xxx

  ▼

Gateway (:8000)

  │  1. Validate session cookie (Redis lookup)

  │  2. Inject: X-User-ID, X-Gateway-Secret headers

  │  3. Route to target service based on URL prefix

  ▼

Backend Service (Django/FastAPI)

  │  1. Verify X-Gateway-Secret

  │  2. Extract X-User-ID

  │  3. Business logic + DB operations

  ▼

MySQL 8.0 (:3307)

  │

  ▼

Response → Gateway → Browser (JSON)

```

**Luồng 2: ESP32 → AI Service → Arduino → Gateway → Backend**

```

ESP32 (WiFi HTTP Client)

  │  Headers: X-Device-Token, X-Gateway-Secret

  │  POST /ai/esp32/check-in/ (hoặc /check-out/)

  ▼

AI Service (:8009)

  │  1. Verify device token

  │  2. Mở camera QR → scan loop 30s → decode booking_id

  │  3. Gọi booking-service validate booking

  │  4. Mở camera plate → YOLO detect → OCR cascade

  │  5. Fuzzy match plate vs booking

  │  6. Gọi booking-service check-in/out

  │  7. Gọi parking-service update slot

  ▼

Response JSON → ESP32

  │  {barrierAction: "open", plateText: "51A-224.56"}

  ▼

ESP32 → UART 9600bps → Arduino

  │  Command: "OPEN_1\n" (entry) hoặc "OPEN_2\n" (exit)

  ▼

Arduino

  │  Servo PWM: 1500μs → 3000μs (mở barrier)

  │  ACK: "ACK_OPEN_1\n"

  │  5s delay → "CLOSE_1\n" (auto-close)

  ▼

ESP32 → I2C → OLED SSD1306 (hiển thị biển số)

```

**Luồng 3: WebSocket Push Flow (Real-time Updates)**

```

Backend Service (booking change, slot update)

  │  Publish event to Redis Pub/Sub channel

  ▼

Realtime Service (:8006, Go + Gorilla WebSocket)

  │  1. Subscribe Redis channels

  │  2. Receive event

  │  3. Route to relevant WebSocket connections

  ▼

WebSocket Hub

  │  Broadcast to all connected clients

  ▼

React SPA (useWebSocket hook)

  │  1. Receive slot_update event

  │  2. Update Redux store

  │  3. Re-render Map component (slot color change)

```

### 3.4.3. Ưu điểm kiến trúc

Kiến trúc microservices của ParkSmart mang lại nhiều lợi ích thiết thực:

**1. Khả năng mở rộng từng thành phần (Independent Scaling)**

Mỗi service chạy trong Docker container riêng biệt, có thể scale theo nhu cầu thực tế. Ví dụ: booking-service đã được mở rộng thành 3 containers (main + celery-worker + celery-beat) để xử lý tác vụ nặng bất đồng bộ. AI service có thể scale riêng khi cần xử lý nhiều camera đồng thời.

**2. Cô lập lỗi (Fault Isolation)**

Lỗi tại một service không ảnh hưởng đến toàn bộ hệ thống. Nếu chatbot-service gặp sự cố, các chức năng đặt chỗ, check-in, bản đồ vẫn hoạt động bình thường. Gateway health check endpoint `/health/services/` cho phép monitoring trạng thái từng service.

**3. Đa dạng công nghệ (Technology Diversity)**

Mỗi service được phát triển bằng công nghệ phù hợp nhất cho chức năng của nó:

- **Django DRF** cho CRUD operations (auth, booking, parking, vehicle) — tận dụng ORM mạnh, admin panel, migration system
- **FastAPI** cho AI inference và async operations (ai, chatbot, payment, notification) — async/await native, hiệu năng cao cho I/O-bound tasks
- **Go Gin** cho gateway và realtime — compiled binary, goroutines xử lý hàng ngàn concurrent connections với overhead cực thấp (~2KB/goroutine)

**4. Phát triển độc lập (Independent Development)**

Các service giao tiếp qua API contracts rõ ràng (HTTP REST + JSON). Mỗi service có thể được phát triển, test, và deploy độc lập mà không ảnh hưởng đến service khác. Điều này cho phép song song hóa quá trình phát triển.

**5. Resilience qua Data Denormalization**

Booking service lưu bản sao (denormalized) thông tin từ auth, vehicle, parking — đảm bảo vẫn hoạt động ngay cả khi các service phụ thuộc tạm ngừng.

### 3.4.4. Nhược điểm kiến trúc

Bên cạnh những lợi ích rõ ràng, kiến trúc microservices cũng mang theo các thách thức cần lưu ý:

**1. Độ phức tạp vận hành (Operational Complexity)**

Với 15 Docker container chạy đồng thời, việc khởi động, giám sát, và bảo trì hệ thống đòi hỏi nhiều tài nguyên hơn so với ứng dụng monolith truyền thống. Máy chủ phát triển cần tối thiểu 8 GB RAM để chạy đầy đủ các services.

**2. Độ trễ mạng giữa các dịch vụ (Network Latency)**

Mỗi request cần đi qua Gateway rồi đến service đích, và một số nghiệp vụ (như đặt chỗ) yêu cầu gọi chuỗi nhiều services — tăng latency tổng so với gọi hàm nội bộ trong monolith. ParkSmart giảm thiểu vấn đề này bằng data denormalization và Redis caching.

**3. Nhất quán dữ liệu (Data Consistency)**

Mỗi service sở hữu bộ bảng riêng, dữ liệu denormalized có thể trở nên không đồng bộ (stale) khi source data thay đổi. Hệ thống hiện chấp nhận mô hình **eventual consistency** — phù hợp với bài toán bãi xe nhưng cần cơ chế sync nếu mở rộng.

**4. Debug và Tracing phức tạp**

Một request đặt chỗ đi qua 4–5 services; khi xảy ra lỗi, việc xác định nguyên nhân gốc khó hơn vì logs phân tán ở nhiều container. Hiện tại đang sử dụng `X-Request-ID` header để correlate logs, nhưng chưa có hệ thống distributed tracing tập trung (xem hướng phát triển tại **Mục 4.2**).

---

## 3.5. Kết quả đạt được

### 3.5.1. Đặt chỗ online (Online Booking)

Chức năng đặt chỗ online là tính năng cốt lõi của hệ thống, cho phép người dùng đặt trước ô đỗ xe qua giao diện web mà không cần đến bãi xe trực tiếp.

**Tính năng đã triển khai:**

- **Multi-step booking wizard**: Quy trình đặt chỗ được chia thành nhiều bước tuần tự (chọn bãi → tầng → zone → ô đỗ → xe → gói thời gian → phương thức thanh toán → xác nhận), mỗi bước hiển thị thông tin liên quan và cho phép quay lại bước trước.
- **4 gói thời gian**: hourly (theo giờ), daily (theo ngày), weekly (theo tuần), monthly (theo tháng) — giá được cấu hình linh hoạt qua bảng `package_pricing` theo loại xe (Car/Motorbike).
- **2 phương thức thanh toán**: online (trả trước qua cổng thanh toán) và on_exit (trả khi ra bãi). Hệ thống tự động áp dụng `force_online_payment` cho users có lịch sử no-show.
- **QR code tự động**: Mỗi booking được tự động sinh mã QR chứa booking_id (UUID), sử dụng tại cổng check-in.
- **Real-time slot updates**: Trạng thái ô đỗ được cập nhật tức thời qua WebSocket — khi một user đặt ô, tất cả users khác đang xem bản đồ sẽ thấy ô đó chuyển sang màu vàng (reserved) ngay lập tức.
- **Auto-expire bookings**: Celery Beat chạy task định kỳ, tự động hủy booking quá hạn mà chưa check-in, giải phóng ô đỗ.

### 3.5.2. Chatbot AI (Trợ lý ảo thông minh)

Chatbot ParkSmart là trợ lý ảo 24/7 hỗ trợ tiếng Việt, tích hợp Google Gemini LLM (gemini-3-flash-preview) với pipeline xử lý đa tầng (chi tiết lý thuyết pipeline tại **Mục 2.8**).

**Kết quả triển khai:**

- **16 loại intent** đã được định nghĩa và phân loại chi tiết tại **Mục 2.8.2** (bao gồm GREETING, BOOKING_CREATE, SLOT_INQUIRY, INCIDENT_REPORT, v.v.), mỗi intent có ví dụ câu nói và hành vi xử lý tương ứng.
- **Booking Wizard**: Cho phép đặt chỗ hoàn toàn qua hội thoại tự nhiên, dẫn dắt người dùng qua từng bước (chọn tầng → zone → xác nhận đặt chỗ) không cần sử dụng giao diện đồ họa.
- **Confidence Gate**: Ngưỡng tin cậy 3 mức (High ≥0.75, Medium 0.50–0.75, Low <0.50) với các hành động nhạy cảm như đặt chỗ yêu cầu confidence ≥0.85.
- **Hybrid Confidence Scoring**: $Confidence = 0.5 \times LLM_{score} + 0.3 \times Entity_{score} + 0.2 \times Context_{score}$
- **Tham số LLM**: temperature=0.3 (ưu tiên chính xác), top_p=0.9, max_tokens=1024.

### 3.5.3. Xem bản đồ bãi xe (Real-time Map)

Trang bản đồ bãi xe cung cấp giao diện trực quan để người dùng xem trạng thái từng ô đỗ trong thời gian thực.

**Tính năng đã triển khai:**

- **Slot grid view**: Mỗi ô đỗ được biểu diễn trên lưới 2D, mã màu theo trạng thái:
  - 🟢 **Xanh** (available): Ô trống, có thể đặt
  - 🔴 **Đỏ** (occupied): Đang có xe đỗ
  - 🟡 **Vàng** (reserved): Đã được đặt trước, chưa check-in
  - ⚫ **Xám** (disabled): Không khả dụng (bảo trì)
- **WebSocket live updates**: Kết nối native WebSocket đến realtime-service (:8006). Mỗi khi slot status thay đổi (đặt chỗ, check-in, check-out), event được broadcast đến tất cả clients trong < 100ms.
- **Filter theo tầng/zone**: Người dùng có thể lọc xem theo tầng (Floor 0, Floor 1) và zone (Zone A, Zone B...) để nhanh chóng tìm ô trống.
- **Thông tin chi tiết slot**: Click vào ô đỗ hiển thị tooltip: mã ô (slot_code), trạng thái, thông tin booking nếu có.

**Dữ liệu bãi xe thực tế:**

- 2 tầng, tổng cộng 158 ô đỗ
- Tầng 0: 72 car slots (4 rows × 18) + 20 moto + 5 garage
- Tầng 1: 36 car slots (2 rows × 18) + 20 moto + 5 garage
- Kích thước ô đỗ: 2.5m × 5m

### 3.5.4. Check-in IoT + AI (Kiểm soát cổng tự động)

Đây là tính năng kết hợp phần cứng IoT và trí tuệ nhân tạo, cho phép check-in/check-out hoàn toàn tự động tại cổng bãi xe. Luồng xử lý chi tiết được mô tả tại **UC06** (Mục 3.2.2) và **Flow 2** (Mục 3.3.1).

**Thành phần phần cứng:**

| Thiết bị        | Vai trò                                                  | Giao tiếp                                         |
| --------------- | -------------------------------------------------------- | ------------------------------------------------- |
| ESP32           | IoT gateway: kết nối WiFi, xử lý nút nhấn, hiển thị OLED | HTTP REST → AI Server, I2C → OLED, UART → Arduino |
| Arduino         | Điều khiển 2 servo barrier (cổng vào/ra)                 | UART 9600bps từ ESP32                             |
| Camera DroidCam | Thu hình mã QR booking                                   | HTTP stream                                       |
| Camera EZVIZ    | Thu hình biển số xe                                      | RTSP stream                                       |
| OLED SSD1306    | Hiển thị biển số, trạng thái                             | I2C 128×64 pixel                                  |

**Kết quả đạt được:**

- **Quy trình hoàn toàn tự động**: Từ lúc nhấn nút đến barrier mở, toàn bộ luồng (QR scan → booking validation → plate OCR → fuzzy matching → barrier control) không cần nhân viên can thiệp.
- **AI Pipeline cascade**: YOLO detect biển số → TrOCR OCR (fallback EasyOCR → Tesseract) → Vietnamese plate format validation → fuzzy matching cho phép ≤3 ký tự sai.
- **Camera fallback**: Nếu camera biển số không khả dụng, hệ thống vẫn cho phép check-in chỉ với QR (giảm bảo mật, ghi log cảnh báo).
- **Auto-close barrier**: Barrier tự động đóng sau 5 giây, có ACK từ Arduino xác nhận thành công.
- **Heartbeat monitoring**: ESP32 gửi heartbeat mỗi 10 giây; server đánh dấu offline nếu không nhận sau 30 giây, thông báo admin.

**Slot Occupancy Detection (bổ sung):**

Ngoài kiểm soát cổng, AI Service còn phát hiện trạng thái ô đỗ qua camera overview sử dụng YOLO11n (nano) với IoU matching (≥0.15), kết hợp fallback OpenCV (edge density + contour + color variance). Kết quả được sync về parking-service cập nhật trạng thái slot realtime.

### 3.5.5. Mô phỏng bãi xe 3D (Parking Simulator — Digital Twin)

ParkSmart phát triển ứng dụng mô phỏng 3D bằng Unity 2022.3 LTS, đóng vai trò **Digital Twin** (bản sao kỹ thuật số) của bãi giữ xe thực tế — cho phép kiểm thử toàn bộ pipeline (AI, WebSocket, IoT, Booking) mà không cần triển khai phần cứng.

**Thành phần chính:**

| Thành phần                | Mô tả                                                                                                                                         |
| ------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| Procedural Lot Generation | 2 tầng, 158 ô đỗ (72+20+5 tầng B1, 36+20+5 tầng 1) được tạo runtime từ parameters — thay đổi layout không cần redesign scene                  |
| 6 Virtual Cameras         | 2 overview (top-down 80°), 2 gate (angled 60°), 2 zone (65°) — RenderTexture 640×480 → JPEG → POST AI Service 5fps                            |
| Vehicle State Machine     | 11 trạng thái: Idle → ApproachingGate → WaitingAtGate → Entering → Navigating → Parking → Parked → Departing → WaitingAtExit → Exiting → Gone |
| BFS Pathfinding           | WaypointGraph adjacency list, tìm đường ngắn nhất từ gate đến slot entrance                                                                   |
| ESP32 Simulator           | IMGUI panel mô phỏng hardware: check-in/check-out, QR scan, thanh toán tiền mặt — gọi cùng API endpoint như ESP32 thật                        |
| NativeWebSocket Real-time | Nhận slot_status_update từ Realtime Service (:8006), cập nhật màu slot với Lerp animation                                                     |
| Gate Camera AI Pipeline   | Physics.OverlapSphere detect xe → capture RenderTexture → AI OCR → verify booking → mở barrier tự động                                        |

**Kết quả đạt được:**

- **API-first testing**: Unity sử dụng cùng API endpoints như ứng dụng thật (Gateway :8000, AI :8009, WebSocket :8006) — mọi bug backend được phát hiện sớm trong quá trình phát triển.
- **Virtual camera pipeline**: 6 camera ảo streaming JPEG frames giống camera RTSP/DroidCam thật — AI Service xử lý frame Unity và frame thật bằng cùng pipeline, đảm bảo tính nhất quán.
- **Offline development**: Mock mode cho phép phát triển Unity offline hoàn toàn (MockDataProvider sinh dữ liệu giả), sau đó chuyển sang backend thật chỉ bằng toggle `useMockData`.
- **Test coverage**: 6 test files NUnit (3 EditMode + 3 PlayMode) kiểm thử: JSON serialization, BFS pathfinding, barrier animation, slot state transitions, booking state management.

---

# Chương 4. KẾT LUẬN VÀ HƯỚNG PHÁT TRIỂN

---

## 4.1. Kết luận

### 4.1.1. Kết quả đạt được

Sau quá trình nghiên cứu và phát triển, hệ thống bãi giữ xe thông minh ParkSmart đã hoàn thành **9 chức năng chính** đáp ứng đầy đủ mục tiêu đề ra:

| #   | Chức năng             | Mô tả kết quả                                                                                             |
| --- | --------------------- | --------------------------------------------------------------------------------------------------------- |
| 1   | **Đặt chỗ online**    | Multi-step wizard, 4 gói thời gian, 2 phương thức thanh toán, QR code tự động, realtime slot updates      |
| 2   | **Check-in/out IoT**  | ESP32 + Arduino full autonomous flow: QR scan → plate OCR → validate → barrier control → auto-close 5s    |
| 3   | **Chatbot AI**        | Pipeline v3.0 + Gemini LLM, 16 intents, booking wizard, confidence gate, tiếng Việt (hỗ trợ không dấu)    |
| 4   | **Bản đồ realtime**   | Slot grid view + WebSocket live updates, 158 ô đỗ, 2 tầng, filter tầng/zone                               |
| 5   | **Nhận dạng biển số** | YOLOv8 + TrOCR cascade (EasyOCR → Tesseract fallback), fuzzy matching ≤3 ký tự                            |
| 6   | **Nhận dạng tiền**    | MobileNetV3-Large multi-branch (4 branches, 1088-dim fusion) + HSV color, cash session tích lũy           |
| 7   | **Admin dashboard**   | Quản lý đầy đủ: users, bãi xe, zones, slots, cameras, ESP32 devices, revenue analytics                    |
| 8   | **Báo sự cố (Panic)** | 5 loại sự cố, geolocation, notify security, resolution workflow                                           |
| 9   | **Mô phỏng 3D**       | Unity Digital Twin: 158 slots procedural, 6 virtual cameras, vehicle FSM, ESP32 simulator, API-first test |

**Quy mô hệ thống:**

- **10 microservices** (4 Django + 4 FastAPI + 2 Go), **15 Docker containers**
- **28 trang giao diện** (19 root + 9 admin), responsive dark/light mode
- **73 tổng UI components** (51 shadcn/ui + 22 custom)
- **5 AI pipelines** (plate, slot, QR, banknote, cash)
- **Phần cứng IoT** thực tế: ESP32 + Arduino + 2 Servo + OLED + 2 Camera
- **Parking Simulator 3D** (Unity 2022.3 LTS): 30 C# scripts, 6 virtual cameras, 158 ô đỗ procedural
- **9 MySQL tables** cho chatbot, cùng tables cho auth, parking, vehicle, booking do ORM quản lý

### 4.1.2. Các bài toán đã được giải quyết

Đối chiếu với năm hạn chế của mô hình bãi giữ xe truyền thống đã phân tích tại Chương 1, hệ thống ParkSmart đã cung cấp giải pháp tương ứng cho cả năm nhóm bài toán:

| #   | Hạn chế của mô hình truyền thống                                              | Giải pháp mà ParkSmart cung cấp                                                                                          |
| --- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------ |
| 1   | **Ùn tắc tại cổng ra/vào** — quy trình thủ công mất 30–60 giây mỗi lượt       | Quy trình check-in/check-out hoàn toàn tự động qua IoT và AI: quét QR, nhận dạng biển số và mở barrier trong dưới 15 giây |
| 2   | **Rủi ro mất vé và gian lận** — vé giấy dễ làm giả, thất lạc                  | Mã QR kỹ thuật số với UUID duy nhất, kết hợp xác minh chéo biển số xe bằng AI                                             |
| 3   | **Người dùng không biết trước còn chỗ trống** — phải di chuyển tìm kiếm        | Đặt chỗ trực tuyến, bản đồ thời gian thực qua WebSocket và trợ lý chatbot hỗ trợ tra cứu                                  |
| 4   | **Quản lý doanh thu thiếu minh bạch** — thu tiền mặt, ghi sổ thủ công         | Hệ thống thanh toán điện tử, AI nhận dạng tiền mặt tại quầy và dashboard phân tích doanh thu cho quản trị viên            |
| 5   | **Thiếu dữ liệu phân tích** — không có số liệu điện tử để khai thác           | Cơ sở dữ liệu lưu trữ đầy đủ lịch sử booking, kết quả AI, chỉ số chatbot và nhật ký hoạt động thiết bị IoT                |

### 4.1.3. Đánh giá ưu điểm và hạn chế của hệ thống

| Tiêu chí      | Ưu điểm                                                                                            | Khuyết điểm                                                                            | Hướng khắc phục                                                      |
| ------------- | -------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- | -------------------------------------------------------------------- |
| **Kiến trúc** | Microservices thực thụ, 10 services đa ngôn ngữ, Docker containerized, fault isolation             | Hệ thống phức tạp, cần nhiều tài nguyên (15 containers), network latency giữa services | Kubernetes orchestration, service mesh (xem Mục 4.2)                 |
| **AI/ML**     | 5 pipelines production-grade, cascade fallback cho plate OCR, YOLO11n nano cho real-time           | Phụ thuộc chất lượng camera và ánh sáng, TrOCR yêu cầu GPU cho inference nhanh         | Edge AI (Jetson Nano/Coral TPU), thêm training data biển số Việt Nam |
| **IoT**       | Phần cứng thực tế (ESP32 + Arduino), giao thức UART tự thiết kế, heartbeat monitoring              | Chưa có OTA firmware update, phụ thuộc WiFi stability, chưa có battery backup          | OTA qua ESP-IDF, UPS backup, multi-gateway failover                  |
| **Chatbot**   | LLM Gemini hỗ trợ tiếng Việt tốt, booking wizard, confidence gate, proactive notifications         | Phụ thuộc Google Gemini API (external), chi phí token, latency ~1–3s                   | LLM caching, local model fallback, quota monitoring                  |
| **Frontend**  | 73 tổng UI components (51 shadcn/ui + 22 custom), dark/light mode, responsive, Redux + React Query | 28 trang giao diện nhiều code, bundle size tương đối lớn                               | Code-splitting, lazy loading, tree-shaking tối ưu                    |
| **Security**  | 3-layer auth (session + gateway secret + device token), CSRF cookies, parameterized queries        | Chưa triển khai 2FA, chưa có API key rotation tự động                                  | 2FA OTP (SMS/email), secret rotation schedule, WAF                   |
| **Testing**   | Playwright E2E, pytest unit/integration, Vitest, seed scripts                                      | Chưa đạt coverage 80% cho mọi service, chưa có load testing                            | Mở rộng test suite, k6/Locust load testing                           |

---

## 4.2. Hướng phát triển

### 4.2.1. Các hạn chế hiện tại của hệ thống

Mặc dù đã hoàn thành các mục tiêu chính đặt ra, hệ thống ParkSmart vẫn còn một số hạn chế cần được khắc phục trong các phiên bản tiếp theo:

1. **Hiệu năng AI trên thiết bị biên còn hạn chế**: Toàn bộ AI inference hiện được thực thi trên máy chủ trung tâm (CPU/GPU), chưa được tối ưu cho triển khai ở biên (edge deployment). Khi số lượng camera tăng lên, máy chủ có khả năng quá tải — đây là một giới hạn về mặt mở rộng quy mô.
2. **Tích hợp thanh toán thực tế chưa hoàn thiện**: Dịch vụ Payment Service hiện ở mức nguyên mẫu (prototype), chưa tích hợp các cổng thanh toán thương mại phổ biến tại Việt Nam như VNPay, MoMo hay ZaloPay. Pipeline nhận dạng tiền mặt cũng cần bổ sung thêm dữ liệu huấn luyện để cải thiện độ chính xác.
3. **Lớp bảo mật nâng cao chưa được triển khai**: Hệ thống chưa hỗ trợ xác thực hai yếu tố (Two-Factor Authentication — 2FA), chưa có cơ chế xoay khóa API tự động (automatic API key rotation), và chưa được bảo vệ bởi tường lửa ứng dụng web (Web Application Firewall — WAF).
4. **Thiếu hạ tầng giám sát và quan sát (Monitoring và Observability)**: Hệ thống chưa tích hợp các công cụ giám sát tập trung như Prometheus và Grafana, nhật ký tập trung như ELK Stack, hay truy vết phân tán như Jaeger — các thành phần cần thiết cho vận hành sản xuất quy mô lớn.
5. **Chưa có ứng dụng di động gốc**: Phía người dùng hiện chỉ có phiên bản web đáp ứng (responsive web), chưa có ứng dụng di động gốc (native mobile app) trên iOS hoặc Android để mang lại trải nghiệm tối ưu trên thiết bị di động.
6. **Quy mô IoT còn giới hạn**: Hệ thống IoT hiện chỉ hỗ trợ một cổng vào và một cổng ra. Để triển khai ở các bãi xe quy mô lớn với nhiều cổng, cần mở rộng để hỗ trợ nhiều thiết bị ESP32 hoạt động song song dưới sự điều phối của một lớp quản lý trung tâm.

### 4.2.2. Định hướng phát triển trong tương lai

**a) Ngắn hạn (3–6 tháng):**

- Tích hợp cổng thanh toán VNPay/MoMo cho payment service
- Triển khai 2FA (OTP qua SMS/email) cho auth service
- Setup Prometheus + Grafana monitoring cho toàn bộ 10 services
- Cải thiện AI model accuracy: thu thập thêm training data biển số Việt Nam, retrain YOLO + TrOCR
- Viết thêm unit tests đạt coverage ≥ 80% cho mọi service

**b) Trung hạn (6–12 tháng):**

- Phát triển React Native mobile app (shared business logic với web)
- Triển khai YOLO inference trên edge device (Jetson Nano / Coral TPU) gần camera, giảm tải server
- Tích hợp ELK Stack (Elasticsearch + Logstash + Kibana) cho centralized logging
- Dynamic pricing: AI phân tích lịch sử booking để đề xuất giá linh hoạt theo giờ cao/thấp điểm
- OTA firmware update cho ESP32 fleet

**c) Dài hạn (12+ tháng):**

- Kubernetes orchestration thay Docker Compose cho production deployment
- Multi-tenant architecture: một instance phục vụ nhiều bãi xe khác nhau
- Computer Vision nâng cao: nhận dạng loại xe, màu xe, phát hiện va chạm tự động
- Tích hợp cảm biến IoT bổ sung: cảm biến siêu âm/từ trường tại mỗi ô đỗ
- AI predictive analytics: dự báo nhu cầu đỗ xe theo thời gian, sự kiện, thời tiết

---

# TÀI LIỆU THAM KHẢO

---

[1] Django Software Foundation, "Django documentation — Django 5.2," [Trực tuyến]. Địa chỉ: https://docs.djangoproject.com/en/5.2/. [Truy cập: 2026].

[2] T. Christie, "Django REST Framework," [Trực tuyến]. Địa chỉ: https://www.django-rest-framework.org/. [Truy cập: 2026].

[3] S. Ramírez, "FastAPI — Modern, fast (high-performance), web framework for building APIs," [Trực tuyến]. Địa chỉ: https://fastapi.tiangolo.com/. [Truy cập: 2026].

[4] The Go Authors, "The Go Programming Language Specification," [Trực tuyến]. Địa chỉ: https://go.dev/doc/. [Truy cập: 2026].

[5] Gin Contributors, "Gin Web Framework — Documentation," [Trực tuyến]. Địa chỉ: https://gin-gonic.com/docs/. [Truy cập: 2026].

[6] Gorilla Web Toolkit, "gorilla/websocket — A fast, well-tested and widely used WebSocket implementation for Go," [Trực tuyến]. Địa chỉ: https://github.com/gorilla/websocket. [Truy cập: 2026].

[7] Meta (Facebook), "React — A JavaScript library for building user interfaces," [Trực tuyến]. Địa chỉ: https://react.dev/. [Truy cập: 2026].

[8] Evan You et al., "Vite — Next Generation Frontend Tooling," [Trực tuyến]. Địa chỉ: https://vite.dev/. [Truy cập: 2026].

[9] G. Jocher, A. Chaurasia, J. Qiu, "Ultralytics YOLO — State-of-the-Art Object Detection Models," [Trực tuyến]. Địa chỉ: https://docs.ultralytics.com/. [Truy cập: 2026].

[10] J. Redmon, S. Divvala, R. Girshick, A. Farhadi, "You Only Look Once: Unified, Real-Time Object Detection," _Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR)_, 2016, pp. 779–788.

[11] M. Li, T. Lv, L. Cui, Y. Lu, D. Florencio, C. Zhang, Z. Li, F. Wei, "TrOCR: Transformer-based Optical Character Recognition with Pre-trained Models," _Proceedings of the AAAI Conference on Artificial Intelligence_, Vol. 37, No. 11, 2023, pp. 13094–13102.

[12] A. Howard, M. Sandler, G. Chu, L.-C. Chen, B. Chen, M. Tan, W. Wang, Y. Zhu, R. Pang, V. Vasudevan, Q. V. Le, H. Adam, "Searching for MobileNetV3," _Proceedings of the IEEE/CVF International Conference on Computer Vision (ICCV)_, 2019, pp. 1314–1324.

[13] K. He, X. Zhang, S. Ren, J. Sun, "Deep Residual Learning for Image Recognition," _Proceedings of the IEEE Conference on Computer Vision and Pattern Recognition (CVPR)_, 2016, pp. 770–778.

[14] Google, "Gemini API — Google AI for Developers," [Trực tuyến]. Địa chỉ: https://ai.google.dev/gemini-api/docs. [Truy cập: 2026].

[15] Docker Inc., "Docker Documentation — Build, Share, and Run Any App, Anywhere," [Trực tuyến]. Địa chỉ: https://docs.docker.com/. [Truy cập: 2026].

[16] Oracle Corporation, "MySQL 8.0 Reference Manual," [Trực tuyến]. Địa chỉ: https://dev.mysql.com/doc/refman/8.0/en/. [Truy cập: 2026].

[17] Redis Ltd., "Redis Documentation — In-memory data store," [Trực tuyến]. Địa chỉ: https://redis.io/docs/. [Truy cập: 2026].

[18] Broadcom (VMware), "RabbitMQ Documentation," [Trực tuyến]. Địa chỉ: https://www.rabbitmq.com/docs. [Truy cập: 2026].

[19] Espressif Systems, "ESP32 Technical Reference Manual," [Trực tuyến]. Địa chỉ: https://www.espressif.com/en/products/socs/esp32/resources. [Truy cập: 2026].

[20] Arduino, "Arduino Documentation — Reference, Tutorials, and Guides," [Trực tuyến]. Địa chỉ: https://docs.arduino.cc/. [Truy cập: 2026].

[21] shadcn, "shadcn/ui — Beautifully designed components built with Radix UI and Tailwind CSS," [Trực tuyến]. Địa chỉ: https://ui.shadcn.com/. [Truy cập: 2026].

[22] Celery Contributors, "Celery — Distributed Task Queue," [Trực tuyến]. Địa chỉ: https://docs.celeryq.dev/en/stable/. [Truy cập: 2026].

[23] M. Fowler, J. Lewis, "Microservices — a definition of this new architectural term," _martinfowler.com_, 2014. [Trực tuyến]. Địa chỉ: https://martinfowler.com/articles/microservices.html. [Truy cập: 2026].

[24] OpenCV Team, "OpenCV — Open Source Computer Vision Library," [Trực tuyến]. Địa chỉ: https://docs.opencv.org/. [Truy cập: 2026].

[25] M. Erikson et al., "Redux Toolkit — The official, opinionated, batteries-included toolset for efficient Redux development," [Trực tuyến]. Địa chỉ: https://redux-toolkit.js.org/. [Truy cập: 2026].

[26] T. Linsley, "TanStack Query (React Query) — Powerful asynchronous state management," [Trực tuyến]. Địa chỉ: https://tanstack.com/query/latest. [Truy cập: 2026].

[27] Tailwind Labs, "Tailwind CSS — A utility-first CSS framework for rapidly building custom designs," [Trực tuyến]. Địa chỉ: https://tailwindcss.com/docs. [Truy cập: 2026].

[28] Microsoft, "TypeScript — JavaScript With Syntax For Types," [Trực tuyến]. Địa chỉ: https://www.typescriptlang.org/docs/. [Truy cập: 2026].

[29] Remix Software, "React Router — Declarative Routing for React.js," [Trực tuyến]. Địa chỉ: https://reactrouter.com/. [Truy cập: 2026].

[30] Microsoft, "Playwright — Fast and reliable end-to-end testing for modern web apps," [Trực tuyến]. Địa chỉ: https://playwright.dev/docs/intro. [Truy cập: 2026].

[31] Unity Technologies, "Unity User Manual 2022.3 (LTS)," [Trực tuyến]. Địa chỉ: https://docs.unity3d.com/2022.3/Documentation/Manual/. [Truy cập: 2026].

---

# PHỤ LỤC

---

## Phụ lục A: Danh sách API Endpoints

### A.1. Auth Service (Django DRF — Port 8001)

| Method              | Endpoint                       | Mô tả                              | Auth  |
| ------------------- | ------------------------------ | ---------------------------------- | ----- |
| POST                | `/auth/register/`              | Đăng ký tài khoản mới              | No    |
| POST                | `/auth/login/`                 | Đăng nhập (session-based)          | No    |
| POST                | `/auth/logout/`                | Đăng xuất (xóa session)            | Yes   |
| GET                 | `/auth/me/`                    | Lấy thông tin user hiện tại        | Yes   |
| POST                | `/auth/change-password/`       | Đổi mật khẩu                       | Yes   |
| POST                | `/auth/forgot-password/`       | Yêu cầu reset password (gửi email) | No    |
| POST                | `/auth/reset-password/`        | Reset password từ token            | No    |
| GET                 | `/auth/google/`                | Lấy URL OAuth Google               | No    |
| GET                 | `/auth/google/callback/`       | Callback OAuth Google              | No    |
| GET                 | `/auth/facebook/`              | Lấy URL OAuth Facebook             | No    |
| GET                 | `/auth/facebook/callback/`     | Callback OAuth Facebook            | No    |
| GET                 | `/auth/admin/dashboard/stats/` | Thống kê admin dashboard           | Admin |
| GET/PUT             | `/auth/admin/config/`          | Cấu hình hệ thống                  | Admin |
| GET/POST/PUT/DELETE | `/auth/admin/users/`           | CRUD users (admin)                 | Admin |

### A.2. Booking Service (Django DRF + Celery — Port 8002)

| Method         | Endpoint                          | Mô tả                           | Auth     |
| -------------- | --------------------------------- | ------------------------------- | -------- |
| GET            | `/bookings/`                      | Danh sách bookings (user's own) | Yes      |
| POST           | `/bookings/`                      | Tạo booking mới                 | Yes      |
| GET            | `/bookings/{id}/`                 | Chi tiết booking                | Yes      |
| PUT/PATCH      | `/bookings/{id}/`                 | Cập nhật booking                | Yes      |
| DELETE         | `/bookings/{id}/`                 | Hủy booking                     | Yes      |
| POST           | `/bookings/{id}/check-in/`        | Check-in booking                | Internal |
| POST           | `/bookings/{id}/check-out/`       | Check-out booking               | Internal |
| POST           | `/bookings/{id}/cancel/`          | Cancel booking                  | Yes      |
| GET            | `/bookings/current-parking/`      | Booking đang active             | Yes      |
| GET            | `/bookings/upcoming/`             | Bookings sắp tới                | Yes      |
| GET            | `/bookings/stats/`                | Thống kê booking                | Yes      |
| POST           | `/bookings/payment/`              | Khởi tạo thanh toán             | Yes      |
| POST           | `/bookings/payment/verify/`       | Xác minh thanh toán             | Yes      |
| POST           | `/bookings/check-slot-bookings/`  | Kiểm tra slot đã booking        | Yes      |
| GET/POST       | `/bookings/packagepricings/`      | CRUD package pricing            | Admin    |
| GET/PUT/DELETE | `/bookings/packagepricings/{id}/` | Chi tiết package pricing        | Admin    |

### A.3. Parking Service (Django DRF — Port 8003)

| Method               | Endpoint                 | Mô tả                | Auth  |
| -------------------- | ------------------------ | -------------------- | ----- |
| GET/POST             | `/parking/lots/`         | CRUD parking lots    | Mixed |
| GET/PUT/DELETE       | `/parking/lots/{id}/`    | Chi tiết parking lot | Mixed |
| GET/POST             | `/parking/floors/`       | CRUD floors          | Mixed |
| GET/PUT/DELETE       | `/parking/floors/{id}/`  | Chi tiết floor       | Mixed |
| GET/POST             | `/parking/zones/`        | CRUD zones           | Mixed |
| GET/PUT/DELETE       | `/parking/zones/{id}/`   | Chi tiết zone        | Mixed |
| GET/POST             | `/parking/slots/`        | CRUD car slots       | Mixed |
| GET/PUT/PATCH/DELETE | `/parking/slots/{id}/`   | Chi tiết car slot    | Mixed |
| GET/POST             | `/parking/cameras/`      | CRUD cameras         | Admin |
| GET/PUT/DELETE       | `/parking/cameras/{id}/` | Chi tiết camera      | Admin |

### A.4. Vehicle Service (Django DRF — Internal)

| Method    | Endpoint                      | Mô tả           | Auth |
| --------- | ----------------------------- | --------------- | ---- |
| GET       | `/vehicles/`                  | Danh sách xe    | Yes  |
| POST      | `/vehicles/`                  | Thêm xe mới     | Yes  |
| GET       | `/vehicles/{id}/`             | Chi tiết xe     | Yes  |
| PUT/PATCH | `/vehicles/{id}/`             | Cập nhật xe     | Yes  |
| DELETE    | `/vehicles/{id}/`             | Xóa xe          | Yes  |
| POST      | `/vehicles/{id}/set-default/` | Đặt xe mặc định | Yes  |
| GET       | `/vehicles/default/`          | Lấy xe mặc định | Yes  |

### A.5. AI Service (FastAPI — Port 8009)

| Method | Endpoint                  | Mô tả                 | Auth     |
| ------ | ------------------------- | --------------------- | -------- |
| POST   | `/ai/esp32/check-in/`     | ESP32 check-in flow   | Device   |
| POST   | `/ai/esp32/check-out/`    | ESP32 check-out flow  | Device   |
| POST   | `/ai/esp32/register/`     | Đăng ký ESP32 device  | Device   |
| POST   | `/ai/esp32/heartbeat/`    | Device heartbeat      | Device   |
| GET    | `/ai/esp32/status/`       | Trạng thái ESP32      | Admin    |
| POST   | `/ai/detection/plate/`    | Nhận dạng biển số     | Internal |
| POST   | `/ai/detection/qr/`       | Đọc QR code           | Internal |
| POST   | `/ai/detection/banknote/` | Nhận dạng tiền giấy   | Yes      |
| POST   | `/ai/detection/cash/`     | Nhận dạng tiền mặt    | Yes      |
| POST   | `/ai/detection/slot/`     | Detect slot occupancy | Internal |
| POST   | `/ai/cameras/frame/`      | Nhận frame từ camera  | Internal |
| GET    | `/ai/cameras/`            | Danh sách cameras     | Admin    |
| GET    | `/ai/parking/status/`     | Trạng thái bãi xe AI  | Yes      |
| GET    | `/ai/parking/slots/`      | Slot status từ AI     | Yes      |
| POST   | `/ai/training/upload/`    | Upload training data  | Admin    |
| GET    | `/ai/metrics/`            | AI service metrics    | Admin    |
| GET    | `/ai/health/`             | Health check          | No       |

### A.6. Chatbot Service (FastAPI — Port 8008)

| Method  | Endpoint                       | Mô tả                    | Auth     |
| ------- | ------------------------------ | ------------------------ | -------- |
| POST    | `/chatbot/chat/`               | Gửi tin nhắn chatbot     | Yes      |
| GET     | `/chatbot/conversations/`      | Danh sách conversations  | Yes      |
| GET     | `/chatbot/conversations/{id}/` | Chi tiết conversation    | Yes      |
| DELETE  | `/chatbot/conversations/{id}/` | Xóa conversation         | Yes      |
| GET/PUT | `/chatbot/preferences/`        | User preferences chatbot | Yes      |
| GET     | `/chatbot/notifications/`      | Proactive notifications  | Yes      |
| POST    | `/chatbot/actions/booking/`    | Chatbot booking action   | Internal |
| GET     | `/chatbot/health/`             | Health check             | No       |

### A.7. Payment Service (FastAPI — Port 8007)

| Method | Endpoint                      | Mô tả                 | Auth |
| ------ | ----------------------------- | --------------------- | ---- |
| POST   | `/payments/initiate/`         | Khởi tạo thanh toán   | Yes  |
| POST   | `/payments/verify/`           | Xác minh thanh toán   | Yes  |
| GET    | `/payments/history/`          | Lịch sử thanh toán    | Yes  |
| POST   | `/payments/cash-session/`     | Bắt đầu cash session  | Yes  |
| POST   | `/payments/cash-session/add/` | Thêm tiền vào session | Yes  |
| GET    | `/payments/health/`           | Health check          | No   |

### A.8. Notification Service (FastAPI — Port 8005)

| Method | Endpoint                    | Mô tả               | Auth     |
| ------ | --------------------------- | ------------------- | -------- |
| GET    | `/notifications/`           | Danh sách thông báo | Yes      |
| POST   | `/notifications/send/`      | Gửi thông báo       | Internal |
| PATCH  | `/notifications/{id}/read/` | Đánh dấu đã đọc     | Yes      |
| GET    | `/notifications/health/`    | Health check        | No       |

### A.9. Gateway Service (Go Gin — Port 8000)

| Method | Endpoint            | Mô tả                    | Auth    |
| ------ | ------------------- | ------------------------ | ------- |
| GET    | `/health/`          | Gateway health check     | No      |
| GET    | `/health/ready/`    | Readiness probe          | No      |
| GET    | `/health/live/`     | Liveness probe           | No      |
| GET    | `/health/services/` | All services health      | No      |
| ANY    | `/{service}/*path`  | Reverse proxy to service | Depends |

### A.10. Realtime Service (Go Gorilla WS — Port 8006)

| Method | Endpoint                | Mô tả                        | Auth |
| ------ | ----------------------- | ---------------------------- | ---- |
| WS     | `/ws/`                  | WebSocket connection         | Yes  |
| WS     | `/ws/parking/{lot_id}/` | Parking lot specific channel | Yes  |
| GET    | `/health/`              | Health check                 | No   |

---

## Phụ lục B: Cấu hình Docker Compose

```yaml

# docker-compose.yml — ParkSmart Microservices (15 containers)

services:

  # ======== INFRASTRUCTURE ========

  mysql:

    image: mysql:8.0

    container_name: parksmartdb_mysql

    restart: unless-stopped

    environment:

      MYSQL_ROOT_PASSWORD: ${DB_PASSWORD}

      MYSQL_DATABASE: parksmartdb

      MYSQL_USER: ${DB_USER}

      MYSQL_PASSWORD: ${DB_PASSWORD}

    ports:

      - "3307:3306"

    volumes:

      - mysql_data:/var/lib/mysql

      - ./init-mysql.sql:/docker-entrypoint-initdb.d/init.sql

    healthcheck:

      test: ["CMD", "mysqladmin", "ping", "-h", "127.0.0.1"]

      interval: 10s

      timeout: 5s

      retries: 10

      start_period: 60s

  redis:

    image: redis:7-alpine

    container_name: parksmartdb_redis

    restart: unless-stopped

    ports:

      - "6379:6379"

    volumes:

      - redis_data:/data

    healthcheck:

      test: ["CMD", "redis-cli", "ping"]

      interval: 10s

  rabbitmq:

    image: rabbitmq:3-management-alpine

    container_name: parksmartdb_rabbitmq

    restart: unless-stopped

    environment:

      RABBITMQ_DEFAULT_USER: ${RABBITMQ_USER}

      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASS}

    ports:

      - "5672:5672" # AMQP

      - "15672:15672" # Management UI

    healthcheck:

      test: ["CMD", "rabbitmq-diagnostics", "ping"]

      interval: 30s

  # ======== DJANGO SERVICES (4) ========

  auth-service:

    build: ./auth-service

    container_name: auth-service

    ports: ["8001:8000"]

    depends_on:

      mysql: { condition: service_healthy }

      redis: { condition: service_healthy }

  booking-service:

    build: ./booking-service

    container_name: booking-service

    ports: ["8002:8000"]

    depends_on:

      mysql: { condition: service_healthy }

      rabbitmq: { condition: service_healthy }

      redis: { condition: service_healthy }

  booking-celery-worker:

    build: ./booking-service

    container_name: booking-celery-worker

    command: celery -A booking_service worker -l info

    depends_on: [mysql, redis, rabbitmq]

  booking-celery-beat:

    build: ./booking-service

    container_name: booking-celery-beat

    command: celery -A booking_service beat -l info

    depends_on: [redis]

  parking-service:

    build: ./parking-service

    container_name: parking-service

    ports: ["8003:8000"]

    depends_on:

      mysql: { condition: service_healthy }

  vehicle-service:

    build: ./vehicle-service

    container_name: vehicle-service

    # No external port — internal only

    depends_on:

      mysql: { condition: service_healthy }

  # ======== FASTAPI SERVICES (4) ========

  ai-service:

    build: ./ai-service-fastapi

    container_name: ai-service

    ports: ["8009:8009"]

    depends_on:

      mysql: { condition: service_healthy }

    volumes:

      - ai_models:/app/models # AI model files

      - ai_media:/app/media # Captured frames

  chatbot-service:

    build: ./chatbot-service-fastapi

    container_name: chatbot-service

    ports: ["8008:8008"]

    depends_on:

      mysql: { condition: service_healthy }

      redis: { condition: service_healthy }

      rabbitmq: { condition: service_healthy }

  payment-service:

    build: ./payment-service-fastapi

    container_name: payment-service

    ports: ["8007:8007"]

    depends_on:

      mysql: { condition: service_healthy }

  notification-service:

    build: ./notification-service-fastapi

    container_name: notification-service

    ports: ["8005:8005"]

    depends_on:

      mysql: { condition: service_healthy }

  # ======== GO SERVICES (2) ========

  realtime-service:

    build: ./realtime-service-go

    container_name: realtime-service

    ports: ["8006:8006"]

    depends_on:

      redis: { condition: service_healthy }

  gateway-service:

    build: ./gateway-service-go

    container_name: gateway-service

    ports: ["8000:8000"]

    depends_on:

      redis: { condition: service_healthy }

      auth-service: { condition: service_started }

volumes:

  mysql_data:

  redis_data:

  rabbitmq_data:

  ai_models:

  ai_media:

networks:

  default:

    name: parksmart-network

```

**Ghi chú:**

- Tất cả services chia sẻ `parksmart-network` (Docker bridge)
- MySQL, Redis, RabbitMQ dùng persistent volumes
- Infrastructure services có health check, application services chờ infrastructure ready
- Biến môi trường quản lý qua file `.env` (gitignored), mẫu tại `.env.example`

---

## Phụ lục C: ESP32 / Arduino Wiring Diagram

### C.1. Sơ đồ kết nối ESP32

```

                    ┌──────────────────────────┐

                    │         ESP32             │

                    │         DevKit            │

                    │                          │

        [Button]────┤ GPIO4     Check-in Button │

        [Button]────┤ GPIO5     Check-out Button│

                    │                          │

                    │ GPIO16 ──TX──► Arduino RX │  ← UART2 (9600bps)

                    │ GPIO17 ◄──RX── Arduino TX │

                    │                          │

                    │ GPIO21 ──SDA──┐           │  ← I2C

                    │ GPIO22 ──SCL──┤ OLED      │

                    │               │ SSD1306   │

                    │               │ 128×64    │

                    │                          │

                    │ GPIO2  ──LED (Status)     │

                    │                          │

                    │ 3.3V  ──VCC────────────┐ │

                    │ GND   ──GND────────────┤ │

                    │                          │

                    │   WiFi: HTTP REST/JSON   │

                    │   → AI Service :8009     │

                    └──────────────────────────┘

```

### C.2. Sơ đồ kết nối Arduino

```

                    ┌──────────────────────────┐

                    │        Arduino            │

                    │        Uno / Nano         │

                    │                          │

   ESP32 GPIO16 ──►│ RX (Pin 0 hoặc SoftSerial)│  ← UART (9600bps)

   ESP32 GPIO17 ◄──│ TX (Pin 1 hoặc SoftSerial)│

                    │                          │

                    │ Pin10 ──Signal──►[Servo 1]│  ← Entry Barrier

                    │                  (SG90)   │

                    │ Pin9  ──Signal──►[Servo 2]│  ← Exit Barrier

                    │                  (SG90)   │

                    │                          │

                    │ Pin13 ──LED (Status)      │

                    │                          │

                    │ 5V   ──VCC Servos         │

                    │ GND  ──GND Common         │

                    └──────────────────────────┘

```

### C.3. Giao thức UART tùy chỉnh

| Lệnh            | Hướng           | Mô tả                       | Thông số Servo             |
| --------------- | --------------- | --------------------------- | -------------------------- |
| `OPEN_1\n`      | ESP32 → Arduino | Mở barrier cổng vào (entry) | Pin10: PWM 1500μs → 3000μs |
| `CLOSE_1\n`     | ESP32 → Arduino | Đóng barrier cổng vào       | Pin10: PWM 3000μs → 1500μs |
| `OPEN_2\n`      | ESP32 → Arduino | Mở barrier cổng ra (exit)   | Pin9: PWM 1500μs → 3000μs  |
| `CLOSE_2\n`     | ESP32 → Arduino | Đóng barrier cổng ra        | Pin9: PWM 3000μs → 1500μs  |
| `STATUS\n`      | ESP32 → Arduino | Query trạng thái barriers   | —                          |
| `ACK_OPEN_1\n`  | Arduino → ESP32 | Xác nhận đã mở entry        | —                          |
| `ACK_CLOSE_1\n` | Arduino → ESP32 | Xác nhận đã đóng entry      | —                          |
| `ACK_OPEN_2\n`  | Arduino → ESP32 | Xác nhận đã mở exit         | —                          |
| `ACK_CLOSE_2\n` | Arduino → ESP32 | Xác nhận đã đóng exit       | —                          |
| `STATUS_OK\n`   | Arduino → ESP32 | Trạng thái bình thường      | —                          |
| `HEARTBEAT\n`   | ESP32 → Server  | Kiểm tra kết nối (mỗi 10s)  | —                          |

**Thông số truyền thông:**

- Baud rate: 9600 bps
- Data bits: 8
- Parity: None
- Stop bits: 1
- Line ending: `\n` (newline)
- Debounce nút nhấn: 300ms
- Auto-close barrier: 5 giây sau khi mở
- Heartbeat interval: 10 giây
- Offline threshold: 30 giây không có heartbeat
- UART Sanitizer: Lọc ký tự non-ASCII (byte rác do nhiễu điện)

### C.4. Sơ đồ kết nối tổng thể

```

                                         ┌────────────┐

                                    WiFi │  AI Server  │

                               ┌────────►│  :8009     │◄─── Camera RTSP

                               │ HTTP    │  (FastAPI)  │     (EZVIZ)

                               │ REST    └──────┬─────┘

                               │                │

                        ┌──────┴──────┐         │        ┌──────────────┐

    [Check-in Btn]──────┤    ESP32    │         │        │ Camera QR    │

    [Check-out Btn]─────┤             │         └────────│ (DroidCam)   │

    [OLED SSD1306]──I2C─┤  GPIO 21/22│                   └──────────────┘

    [Status LED]────────┤  GPIO 2    │

                        │             │

                        │  GPIO16 TX──┤────UART 9600───┐

                        │  GPIO17 RX──┤◄───────────────┤

                        └─────────────┘                │

                                                ┌──────┴──────┐

                                                │   Arduino    │

                                                │              │

                                    ┌───────────┤  Pin10       │

                                    │  Signal   │  Pin9        ├───────────┐

                                    │           │              │   Signal  │

                                    ▼           └──────────────┘           ▼

                            ┌──────────────┐                    ┌──────────────┐

                            │  Servo SG90  │                    │  Servo SG90  │

                            │  Entry Gate  │                    │  Exit Gate   │

                            │  (Barrier 1) │                    │  (Barrier 2) │

                            └──────────────┘                    └──────────────┘

```

---
