# Chương 4. CÀI ĐẶT VÀ THỰC NGHIỆM

---

Chương này trình bày quá trình cài đặt thực tế hệ thống ParkSmart từ môi trường phát triển cho đến môi trường vận hành công khai trên Internet, đồng thời mô tả các kịch bản thực nghiệm đã thực hiện và kết quả đánh giá thu được. Khác với Chương 3 tập trung vào phân tích và thiết kế ở mức khái niệm, Chương 4 đi vào chi tiết các bước triển khai cụ thể của từng thành phần và minh chứng tính khả dụng của hệ thống thông qua các phép kiểm thử đầu cuối.

## 4.1. Môi trường triển khai

### 4.1.1. Cấu hình phần cứng

Hệ thống được cài đặt và kiểm thử trên môi trường gồm hai nhóm thiết bị có vai trò khác nhau. Nhóm thứ nhất là **máy chủ phát triển** đảm nhận vai trò chạy backend, AI service và frontend, có cấu hình: bộ vi xử lý Intel Core i7 (hoặc tương đương), bộ nhớ RAM 16 GB, ổ cứng SSD dung lượng tối thiểu 50 GB cho mã nguồn và dữ liệu huấn luyện, kèm card đồ họa NVIDIA GTX 1650 4 GB phục vụ huấn luyện và suy luận các mô hình thị giác máy tính. Nhóm thứ hai là **cụm thiết bị IoT vật lý** đặt tại cổng bãi xe, gồm vi điều khiển ESP32-WROOM-32 làm gateway điều khiển, một bo Arduino UNO R3 điều khiển hai servo SG90 (cổng vào và cổng ra), một màn hình OLED SSD1306 độ phân giải 128×64 hiển thị thông tin biển số, hai camera (DroidCam trên điện thoại Android cho luồng quét QR và camera RTSP/HTTP cho luồng đọc biển số), cùng các module phụ trợ như nguồn 5V/2A và bo mạch test breadboard.

### 4.1.2. Cấu hình phần mềm

Toàn bộ hệ thống được phát triển và triển khai trên hệ điều hành Windows 11 Home Single Language với các nền tảng phần mềm chính được tổng hợp tại Bảng 4.1.

_Bảng 4.1: Tổng hợp phần mềm và phiên bản sử dụng trong dự án_

| Lớp                           | Công cụ / Khung làm việc       | Phiên bản              |
| ----------------------------- | ------------------------------ | ---------------------- |
| **Hệ điều hành**              | Windows 11 + WSL2 (Ubuntu)     | 22H2 / Ubuntu 22.04    |
| **Container runtime**         | Docker Desktop                 | 4.x                    |
| **Ngôn ngữ lập trình**        | Python                         | 3.10 và 3.11           |
|                               | Go                             | 1.22                   |
|                               | TypeScript / JavaScript        | TypeScript 5.8         |
|                               | C# (Unity)                     | .NET Standard 2.1      |
| **Khung làm việc backend**    | Django + Django REST Framework | 5.2 + 3.15             |
|                               | FastAPI + Uvicorn              | 0.134                  |
|                               | Gin + Gorilla WebSocket        | 1.10 + 1.5             |
| **Khung làm việc frontend**   | React + Vite                   | 18.3 + 5.4             |
|                               | Tailwind CSS + shadcn/ui       | 3.4 + 51 components    |
| **Cơ sở dữ liệu / cache**     | MySQL                          | 8.0                    |
|                               | Redis                          | 7                      |
|                               | RabbitMQ                       | 3                      |
|                               | Chroma vector store            | 0.4.22                 |
| **Khung trí tuệ nhân tạo**    | PyTorch + torchvision          | 1.13 + cu116           |
|                               | Ultralytics YOLO               | 8                      |
|                               | TrOCR (HuggingFace)            | base-printed           |
|                               | sentence-transformers          | 2.7                    |
| **Mô phỏng 3D**               | Unity LTS                      | 2022.3                 |
| **Phần cứng IoT**             | Arduino IDE                    | 2.x                    |
|                               | ESP-IDF / Arduino Core ESP32   | 2.x                    |
| **Triển khai công khai**      | Cloudflare Tunnel (cloudflared) | 2024.x                |
| **Kiểm thử**                  | Playwright                     | 1.x                    |
|                               | pytest                         | 7.x                    |

## 4.2. Cài đặt và cấu hình hệ thống

### 4.2.1. Cài đặt cụm dịch vụ backend bằng Docker Compose

Cụm chín microservices Django, FastAPI và Go được đóng gói thành các Docker image riêng biệt và quản lý bằng `docker compose`. Quy trình cài đặt diễn ra theo các bước sau. Trước hết, tác giả chuẩn bị tệp biến môi trường `.env` ở thư mục gốc backend, chứa thông tin xác thực cơ sở dữ liệu, khoá bí mật giao tiếp giữa các dịch vụ và khoá truy cập các dịch vụ AI bên ngoài. Tệp này không được đẩy lên kho mã nguồn và được thay bằng tệp mẫu `.env.example` cho người triển khai khác. Tiếp theo, lệnh `docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build` được thực thi để khởi tạo toàn bộ stack: Docker tự động kéo (pull) các image gốc của MySQL, Redis, RabbitMQ và Nginx từ Docker Hub, đồng thời build các image dịch vụ tự phát triển từ Dockerfile của từng dịch vụ. Khi các container đã ở trạng thái `healthy`, hệ thống tiến hành chạy các lệnh `python manage.py migrate` cho từng dịch vụ Django để áp dụng migration cơ sở dữ liệu, và chạy các script seed dữ liệu mẫu (`seed_e2e_data.py`, `seed_unity_test_data.py`, `seed_admin_test_data.py`) phục vụ kiểm thử và mô phỏng.

Cấu hình Docker Compose được chia thành hai tệp riêng để phân tách trách nhiệm: `docker-compose.yml` chứa định nghĩa chung dùng được cho cả phát triển và sản xuất, còn `docker-compose.prod.yml` chỉ chứa các thiết lập đặc thù cho môi trường vận hành (Nginx, ENV=production, cookie bảo mật). Tổng cộng có mười bốn container được khởi động trong môi trường vận hành: bốn dịch vụ Django (auth, booking, parking, vehicle), ba dịch vụ FastAPI (chatbot, payment, notification), hai dịch vụ Go (gateway, realtime), hai container Celery cho booking-service (worker và beat), một container Nginx làm reverse proxy ở cổng 80, cùng ba container hạ tầng MySQL, Redis và RabbitMQ. Container `ai-service-fastapi` được loại trừ khỏi Docker stack này vì lý do trình bày tại Mục 4.2.2.

### 4.2.2. Cài đặt AI Service trên môi trường cục bộ

Khác với các dịch vụ khác, AI Service được triển khai trực tiếp trên máy chủ phát triển bằng môi trường ảo Python (`venv`) thay vì chạy trong Docker container. Quyết định này xuất phát từ hai lý do thực tế: thứ nhất, các thư viện học sâu (PyTorch, ultralytics, transformers) cần truy cập trực tiếp tới GPU NVIDIA qua driver CUDA của hệ điều hành chủ — việc chạy trong Docker đòi hỏi cấu hình GPU passthrough phức tạp và không ổn định trên Windows; thứ hai, các bộ trọng số mô hình AI (banknote, plate OCR, slot detection) có dung lượng lớn nên không tiện đóng gói trong Docker image.

Quy trình cài đặt AI Service gồm các bước: tạo môi trường ảo Python 3.10 bằng lệnh `python -m venv venv`, cài đặt các thư viện phụ thuộc qua `pip install -r requirements.txt` (PyTorch 1.13.1+cu116, ultralytics 8.x, transformers, easyocr, pytesseract, opencv-python, fastapi, uvicorn, sentence-transformers, chromadb), sao chép các tệp trọng số mô hình vào thư mục `ml/models/` (chủ yếu là `banknote_effv2s.pth` 82 MB cho mô hình nhận diện tiền giấy và `yolo11n.pt` cho mô hình phát hiện ô đỗ), thiết lập biến môi trường nội bộ trỏ tới các dịch vụ chạy trong Docker (`DB_HOST=127.0.0.1`, `DB_PORT=3307`, `REDIS_HOST=127.0.0.1`, `RABBITMQ_HOST=127.0.0.1`), cuối cùng khởi chạy bằng lệnh `python -m uvicorn app.main:app --host 0.0.0.0 --port 8009`. Khi khởi động, AI Service tự động làm nóng (pre-warm) các mô hình trong vòng đời `lifespan()` để giảm độ trễ cho lần gọi đầu tiên.

### 4.2.3. Cài đặt và build giao diện người dùng

Phía giao diện người dùng được phát triển bằng React 18 với công cụ build Vite. Quy trình cài đặt rất đơn giản: chạy `npm ci` để cài đặt chính xác các thư viện theo `package-lock.json`, sao chép tệp `.env.example` thành `.env` rồi điền các giá trị `VITE_API_URL`, `VITE_WS_URL`, và `VITE_GATEWAY_SECRET`. Cho môi trường phát triển, lệnh `npm run dev` khởi chạy Vite dev server tại cổng 8080 với cơ chế reload nóng (hot module replacement). Cho môi trường vận hành, lệnh `npm run build` được dùng để tạo bundle tĩnh tại thư mục `dist/`, sau đó Nginx phục vụ thư mục này như một ứng dụng đơn trang (single-page application).

Cấu hình quan trọng là biến môi trường `VITE_GATEWAY_SECRET` — khoá này được build vào bundle để frontend có thể gọi API qua Gateway, và quá trình build sẽ thất bại nếu thiếu biến này nhằm tránh trường hợp đẩy ra môi trường vận hành thiếu cấu hình. Toàn bộ giao diện được kiểm thử end-to-end bằng Playwright với tệp cấu hình `playwright.config.ts` chỉ định baseURL và các trình duyệt mục tiêu.

### 4.2.4. Lắp đặt và lập trình hệ thống IoT

Phần IoT được lắp ráp theo sơ đồ chi tiết tại Phụ lục C, bao gồm việc kết nối ESP32 với Arduino qua giao thức UART (chân TX của ESP32 nối với chân RX của Arduino và ngược lại, tốc độ 9600bps), kết nối hai servo SG90 với Arduino tại các chân điều khiển PWM, kết nối màn hình OLED SSD1306 với ESP32 qua bus I2C tại chân SDA và SCL, cùng hai nút nhấn nối với chân GPIO của ESP32 cho thao tác check-in và check-out. Phần lập trình firmware cho ESP32 được thực hiện trên Arduino IDE 2.x với thư viện ESP32 Core, sử dụng các thư viện hỗ trợ HTTPClient, ArduinoJson và Adafruit_SSD1306; firmware cho Arduino đơn giản hơn, chủ yếu nhận lệnh UART và điều khiển servo theo PWM 1500–3000μs.

ESP32 sau khi nạp firmware sẽ tự động kết nối WiFi theo SSID/mật khẩu đã cấu hình trong code, gửi tín hiệu heartbeat về AI Service mỗi mười giây, và phản hồi các sự kiện nhấn nút bằng cách gọi HTTP POST đến endpoint check-in/check-out của AI Service kèm theo device token và khoá bí mật nội bộ.

### 4.2.5. Triển khai công khai qua Cloudflare Tunnel

Để hệ thống có thể tiếp cận từ Internet công cộng phục vụ kiểm thử và bảo vệ luận văn, tác giả triển khai một đường hầm Cloudflare Tunnel kết nối từ máy chủ phát triển (chạy phía sau NAT của mạng nội bộ) đến hạ tầng Cloudflare. Quy trình diễn ra theo các bước sau: cài đặt công cụ `cloudflared` từ kho chính thức của Cloudflare, đăng nhập tài khoản Cloudflare bằng lệnh `cloudflared tunnel login`, tạo một đường hầm có tên định danh và nhận về tệp credential lưu tại `~/.cloudflared/<tunnel-id>.json`, soạn tệp cấu hình `infra/cloudflare/cloudflared/config.yml` định nghĩa các quy tắc định tuyến cho bốn tên miền con (`parksmart.ghepdoicaulong.shop`, `app.ghepdoicaulong.shop`, `api.ghepdoicaulong.shop`, `ws.ghepdoicaulong.shop`) tất cả trỏ về Nginx tại cổng 80, đăng ký bản ghi DNS bằng lệnh `cloudflared tunnel route dns <tunnel-id> <hostname>`, cuối cùng khởi chạy đường hầm với `cloudflared tunnel --config config.yml run`.

Sau khi đường hầm đã đăng ký kết nối thành công với bốn datacenter Cloudflare ở khu vực châu Á (HKG), người dùng từ bất kỳ đâu trên Internet có thể truy cập hệ thống tại địa chỉ <https://parksmart.ghepdoicaulong.shop> mà không cần mở cổng public IP của máy chủ phát triển. Cloudflare cũng tự động cung cấp chứng chỉ TLS (HTTPS) và tường lửa cấp cạnh (edge firewall) miễn phí cho đường hầm này.

## 4.3. Thực nghiệm và đánh giá

### 4.3.1. Kịch bản kiểm thử đầu cuối

Hệ thống được kiểm thử qua các kịch bản nghiệp vụ phản ánh đúng vòng đời sử dụng thực tế của một bãi giữ xe, được trình bày tóm tắt tại Bảng 4.2.

_Bảng 4.2: Các kịch bản kiểm thử đầu cuối đã thực hiện_

| #   | Kịch bản                              | Phương thức kiểm thử                                | Kết quả                                                                                |
| --- | ------------------------------------- | --------------------------------------------------- | -------------------------------------------------------------------------------------- |
| 1   | Đăng ký tài khoản và đăng nhập        | Playwright tự động hoá trên trình duyệt Chromium    | ✅ Tạo và đăng nhập thành công, lưu phiên qua cookie                                   |
| 2   | Đặt chỗ online qua wizard 5 bước      | Người dùng thật + Playwright kịch bản đặt chỗ      | ✅ Tạo booking, sinh QR, cập nhật slot trạng thái `reserved` qua WebSocket             |
| 3   | Thanh toán online bằng VietQR         | Quy trình thủ công + giả lập callback ngân hàng     | ✅ Booking chuyển sang `confirmed`, polling phát hiện trạng thái thay đổi              |
| 4   | Check-in tại cổng bằng QR + AI biển số | Mô phỏng trên Unity Digital Twin và phần cứng thật | ✅ Quét QR → AI nhận diện biển số → mở barrier trong dưới 5 giây                        |
| 5   | Đỗ xe vào ô đã đặt                    | Mô phỏng Unity gửi frame đến AI Service            | ✅ Camera AI phát hiện xe chiếm slot, tự cập nhật trạng thái `parked`                   |
| 6   | Check-out kèm thanh toán tiền mặt     | Mô phỏng đưa tiền mặt trước camera                  | ✅ AI nhận diện đúng mệnh giá, tích luỹ đến đủ tiền, mở barrier ra                      |
| 7   | Trợ lý chatbot trả lời câu hỏi FAQ    | Script `test_chatbot_rag.sh` với 6 câu hỏi mẫu      | ✅ 5/6 câu hỏi (83%) trả lời đúng nhờ truy xuất tri thức RAG                            |
| 8   | Bản đồ thời gian thực                 | Truy cập trang Map sau khi check-in                 | ✅ Hiển thị sơ đồ tầng, vị trí slot đã đặt, đường đi từ cổng tới slot kèm hoạt cảnh    |
| 9   | Báo sự cố qua nút Panic               | Người dùng nhấn báo sự cố, kèm geolocation         | ✅ Sự cố lưu vào cơ sở dữ liệu, gửi thông báo cho quản trị viên qua RabbitMQ          |
| 10  | Truy cập từ Internet công cộng        | Kết nối tới `https://parksmart.ghepdoicaulong.shop` | ✅ Phản hồi HTTP/2 200 với chứng chỉ TLS hợp lệ qua Cloudflare Tunnel                  |

### 4.3.2. Đánh giá độ chính xác của các mô hình AI

**Mô hình nhận diện tiền giấy (banknote classifier).** Mô hình EfficientNetV2-S được huấn luyện 25 epoch trên tập dữ liệu 15.252 ảnh huấn luyện và đánh giá trên 3.818 ảnh kiểm thử thuộc đầy đủ chín mệnh giá tiền Việt Nam (1.000 đ → 500.000 đ). Kết quả đánh giá tổng kết tại Bảng 4.3 cho thấy mô hình đạt độ chính xác tổng thể 100%, với chỉ số precision, recall và F1-score đều bằng 1,00 cho từng mệnh giá. Đặc biệt, mô hình đã giải quyết được vấn đề bỏ sót lớp 200.000 đồng tồn tại ở phiên bản cũ (ResNet50 v1) — phiên bản mới hỗ trợ đầy đủ chín mệnh giá với cùng độ chính xác. Phân tích ngưỡng chấp nhận (precision-at-accept) cho thấy ở mức độ tin cậy ≥ 0,85 và biên (margin) ≥ 0,25, hệ thống vẫn duy trì 100% accept rate và 100% precision — hoàn toàn phù hợp cho kịch bản thanh toán đòi hỏi chính xác cao.

_Bảng 4.3: Kết quả đánh giá mô hình nhận diện tiền giấy EfficientNetV2-S_

| Mệnh giá  | Số ảnh kiểm thử | Precision | Recall | F1-score |
| --------- | --------------- | --------- | ------ | -------- |
| 1.000 đ   | 483             | 1,00      | 1,00   | 1,00     |
| 2.000 đ   | 483             | 1,00      | 1,00   | 1,00     |
| 5.000 đ   | 480             | 1,00      | 1,00   | 1,00     |
| 10.000 đ  | 448             | 1,00      | 1,00   | 1,00     |
| 20.000 đ  | 472             | 1,00      | 1,00   | 1,00     |
| 50.000 đ  | 400             | 1,00      | 1,00   | 1,00     |
| 100.000 đ | 471             | 1,00      | 1,00   | 1,00     |
| 200.000 đ | 115             | 1,00      | 1,00   | 1,00     |
| 500.000 đ | 466             | 1,00      | 1,00   | 1,00     |
| **Tổng**  | **3.818**       | **1,00**  | **1,00** | **1,00** |

**Pipeline nhận diện biển số xe.** Pipeline kết hợp YOLOv8 cho phát hiện vùng biển số và TrOCR (cùng hai phương án dự phòng EasyOCR và Tesseract) cho việc đọc ký tự. Trên tập biển số xe Việt Nam được chụp tại điều kiện ánh sáng khác nhau, pipeline đạt độ chính xác cao với các biển số rõ ràng (xấp xỉ 92–95%) và giảm xuống dưới 80% với các biển số mờ, bị che hoặc ánh sáng kém. Cơ chế đối sánh mờ (fuzzy matching) cho phép sai lệch tối đa ba ký tự so với biển số trong booking, qua đó nâng tỉ lệ chấp nhận thực tế lên 97% trong kịch bản kiểm thử.

**Mô hình phát hiện ô đỗ.** YOLO11n được sử dụng để phát hiện xe trên ảnh tổng quan của bãi xe, kết hợp đối sánh IoU (Intersection over Union ≥ 0,15) với toạ độ ô đỗ đã cấu hình trước. Mô hình chạy ổn định ở tốc độ 5 khung hình mỗi giây, đủ để cập nhật trạng thái 158 ô đỗ trong sơ đồ Unity Digital Twin theo thời gian gần thực.

**Trợ lý hội thoại Chatbot RAG.** Cơ sở tri thức RAG gồm 93 đoạn (chunk) được trích xuất từ 15 tệp Markdown nội bộ về chính sách, quy định, thông tin từng bãi xe và các câu hỏi thường gặp. Bộ kiểm thử đầu cuối với sáu câu hỏi mẫu cho kết quả 5/6 (83,3%) câu được phân loại đúng intent là `faq` và truy xuất đúng đoạn văn nguồn để trả lời, một câu hỏi nằm ngoài phạm vi tri thức (về tiền điện tử) được hệ thống định tuyến sang intent khác — điều này được xem là hành vi chấp nhận được vì câu hỏi không thuộc phạm vi nghiệp vụ của bãi xe.

### 4.3.3. Đánh giá hiệu năng hệ thống

Trong các phép đo trên môi trường thử nghiệm, các tác vụ chính của hệ thống cho thấy độ trễ (latency) hoàn toàn phù hợp với trải nghiệm người dùng tương tác. Việc tải trang chủ và bảng điều khiển cá nhân hoàn tất trong dưới 1,5 giây kể từ khi nhấn liên kết. Một thao tác đặt chỗ hoàn chỉnh từ lúc nhấn nút "xác nhận" đến lúc nhận phản hồi thành công thường nằm trong khoảng 0,8 đến 1,2 giây, bao gồm cả thời gian gateway xác thực phiên, booking-service kiểm tra tính hợp lệ và sinh mã QR. Cập nhật trạng thái ô đỗ qua WebSocket được phát đến tất cả các trình duyệt đang theo dõi cùng vùng đỗ trong khoảng 50–150 mili giây sau khi sự kiện được phát từ backend.

Độ trễ của các tác vụ AI phụ thuộc đáng kể vào việc có sử dụng GPU hay không. Trên máy có GPU GTX 1650, một lần suy luận của pipeline nhận diện biển số đầu cuối (YOLOv8 + TrOCR) mất khoảng 250–400 mili giây, trong khi phân loại tiền giấy bằng EfficientNetV2-S với Test-Time Augmentation năm bước mất khoảng 80–120 mili giây. Trợ lý chatbot có độ trễ cao hơn do phải gọi API Gemini bên ngoài, dao động từ 1 đến 3 giây tuỳ độ phức tạp của câu hỏi.

Quá trình đường hầm Cloudflare hoạt động ổn định trong suốt nhiều giờ kiểm thử mà không xảy ra gián đoạn; bốn kết nối song song tới các datacenter HKG đảm bảo tính sẵn sàng cao và độ trễ thấp cho người truy cập từ Việt Nam.

### 4.3.4. Đánh giá trải nghiệm người dùng

Kiểm thử trải nghiệm được thực hiện theo hai con đường song song. Thứ nhất là kiểm thử tự động bằng Playwright với hơn mười kịch bản đầu cuối, bao trùm các thao tác đăng ký, đăng nhập, đặt chỗ, xem lịch sử, thanh toán, trò chuyện với chatbot và xem bản đồ. Thứ hai là kiểm thử thủ công với một nhóm bạn học và người thân được mời sử dụng hệ thống tại địa chỉ công khai, sau đó cho ý kiến phản hồi qua bảng câu hỏi ngắn. Các phản hồi tích cực đáng chú ý bao gồm: giao diện được đánh giá là hiện đại và thân thiện; quy trình đặt chỗ năm bước được nhận xét là rõ ràng, không gây bối rối; việc nhận được mã QR ngay trong giao diện và có thể quét từ điện thoại để check-in tại cổng được xem là rất tiện lợi; trợ lý chatbot phản hồi tự nhiên bằng tiếng Việt và biết gợi ý các câu hỏi tiếp theo. Một số góp ý cần cải tiến gồm: thời gian phản hồi của chatbot đôi lúc còn dài, cần thêm hỗ trợ ngôn ngữ tiếng Anh cho khách quốc tế, và mong muốn có ứng dụng di động gốc thay vì chỉ giao diện web — những góp ý này đã được ghi nhận và đưa vào định hướng phát triển ở Chương 5.

Tổng hợp lại, các kết quả thực nghiệm đã chứng minh rằng hệ thống ParkSmart không chỉ chạy đúng về mặt chức năng mà còn đạt được mức hiệu năng và trải nghiệm chấp nhận được ở quy mô của một sản phẩm khoá luận tốt nghiệp. Hệ thống đã sẵn sàng làm nền tảng để mở rộng và tối ưu thêm trong các phiên bản tiếp theo theo định hướng được trình bày ở chương kết.
