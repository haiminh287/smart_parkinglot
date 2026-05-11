## 3.4. Kiến trúc hệ thống

### 3.4.1. Kiến trúc Microservices

Hệ thống ParkSmart áp dụng **kiến trúc Microservices** — toàn bộ chức năng nghiệp vụ được tách thành **10 dịch vụ độc lập**, mỗi dịch vụ phụ trách một miền (domain) riêng, sở hữu cơ sở dữ liệu/cache riêng và có thể được phát triển, kiểm thử, triển khai một cách độc lập với các dịch vụ còn lại. Mọi yêu cầu từ phía client (React SPA, Unity Digital Twin, ESP32 IoT) đều đi qua một điểm vào duy nhất là **API Gateway**, đóng vai trò xác thực phiên đăng nhập, kiểm soát truy cập, giới hạn tần suất và định tuyến request đến đúng dịch vụ đích. Mô hình này đảm bảo tính phân tách trách nhiệm, khả năng mở rộng độc lập từng dịch vụ và cô lập lỗi giữa các thành phần.

**Phân nhóm 10 microservices theo công nghệ và miền nghiệp vụ:**

_Bảng 3.1: Phân nhóm 10 microservices của hệ thống ParkSmart_

| Nhóm                               | Dịch vụ                          | Cổng       | Vai trò chính                                                                                  |
| ---------------------------------- | -------------------------------- | ---------- | ---------------------------------------------------------------------------------------------- |
| **Lớp Edge / Cổng vào**            | gateway-service-go               | 8000       | Xác thực phiên, định tuyến, rate limiting, CORS, kiểm soát truy cập                            |
|                                    | realtime-service-go              | 8006       | Hub WebSocket, phát sự kiện thời gian thực tới các trình duyệt và Unity                        |
| **Django REST Framework (CRUD)**   | auth-service                     | 8001       | Đăng ký, đăng nhập, OAuth, quản lý người dùng                                                  |
|                                    | booking-service                  | 8002       | Đặt chỗ, sinh QR, huỷ booking, kiểm tra hết hạn (Celery worker + beat)                         |
|                                    | parking-service                  | 8003       | Quản lý bãi xe, tầng, vùng đỗ, ô đỗ, cấu hình camera                                            |
|                                    | vehicle-service                  | nội bộ     | Quản lý phương tiện của người dùng                                                              |
| **FastAPI (xử lý bất đồng bộ/AI)** | ai-service-fastapi               | 8009       | Nhận diện biển số xe, phát hiện ô đỗ, nhận diện tiền giấy, xử lý sự kiện ESP32                |
|                                    | chatbot-service-fastapi          | 8008       | Trò chuyện đa lượt, đặt chỗ qua hội thoại, RAG cho câu hỏi chính sách                          |
|                                    | payment-service-fastapi          | 8007       | Tạo phiên thanh toán, theo dõi trạng thái, tích luỹ tiền mặt tại cổng                          |
|                                    | notification-service-fastapi     | 8005       | Gửi thông báo đẩy, email, tiêu thụ sự kiện từ hàng đợi                                         |

**Hạ tầng dùng chung:** MySQL 8.0 lưu dữ liệu nghiệp vụ chính, Redis 7 đảm nhiệm vai trò cache + lưu phiên đăng nhập + queue cho Celery + pub/sub cho realtime, RabbitMQ làm message broker cho các sự kiện nghiệp vụ giữa các dịch vụ, và Chroma vector store lưu các embedding phục vụ tính năng RAG của chatbot.

**Vai trò của API Gateway:**

API Gateway là điểm vào duy nhất của toàn hệ thống, đảm nhận sáu nhóm trách nhiệm chính. Thứ nhất, gateway quản lý xác thực phiên đăng nhập bằng cookie session; mỗi request được kiểm tra với Redis để lấy thông tin người dùng tương ứng. Thứ hai, gateway thực hiện chèn các header định danh nội bộ trước khi chuyển tiếp request đến dịch vụ đích, giúp các dịch vụ phía sau biết được người dùng nào đang gọi mà không phải tự xác thực lại. Thứ ba, gateway sử dụng một khoá bí mật chung giữa các dịch vụ để chỉ chấp nhận request đến từ chính nó, bảo vệ các dịch vụ phía sau khỏi truy cập trực tiếp từ bên ngoài. Thứ tư, gateway giới hạn số request mỗi phút theo địa chỉ IP nhằm chống lạm dụng. Thứ năm, gateway xử lý chính sách CORS để cho phép React SPA trên domain công khai gọi API. Cuối cùng, gateway thực hiện vai trò reverse proxy — định tuyến request đến đúng dịch vụ đích dựa trên tiền tố URL.

_Bảng 3.2: Bảng định tuyến của API Gateway_

| Tiền tố URL        | Dịch vụ đích                 | Ghi chú                                                              |
| ------------------ | ---------------------------- | -------------------------------------------------------------------- |
| `/auth/*`          | auth-service                 | Cho phép truy cập công khai cho đăng ký/đăng nhập                    |
| `/bookings/*`      | booking-service              | Yêu cầu phiên đăng nhập hợp lệ                                       |
| `/parking/*`       | parking-service              | Một số endpoint công khai (danh sách bãi)                             |
| `/vehicles/*`      | vehicle-service              | Yêu cầu phiên đăng nhập hợp lệ                                       |
| `/ai/*`            | ai-service-fastapi           | ESP32 dùng device token riêng                                         |
| `/chatbot/*`       | chatbot-service-fastapi      | Yêu cầu phiên đăng nhập hợp lệ                                       |
| `/payments/*`      | payment-service-fastapi      | Yêu cầu phiên đăng nhập hợp lệ                                       |
| `/notifications/*` | notification-service-fastapi | Yêu cầu phiên đăng nhập hợp lệ                                       |
| `/ws/*`            | realtime-service-go          | Nâng cấp kết nối WebSocket                                           |
| `/health/*`        | gateway-service-go           | Kiểm tra sức khoẻ, không yêu cầu xác thực                           |

### 3.4.2. Các kiểu giao tiếp giữa các dịch vụ

Trong kiến trúc microservices của ParkSmart, các dịch vụ giao tiếp với nhau theo **ba kiểu chính** tuỳ theo đặc tính nghiệp vụ.

**Kiểu 1 — Giao tiếp đồng bộ qua HTTP REST.** Đây là kiểu giao tiếp phổ biến nhất, được sử dụng cho mọi tương tác giữa client và server cũng như giữa các dịch vụ backend với nhau. Client gọi vào API Gateway; gateway xác thực phiên rồi chuyển tiếp request đến dịch vụ đích kèm theo các header định danh nội bộ. Mỗi dịch vụ backend cũng có thể chủ động gọi sang dịch vụ khác (ví dụ booking-service gọi vehicle-service để xác minh xe của người dùng) qua chính API Gateway hoặc qua tên DNS nội bộ trong cùng mạng container. Mọi request nội bộ đều mang khoá bí mật chung để dịch vụ đích biết request đó đến từ một dịch vụ hợp lệ.

**Kiểu 2 — Giao tiếp bất đồng bộ qua hàng đợi sự kiện (RabbitMQ).** Kiểu này được dùng cho các tác vụ không đòi hỏi phản hồi tức thì và cần được tách rời khỏi luồng request chính, giúp giảm thời gian phản hồi cho người dùng và tránh phụ thuộc cứng giữa các dịch vụ. Khi một sự kiện nghiệp vụ xảy ra (đặt chỗ thành công, thanh toán hoàn tất, sự cố được báo, ô đỗ thay đổi trạng thái), dịch vụ phát sự kiện sẽ đẩy thông điệp lên RabbitMQ; các dịch vụ khác đăng ký lắng nghe sẽ xử lý theo phần việc của mình một cách độc lập. Ví dụ, sau khi booking-service tạo booking thành công, dịch vụ này phát sự kiện "booking_created"; notification-service tiêu thụ sự kiện để gửi email và thông báo đẩy, đồng thời realtime-service broadcast cập nhật trạng thái ô đỗ tới mọi trình duyệt đang xem.

**Kiểu 3 — Đẩy thời gian thực qua WebSocket.** Kiểu này phục vụ các trường hợp client cần được cập nhật ngay khi có thay đổi mà không phải hỏi lại liên tục. Realtime Service duy trì các kết nối WebSocket bền vững với React SPA và Unity Digital Twin; khi nhận được sự kiện từ Redis Pub/Sub hoặc RabbitMQ, dịch vụ này sẽ phát thông điệp đến đúng nhóm client đang quan tâm (ví dụ: chỉ những người dùng đang xem cùng một vùng đỗ mới nhận được cập nhật trạng thái ô đỗ trong vùng đó).

### 3.4.3. Luồng xử lý dữ liệu tổng quát

Hệ thống ParkSmart có **ba luồng dữ liệu chính** ứng với ba loại client khác nhau.

**Luồng 1 — Người dùng web/mobile thao tác qua React SPA.** Người dùng tương tác với giao diện web; trình duyệt gửi request kèm cookie phiên đăng nhập về API Gateway. Gateway tra cứu Redis để xác thực phiên, sau đó chèn các header định danh nội bộ và chuyển tiếp request đến dịch vụ Django/FastAPI tương ứng. Dịch vụ thực thi nghiệp vụ, đọc/ghi dữ liệu vào MySQL hoặc cache trên Redis nếu cần, rồi trả kết quả về dạng JSON. Gateway gửi response về trình duyệt và hệ thống cập nhật giao diện cho người dùng.

**Luồng 2 — Thiết bị IoT ESP32 tại cổng vào/ra phối hợp với AI Service.** Khi có xe đến cổng, ESP32 gửi yêu cầu check-in/check-out lên AI Service kèm theo device token và khoá bí mật nội bộ. AI Service kích hoạt camera quét QR, giải mã ra mã booking, sau đó tra cứu booking-service để lấy thông tin chi tiết. Tiếp đó, AI Service kích hoạt camera biển số để chụp xe, dùng các mô hình thị giác máy tính để nhận diện biển số và đối chiếu với booking. Nếu hợp lệ, AI Service gọi booking-service cập nhật trạng thái sang đã check-in, gọi parking-service đánh dấu ô đỗ đã được sử dụng, rồi gửi tín hiệu cho ESP32. ESP32 nhận tín hiệu sẽ điều khiển Arduino qua giao thức UART để mở barrier và hiển thị biển số nhận được trên màn hình OLED tại cổng. Sau ít giây barrier tự động đóng để tránh nhiều xe lọt vào cùng lúc.

**Luồng 3 — Cập nhật thời gian thực tới các trình duyệt đang xem.** Khi một dịch vụ backend thay đổi dữ liệu có ảnh hưởng đến trải nghiệm thời gian thực (ô đỗ chuyển trạng thái, booking thay đổi, sự cố được tạo), dịch vụ này phát sự kiện lên kênh Pub/Sub của Redis hoặc lên RabbitMQ. Realtime Service đăng ký lắng nghe các kênh này; khi nhận được sự kiện, dịch vụ phát thông điệp đến tất cả các kết nối WebSocket có liên quan. Phía React SPA nhận sự kiện, cập nhật kho dữ liệu nội bộ và làm mới các thành phần giao diện đang hiển thị (ví dụ đổi màu ô đỗ trên bản đồ) mà không cần tải lại trang.

### 3.4.4. Ưu điểm kiến trúc

Kiến trúc microservices của ParkSmart mang lại nhiều lợi ích thiết thực, nổi bật nhất là **khả năng mở rộng từng thành phần độc lập**. Mỗi dịch vụ chạy trong một container riêng và có thể được nhân bản theo nhu cầu thực tế; điển hình là booking-service được tách thành nhiều container xử lý bất đồng bộ qua Celery, trong khi AI service có thể được cấp phát thêm tài nguyên để xử lý luồng dữ liệu từ nhiều camera mà không ảnh hưởng đến các dịch vụ còn lại. Sự phân tách này đồng thời mang lại lợi thế về **cô lập lỗi**, đảm bảo rằng sự cố tại một dịch vụ phụ (như chatbot tạm dừng) hoàn toàn không làm gián đoạn các luồng nghiệp vụ cốt lõi như đặt chỗ hay check-in.

Kiến trúc này cũng tạo điều kiện để áp dụng chiến lược **đa dạng công nghệ** — sử dụng Django DRF cho các tác vụ quản lý dữ liệu CRUD nhờ thế mạnh về ORM và admin tích hợp, FastAPI để xử lý tối ưu các luồng I/O bất đồng bộ trong AI và chatbot, Go cho lớp Gateway và Realtime nhằm tiếp nhận hàng nghìn kết nối đồng thời với độ trễ cực thấp. Sự linh hoạt trong lựa chọn công nghệ kết hợp với các giao thức giao tiếp chuẩn hoá đã thúc đẩy **khả năng phát triển độc lập**, cho phép song song hoá các khâu lập trình, kiểm thử và triển khai trên từng dịch vụ. Cuối cùng, việc kết hợp đồng thời ba kiểu giao tiếp (đồng bộ qua HTTP, bất đồng bộ qua RabbitMQ, thời gian thực qua WebSocket) giúp hệ thống vừa đảm bảo phản hồi nhanh khi cần, vừa giảm phụ thuộc cứng giữa các dịch vụ, mang lại **khả năng phục hồi** tốt hơn so với một hệ thống đơn khối truyền thống.

### 3.4.5. Nhược điểm kiến trúc

Bên cạnh những lợi ích rõ ràng, kiến trúc microservices cũng mang theo nhiều thách thức đáng chú ý, trước tiên là sự gia tăng về **độ phức tạp vận hành**. Việc duy trì và giám sát đồng thời mười dịch vụ cùng các thành phần hạ tầng (MySQL, Redis, RabbitMQ, Chroma) đòi hỏi nguồn tài nguyên hệ thống dồi dào và các công cụ quản lý chuyên biệt so với kiến trúc nguyên khối truyền thống. Khó khăn tiếp theo là **độ trễ mạng giữa các dịch vụ**: một yêu cầu nghiệp vụ phức tạp đôi khi đòi hỏi nhiều lệnh gọi bắc cầu qua API Gateway và chuỗi dịch vụ nội bộ, làm tăng tổng thời gian phản hồi; vấn đề này hiện đang được kiểm soát thông qua bộ nhớ đệm Redis và các kỹ thuật phi chuẩn hoá dữ liệu (denormalization) hợp lý.

Hệ thống cũng phải đối mặt với bài toán **nhất quán dữ liệu**: khi mỗi dịch vụ sở hữu phạm vi dữ liệu riêng và giao tiếp bất đồng bộ qua hàng đợi sự kiện, hệ thống buộc phải chấp nhận mô hình nhất quán cuối cùng, dẫn đến nguy cơ dữ liệu không đồng bộ tạm thời tại các điểm giao cắt giữa dịch vụ và đòi hỏi các cơ chế bù trừ nếu một bước xử lý thất bại. Cuối cùng, quá trình **kiểm lỗi và theo vết** trở nên khó hơn khi nhật ký bị phân tán trên nhiều container; mặc dù hệ thống đang sử dụng định danh request truyền theo header để đối chiếu các luồng thực thi, một giải pháp theo vết phân tán chuyên sâu vẫn cần thiết khi quy mô triển khai mở rộng.
