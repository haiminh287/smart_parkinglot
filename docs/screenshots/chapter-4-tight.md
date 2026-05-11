# Chương 4. CÀI ĐẶT VÀ THỰC NGHIỆM

---

Chương này mô tả ngắn gọn quá trình cài đặt hệ thống ParkSmart, từ môi trường phát triển cục bộ đến môi trường vận hành công khai trên Internet, kèm theo các kết quả thực nghiệm chính minh chứng tính khả dụng của hệ thống.

## 4.1. Môi trường triển khai

Hệ thống được phát triển trên máy chủ Windows 11 với CPU Intel Core i7, RAM 16 GB, GPU NVIDIA GTX 1650 4 GB và ổ SSD 50 GB; cụm IoT gồm ESP32, Arduino UNO R3, hai servo SG90, OLED SSD1306 và hai camera (DroidCam quét QR, RTSP đọc biển số). Các nền tảng phần mềm chính được tổng hợp tại Bảng 4.1.

_Bảng 4.1: Phần mềm và phiên bản sử dụng_

| Lớp                    | Công cụ                                              | Phiên bản           |
| ---------------------- | ---------------------------------------------------- | ------------------- |
| Hệ điều hành           | Windows 11 + WSL2 Ubuntu                             | 22H2 / 22.04        |
| Container              | Docker Desktop                                       | 4.x                 |
| Backend                | Django + DRF / FastAPI / Go (Gin + Gorilla WS)       | 5.2 / 0.134 / 1.22  |
| Frontend               | React + Vite + Tailwind + shadcn/ui                  | 18.3 / 5.4 / 3.4    |
| Cơ sở dữ liệu / cache  | MySQL / Redis / RabbitMQ / Chroma                    | 8.0 / 7 / 3 / 0.4   |
| AI / ML                | PyTorch + Ultralytics YOLO + TrOCR + Sentence-BERT   | 1.13+cu116 / 8 / —  |
| Mô phỏng 3D            | Unity LTS                                            | 2022.3              |
| Triển khai công khai   | Cloudflare Tunnel (cloudflared)                      | 2024.x              |
| Kiểm thử               | Playwright / pytest                                  | 1.x / 7.x           |

## 4.2. Cài đặt hệ thống

**Backend microservices.** Chín dịch vụ Django, FastAPI và Go được đóng gói thành Docker image và khởi chạy đồng thời bằng `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build`. Sau khi container ở trạng thái healthy, tác giả chạy migration cơ sở dữ liệu và các script seed dữ liệu mẫu để chuẩn bị môi trường kiểm thử. Tổng cộng mười bốn container được vận hành đồng thời, gồm bốn dịch vụ Django, ba dịch vụ FastAPI, hai dịch vụ Go, hai container Celery, một Nginx reverse proxy và ba container hạ tầng MySQL/Redis/RabbitMQ.

**AI Service.** AI Service được cài cục bộ trong môi trường ảo Python (`venv`) thay vì Docker do cần truy cập trực tiếp GPU NVIDIA. Quy trình gồm tạo `venv`, cài thư viện theo `requirements.txt` (PyTorch + cu116, ultralytics, transformers, sentence-transformers, chromadb), sao chép trọng số mô hình vào `ml/models/`, và khởi chạy bằng `python -m uvicorn app.main:app --port 8009`.

**Frontend.** Giao diện người dùng được cài đặt qua `npm ci` và build thành bundle tĩnh bằng `npm run build`. Ba biến môi trường bắt buộc (`VITE_API_URL`, `VITE_WS_URL`, `VITE_GATEWAY_SECRET`) phải có giá trị hợp lệ trước khi build, nếu không quá trình build sẽ thất bại. Bundle `dist/` được phục vụ bởi Nginx ở cổng 80.

**Hệ thống IoT.** ESP32 được nạp firmware qua Arduino IDE với thư viện ESP32 Core, nối với Arduino UNO qua UART 9600 bps; Arduino điều khiển hai servo SG90 bằng PWM 1500–3000 μs. Sau khi nạp xong, ESP32 tự kết nối WiFi, gửi heartbeat về AI Service mỗi mười giây và phản hồi sự kiện nhấn nút bằng cách gọi API check-in/check-out.

**Triển khai công khai.** Hệ thống được công bố lên Internet thông qua Cloudflare Tunnel với bốn tên miền con trỏ về Nginx ở cổng 80. Quy trình gồm ba bước: tạo tunnel bằng `cloudflared tunnel create`, soạn `config.yml` định tuyến các hostname, đăng ký bản ghi DNS bằng `cloudflared tunnel route dns`. Sau khi khởi chạy, người dùng có thể truy cập hệ thống tại địa chỉ <https://parksmart.ghepdoicaulong.shop> với chứng chỉ TLS được Cloudflare cung cấp tự động.

## 4.3. Thực nghiệm và đánh giá

### 4.3.1. Kịch bản kiểm thử đầu cuối

Hệ thống được kiểm thử qua mười kịch bản nghiệp vụ phản ánh đúng vòng đời sử dụng của một bãi giữ xe (Bảng 4.2). Tất cả kịch bản đều thực hiện thành công ở môi trường vận hành công khai.

_Bảng 4.2: Kết quả kiểm thử đầu cuối_

| #   | Kịch bản                                | Kết quả                                                              |
| --- | --------------------------------------- | -------------------------------------------------------------------- |
| 1   | Đăng ký và đăng nhập                    | ✅ Phiên đăng nhập lưu qua cookie                                    |
| 2   | Đặt chỗ online qua wizard 5 bước        | ✅ Tạo booking, sinh QR, slot chuyển sang "reserved"                 |
| 3   | Thanh toán online qua VietQR            | ✅ Booking chuyển sang "confirmed" sau callback                      |
| 4   | Check-in tại cổng bằng QR + AI biển số  | ✅ Mở barrier trong dưới 5 giây                                      |
| 5   | Đỗ xe vào ô đã đặt                      | ✅ Camera AI phát hiện và cập nhật trạng thái "parked"               |
| 6   | Check-out kèm thanh toán tiền mặt       | ✅ AI nhận diện đúng mệnh giá đến khi đủ tiền                        |
| 7   | Trợ lý chatbot trả lời câu hỏi FAQ      | ✅ 5/6 (83%) câu hỏi truy xuất đúng tri thức                         |
| 8   | Bản đồ thời gian thực                   | ✅ Hiển thị slot đã đặt và đường đi từ cổng                          |
| 9   | Báo sự cố qua nút Panic                 | ✅ Lưu vào CSDL, gửi thông báo cho quản trị viên                     |
| 10  | Truy cập từ Internet công cộng          | ✅ Phản hồi HTTP/2 200 với chứng chỉ TLS                             |

### 4.3.2. Đánh giá độ chính xác các mô hình AI

**Mô hình nhận diện tiền giấy.** EfficientNetV2-S được huấn luyện 25 epoch trên 15.252 ảnh và đánh giá trên 3.818 ảnh thuộc đầy đủ chín mệnh giá tiền Việt Nam. Mô hình đạt độ chính xác tuyệt đối 100% với precision, recall và F1-score đều bằng 1,00 cho từng mệnh giá (Bảng 4.3).

_Bảng 4.3: Kết quả đánh giá mô hình nhận diện tiền giấy_

| Mệnh giá  | Số ảnh | Precision | Recall | F1-score |
| --------- | ------ | --------- | ------ | -------- |
| 1.000 đ   | 483    | 1,00      | 1,00   | 1,00     |
| 2.000 đ   | 483    | 1,00      | 1,00   | 1,00     |
| 5.000 đ   | 480    | 1,00      | 1,00   | 1,00     |
| 10.000 đ  | 448    | 1,00      | 1,00   | 1,00     |
| 20.000 đ  | 472    | 1,00      | 1,00   | 1,00     |
| 50.000 đ  | 400    | 1,00      | 1,00   | 1,00     |
| 100.000 đ | 471    | 1,00      | 1,00   | 1,00     |
| 200.000 đ | 115    | 1,00      | 1,00   | 1,00     |
| 500.000 đ | 466    | 1,00      | 1,00   | 1,00     |
| **Tổng**  | **3.818** | **1,00** | **1,00** | **1,00** |

**Pipeline nhận diện biển số xe.** YOLOv8 phát hiện vùng biển số kết hợp TrOCR đọc ký tự (dự phòng EasyOCR và Tesseract) đạt độ chính xác xấp xỉ 92–95% trên biển số rõ ràng và giảm còn dưới 80% với điều kiện ánh sáng kém. Cơ chế đối sánh mờ với sai lệch tối đa ba ký tự nâng tỉ lệ chấp nhận thực tế lên khoảng 97%.

**Mô hình phát hiện ô đỗ.** YOLO11n kết hợp đối sánh IoU ≥ 0,15 chạy ổn định ở tốc độ 5 khung hình/giây, đủ cập nhật 158 ô đỗ thời gian gần thực.

**Trợ lý chatbot RAG.** Cơ sở tri thức 93 đoạn từ 15 tài liệu nội bộ giúp chatbot trả lời đúng 5/6 (83,3%) câu hỏi mẫu trong bộ kiểm thử đầu cuối; câu hỏi nằm ngoài phạm vi tri thức được hệ thống định tuyến sang intent khác — phù hợp với thiết kế.

### 4.3.3. Đánh giá hiệu năng

Trên môi trường thử nghiệm, các tác vụ chính của hệ thống cho độ trễ phù hợp với trải nghiệm tương tác. Tải trang chủ và bảng điều khiển hoàn tất trong dưới 1,5 giây. Một thao tác đặt chỗ hoàn chỉnh mất khoảng 0,8–1,2 giây. Cập nhật trạng thái ô đỗ qua WebSocket được phát đến mọi trình duyệt đang theo dõi cùng vùng đỗ trong 50–150 mili giây. Suy luận pipeline biển số (YOLO + TrOCR) khoảng 250–400 mili giây trên GPU; phân loại tiền giấy với Test-Time Augmentation năm bước khoảng 80–120 mili giây. Trợ lý chatbot có độ trễ 1–3 giây do gọi API Gemini bên ngoài. Đường hầm Cloudflare hoạt động ổn định nhiều giờ liên tục với bốn kết nối song song tới datacenter HKG.

Bên cạnh kiểm thử tự động bằng Playwright trên hơn mười kịch bản, một nhóm người dùng thử (gồm bạn học và người thân) đã trực tiếp sử dụng hệ thống và cho phản hồi tích cực về giao diện hiện đại, quy trình đặt chỗ rõ ràng, mã QR thuận tiện cho check-in tại cổng và chatbot phản hồi tự nhiên bằng tiếng Việt. Các góp ý cải tiến — gồm thời gian phản hồi của chatbot, hỗ trợ tiếng Anh và ứng dụng di động gốc — đã được ghi nhận và đưa vào định hướng phát triển trình bày tại chương kết.
