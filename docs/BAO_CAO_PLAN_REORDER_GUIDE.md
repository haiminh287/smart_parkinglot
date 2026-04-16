# Hướng dẫn tái cấu trúc BAO_CAO_PLAN.md — Chương 2

**Ngày cập nhật:** 2026-04-15 (v2)
**Tác giả:** Nguyễn Hải Minh
**Mục đích:** Tái cấu trúc Chương 2 (Cơ sở lý thuyết) của khóa luận theo hai nguyên tắc đồng thời:
1. **Ưu tiên công nghệ cốt lõi** — đưa các công nghệ tạo nên đóng góp khoa học đặc thù của đề tài lên đầu chương.
2. **Cơ sở lý thuyết thuần túy** — nội dung Chương 2 phải tập trung vào **bản chất công nghệ** (định nghĩa, lịch sử, kiến trúc chung, nguyên lý hoạt động), không lồng ghép quá nhiều chi tiết triển khai cụ thể của ParkSmart. Các phần "áp dụng trong ParkSmart" cần được tách và chuyển sang **Chương 3**.

---

## 1. Triết lý tái cấu trúc

### 1.1. Về thứ tự ưu tiên — "Core and Unique First"

Phiên bản hiện hành của Chương 2 được sắp xếp theo mô hình **bottom-up** (hạ tầng → framework → thành phần bổ trợ). Cách trình bày này phản ánh đúng trình tự xây dựng hệ thống nhưng lại **không làm nổi bật** các điểm mạnh mang tính đặc thù của đề tài. Đối với một khóa luận tốt nghiệp, phần cơ sở lý thuyết nên được tổ chức sao cho người đọc (hội đồng phản biện, giảng viên hướng dẫn) nhận diện ngay được giá trị khoa học và tính mới của công trình. Vì vậy, các công nghệ cốt lõi và tạo khác biệt — kiến trúc Microservices, Trí tuệ nhân tạo, Chatbot LLM, IoT, Digital Twin — được đưa lên đầu; các framework phát triển ứng dụng ở giữa; và hạ tầng hỗ trợ (MySQL, Redis, Docker…) xếp cuối cùng.

### 1.2. Về tính chất nội dung — "Lý thuyết thuần túy, không lồng ghép chi tiết dự án"

Đây là nguyên tắc **quan trọng nhất** đã được bổ sung vào phiên bản v2 của guide. Chương 2 là **cơ sở lý thuyết** — nơi người đọc học về các công nghệ nền tảng được đề tài sử dụng. Nội dung phải trả lời bốn câu hỏi về **công nghệ**, không phải về **dự án**:

1. **Công nghệ đó là gì?** — Định nghĩa chính thức, lịch sử ra đời, tác giả/tổ chức phát triển, phiên bản hiện tại.
2. **Kiến trúc của công nghệ đó như thế nào?** — Các thành phần chính, mô hình vận hành, sơ đồ kiến trúc chung.
3. **Nguyên lý hoạt động ra sao?** — Các thuật toán cốt lõi, luồng xử lý, các khái niệm kỹ thuật nền tảng.
4. **Ưu và nhược điểm vốn có của công nghệ là gì?** — Những đặc tính kỹ thuật làm nên thế mạnh và giới hạn của công nghệ trong khung tham chiếu chung, không riêng đề tài.

Các câu trả lời phải mang tính **phổ quát** — tức là một người đọc Chương 2 mà không cần biết đến ParkSmart vẫn hiểu được công nghệ đó là gì và hoạt động ra sao. Điều này khác biệt với Chương 3 (Hệ thống phát triển), nơi trình bày **cách ParkSmart áp dụng** các công nghệ này vào bài toán cụ thể của mình.

**Hệ quả cụ thể với phiên bản hiện tại:**

- Các tiểu mục dạng "**Các kỹ thuật chính áp dụng trong ParkSmart**" (có trong mọi mục 2.4, 2.5, 2.6, 2.7, 2.8 hiện tại) phải được **cắt ra khỏi Chương 2** và chuyển sang **Chương 3** dưới các mục tương ứng như "3.X.Y. Triển khai [tên dịch vụ] bằng [công nghệ]".
- Các đoạn mở đầu dạng "Trong dự án ParkSmart, [công nghệ X] được sử dụng cho..." phải được thay bằng câu giới thiệu **thuần về công nghệ**, chuyển phần áp dụng dự án về cuối Chương 2 (trong một đoạn ngắn 2–3 câu "tổng hợp vai trò trong đề tài") hoặc loại bỏ hoàn toàn.
- Các **bảng so sánh công nghệ** (DRF vs Flask, Microservices vs Monolithic…) **được giữ lại** trong Chương 2 vì đây là phần biện luận lựa chọn công nghệ thuộc phạm trù cơ sở lý thuyết.
- Các thông số triển khai cụ thể (số hiệu cổng, phiên bản pin trong requirements.txt, tên file cấu hình) phải **bị loại bỏ** khỏi Chương 2 và chỉ xuất hiện trong Chương 3 hoặc Phụ lục.

---

## 2. Cấu trúc mới cho mỗi mục trong Chương 2

Để đảm bảo tính nhất quán và thuần lý thuyết, mỗi mục 2.X trong Chương 2 nên tuân theo cấu trúc sau:

```
## 2.X. [Tên công nghệ]

### 2.X.1. Giới thiệu
- Định nghĩa công nghệ
- Tác giả/tổ chức phát triển, năm ra đời
- Phiên bản chính hiện nay
- Vị trí của công nghệ trong hệ sinh thái phần mềm

### 2.X.2. Kiến trúc và nguyên lý hoạt động
- Các thành phần chính của công nghệ
- Mô hình/sơ đồ kiến trúc chung
- Các khái niệm kỹ thuật nền tảng
- Luồng xử lý tổng quát

### 2.X.3. So sánh với các công nghệ thay thế
- Bảng so sánh với 2-3 phương án thay thế phổ biến
- Các tiêu chí đánh giá (hiệu năng, độ phức tạp, tính năng...)
- 1 đoạn ngắn (3-5 câu) nêu lý do đề tài chọn công nghệ này

### 2.X.4. Ưu và nhược điểm
- Ưu điểm vốn có của công nghệ (phổ quát, không riêng đề tài)
- Nhược điểm và giới hạn kỹ thuật
```

**KHÔNG có tiểu mục "Các kỹ thuật áp dụng trong ParkSmart"** trong Chương 2 — tiểu mục này chuyển sang Chương 3.

---

## 3. Bảng ánh xạ thứ tự mới (Old → New)

| Mới | Tiêu đề mới | Cũ | Lý do ưu tiên |
|---|---|---|---|
| **2.1** | Kiến trúc Microservices và các nguyên tắc thiết kế hệ thống phân tán | 2.1.6 (nâng thành section độc lập) | Kiến trúc tổng thể — nền tảng định hình toàn bộ thiết kế. Đặt đầu để người đọc nắm ngay triết lý hệ thống. |
| **2.2** | Trí tuệ nhân tạo và Thị giác máy tính | 2.2 | Trụ cột khoa học chính của đề tài. Giữ nguyên vị trí cao. |
| **2.3** | Chatbot AI và Mô hình Ngôn ngữ Lớn | 2.8 | Thành phần đặc thù hiếm gặp ở đồ án sinh viên — Transformer, LLM, Gemini, Hexagonal Architecture. Đưa lên cao. |
| **2.4** | Internet of Things | 2.3 | Thành phần phần cứng thực tế. Đi ngay sau AI + Chatbot vì tạo thành bộ ba công nghệ đặc thù. |
| **2.5** | Unity Game Engine và Bộ mô phỏng ba chiều | 2.9 | Chiến lược kiểm thử độc đáo. Đi sau IoT vì thay thế cho thiết bị vật lý trong giai đoạn test. |
| **2.6** | Django REST Framework | 2.4 | Framework backend nghiệp vụ. Mở đầu phần framework phát triển. |
| **2.7** | FastAPI | 2.5 | Framework backend bất đồng bộ và AI inference. |
| **2.8** | Ngôn ngữ Go, Gin Framework và Gorilla WebSocket | 2.6 | Công nghệ cho thành phần hiệu năng cao. |
| **2.9** | ReactJS, TypeScript và Kiến trúc Component-based | 2.7 | Công nghệ cho giao diện người dùng. |
| **2.10** | Hạ tầng và các dịch vụ hỗ trợ (MySQL, Redis, RabbitMQ, Docker, Nginx) | 2.1.1 → 2.1.5 | Hạ tầng vận hành — tiêu chuẩn công nghiệp, không phải đóng góp riêng của đề tài. Đưa xuống cuối. |

---

## 4. Câu mở đầu mới cho Chương 2

Thay thế đoạn mở hiện tại (đã được cập nhật ở dòng 307 của `BAO_CAO_PLAN.md`) bằng đoạn văn sau — đoạn này **đã được apply inline** vào file gốc, được giữ tại đây để tham khảo và kiểm tra:

> Chương này trình bày cơ sở lý thuyết của **mười nhóm công nghệ** được ParkSmart áp dụng, sắp xếp theo **mức độ trọng yếu đối với đóng góp khoa học của đề tài** — ưu tiên trình bày các công nghệ cốt lõi tạo nên sự khác biệt trước, sau đó mới đến các framework phát triển ứng dụng và cuối cùng là hạ tầng hỗ trợ.
>
> Mở đầu là **kiến trúc Microservices** (Mục 2.1) — bộ khung tổng thể định hình toàn bộ cách các dịch vụ trong hệ thống giao tiếp, triển khai và mở rộng độc lập. Tiếp theo, ba trụ cột công nghệ mang tính đặc thù của đề tài được trình bày tuần tự: **Trí tuệ nhân tạo và Thị giác máy tính** (Mục 2.2), **Chatbot AI và Mô hình Ngôn ngữ Lớn** (Mục 2.3) và **Internet of Things** (Mục 2.4). Mục 2.5 giới thiệu **Unity Game Engine** cùng bộ mô phỏng ba chiều phục vụ kiểm thử và trực quan hóa hệ thống.
>
> Các mục 2.6 đến 2.9 trình bày các **framework phát triển ứng dụng**: **Django REST Framework** (Mục 2.6), **FastAPI** (Mục 2.7), **ngôn ngữ Go cùng Gin Framework và Gorilla WebSocket** (Mục 2.8), và **ReactJS kết hợp TypeScript** (Mục 2.9). Kết thúc chương, Mục 2.10 tổng hợp các **dịch vụ hạ tầng và triển khai** bao gồm MySQL, Redis, RabbitMQ, Docker và Nginx.
>
> Mỗi nhóm công nghệ được trình bày thuần theo tính chất **cơ sở lý thuyết**: (1) giới thiệu khái niệm và lịch sử phát triển của công nghệ; (2) kiến trúc hoặc nguyên lý hoạt động ở mức khái niệm; (3) so sánh với các công nghệ thay thế kèm bảng đánh giá; (4) ưu và nhược điểm kỹ thuật vốn có. Các chi tiết về **cách đề tài áp dụng** từng công nghệ cụ thể (cấu hình, phiên bản, tham số, mã nguồn) được trình bày ở Chương 3 — nơi phân tích và thiết kế hệ thống — nhằm tuân thủ nguyên tắc phân tách rõ ràng giữa nền tảng lý thuyết và triển khai thực tiễn.

---

## 5. Nội dung Mục 2.1 — Kiến trúc Microservices (thuần lý thuyết)

Đoạn văn dưới đây là bản **đã rewrite theo nguyên tắc "lý thuyết thuần túy"** — hoàn toàn không có đoạn "trong ParkSmart", không liệt kê 10 microservices cụ thể, không nhắc đến Gateway Go port 8000. Các chi tiết này sẽ xuất hiện ở Chương 3.

### 2.1. Kiến trúc Microservices và các nguyên tắc thiết kế hệ thống phân tán

#### 2.1.1. Giới thiệu kiến trúc Microservices

**Microservices** (kiến trúc vi dịch vụ) là mô hình thiết kế phần mềm trong đó một ứng dụng được phân rã thành tập hợp các **dịch vụ độc lập, nhỏ gọn**, mỗi dịch vụ đảm nhận một chức năng nghiệp vụ cụ thể, chạy trong tiến trình riêng biệt và giao tiếp với nhau qua các giao thức nhẹ như HTTP REST hoặc hàng đợi tin nhắn. Thuật ngữ "Microservices" được sử dụng lần đầu tại các hội nghị kỹ thuật phần mềm năm 2011, và được **Martin Fowler** cùng **James Lewis** chính thức định nghĩa qua bài viết nổi tiếng _"Microservices — a definition of this new architectural term"_ năm 2014 [23]. Mô hình này kế thừa nhiều ý tưởng từ kiến trúc hướng dịch vụ (Service-Oriented Architecture — SOA) của thập niên 2000, nhưng đặt trọng tâm vào **độc lập hóa triển khai** và **tự trị nghiệp vụ** ở mức chi tiết hơn hẳn SOA truyền thống.

Kiến trúc microservices đối lập trực tiếp với mô hình **monolithic** (khối nguyên) — nơi toàn bộ ứng dụng nằm trong một mã nguồn duy nhất, biên dịch thành một đơn vị triển khai duy nhất, chia sẻ chung một connection pool cơ sở dữ liệu, và bất kỳ thay đổi nào dù nhỏ đều yêu cầu triển khai lại toàn bộ hệ thống. Kiến trúc monolithic có ưu điểm đơn giản ở giai đoạn khởi đầu của dự án, nhưng bộc lộ nhiều hạn chế khi quy mô ứng dụng và đội phát triển tăng lên: khả năng cập lệ (coupling) giữa các module trở nên cao, việc kiểm thử riêng lẻ từng phần khó khăn, một lỗi cục bộ có thể kéo theo sự cố của toàn hệ thống, và việc nhiều nhóm phát triển cùng làm việc trên một mã nguồn duy nhất tạo ra xung đột liên tục trong quá trình triển khai.

Microservices được xây dựng để giải quyết các hạn chế trên thông qua việc **phân rã ứng dụng theo miền nghiệp vụ (business domain)** — mỗi dịch vụ tương ứng với một bounded context trong thuật ngữ của Domain-Driven Design, có thể được phát triển, kiểm thử, triển khai và mở rộng độc lập với các dịch vụ khác.

#### 2.1.2. Các nguyên tắc thiết kế cốt lõi

Kiến trúc microservices được xây dựng trên năm nguyên tắc thiết kế nền tảng, được cộng đồng phần mềm đúc kết qua hơn một thập kỷ triển khai thực tế tại các công ty công nghệ lớn như Netflix, Amazon, Uber, và Spotify:

1. **Single Responsibility (Trách nhiệm duy nhất)**: Mỗi dịch vụ chỉ đảm nhận một miền nghiệp vụ được định nghĩa rõ ràng và không can thiệp vào miền của dịch vụ khác. Nguyên tắc này dựa trên khái niệm **bounded context** của Domain-Driven Design — một dịch vụ chỉ hiểu và xử lý các thực thể, quy tắc, và thuật ngữ thuộc phạm vi nghiệp vụ của mình.
2. **Independent Deployment (Triển khai độc lập)**: Nhóm phát triển có thể cập nhật, triển khai, hoặc khôi phục (rollback) một dịch vụ mà không cần can thiệp đến các dịch vụ còn lại. Đây là đặc tính quan trọng nhất phân biệt microservices với SOA truyền thống — nơi các dịch vụ vẫn chia sẻ nhiều cấu hình và thư viện chung, làm cho việc triển khai từng dịch vụ riêng rẽ khó khăn.
3. **Decentralized Data Management (Quản lý dữ liệu phi tập trung)**: Mỗi dịch vụ sở hữu và quản lý tập dữ liệu riêng — không có dịch vụ nào được phép truy cập trực tiếp vào cơ sở dữ liệu của dịch vụ khác. Mọi trao đổi dữ liệu đều phải đi qua giao diện API công khai hoặc các sự kiện bất đồng bộ. Nguyên tắc này đảm bảo tính **cô lập dữ liệu** — schema của một dịch vụ có thể thay đổi mà không làm vỡ các dịch vụ khác.
4. **Failure Isolation (Cô lập lỗi)**: Khi một dịch vụ gặp sự cố, các dịch vụ còn lại vẫn phải hoạt động bình thường. Nguyên tắc này đòi hỏi mọi lời gọi giữa các dịch vụ đều phải có cơ chế **timeout** (giới hạn thời gian chờ), **retry** (thử lại) và **circuit breaker** (ngắt mạch — tạm thời dừng gọi đến dịch vụ lỗi để tránh lan truyền sự cố).
5. **Technology Heterogeneity (Đa dạng công nghệ)**: Mỗi dịch vụ có thể được phát triển bằng ngôn ngữ lập trình, framework, hoặc loại cơ sở dữ liệu phù hợp nhất với bài toán cụ thể mà nó giải quyết, thay vì phải đồng nhất công nghệ trên toàn bộ hệ thống. Nguyên tắc này cho phép các đội kỹ thuật tận dụng thế mạnh của từng công nghệ — ví dụ dùng Python cho các dịch vụ xử lý dữ liệu và machine learning, dùng Go cho các dịch vụ yêu cầu độ trễ thấp và khả năng xử lý đồng thời cao.

#### 2.1.3. Các mẫu thiết kế phổ biến

Để hiện thực hóa năm nguyên tắc trên trong thực tiễn, cộng đồng phần mềm đã phát triển và chuẩn hóa một tập hợp các **design patterns microservices** — những mẫu thiết kế đã được kiểm chứng ở nhiều hệ thống thực tế. Các pattern quan trọng nhất bao gồm:

1. **API Gateway Pattern**: Toàn bộ luồng yêu cầu từ phía client đi qua một điểm vào duy nhất gọi là API Gateway. Gateway đảm nhiệm các mối quan tâm xuyên suốt (cross-cutting concerns) gồm xác thực người dùng, định tuyến đến dịch vụ đích, giới hạn tần suất yêu cầu (rate limiting), và tổng hợp dữ liệu từ nhiều dịch vụ. Pattern này giúp đơn giản hóa kiến trúc phía client và tập trung các tính năng bảo mật tại một điểm duy nhất.
2. **Database per Service**: Mỗi microservice sở hữu một cơ sở dữ liệu riêng, không chia sẻ schema hoặc bảng với dịch vụ khác. Pattern này là sự cụ thể hóa của nguyên tắc _Decentralized Data Management_. Trong thực tế, có hai biến thể phổ biến: **vật lý riêng biệt** (mỗi dịch vụ một database instance) hoặc **logic riêng biệt** (các dịch vụ chia sẻ cùng một database instance nhưng mỗi dịch vụ chỉ truy cập tập bảng của riêng nó).
3. **Service Discovery**: Các dịch vụ đăng ký địa chỉ của mình vào một **service registry** trung tâm khi khởi động, và tra cứu registry này khi cần gọi đến dịch vụ khác. Pattern này loại bỏ việc hardcode địa chỉ dịch vụ, cho phép các dịch vụ thay đổi vị trí (ví dụ khi restart hoặc scale) mà không cần cấu hình lại các dịch vụ phụ thuộc.
4. **Circuit Breaker**: Khi một dịch vụ phát hiện dịch vụ phía sau đang gặp sự cố (ví dụ nhiều lời gọi liên tiếp bị timeout), nó mở **cầu dao** (circuit breaker) và tạm thời ngừng gọi đến dịch vụ đó trong một khoảng thời gian. Sau khoảng thời gian này, cầu dao chuyển sang trạng thái **half-open** để thử gửi một lời gọi kiểm tra — nếu thành công, cầu dao đóng lại; nếu thất bại, cầu dao tiếp tục ở trạng thái mở. Pattern này ngăn chặn hiện tượng **cascade failure** — khi một dịch vụ lỗi kéo theo toàn bộ hệ thống sập.
5. **Event-Driven Architecture**: Các dịch vụ giao tiếp không đồng bộ thông qua sự kiện thay vì gọi trực tiếp nhau trong chu kỳ request. Khi một dịch vụ tạo ra thay đổi (ví dụ tạo booking mới), nó phát sinh sự kiện vào một **message broker** (RabbitMQ, Kafka, Redis Pub/Sub); các dịch vụ khác quan tâm đến sự kiện này chủ động đăng ký (subscribe) và nhận thông báo. Pattern này giảm cập lệ giữa các dịch vụ — publisher không cần biết ai là subscriber, và ngược lại.
6. **Saga Pattern**: Một quy trình nghiệp vụ trải qua nhiều dịch vụ (ví dụ đặt chỗ liên quan đến kiểm tra slot, tạo booking, thu tiền, gửi thông báo) được chia thành chuỗi các giao dịch cục bộ (local transactions). Mỗi bước trong saga có thể được khôi phục (compensate) nếu bước sau đó thất bại. Pattern này giải quyết bài toán **giao dịch phân tán** mà không cần two-phase commit — một kỹ thuật phức tạp và có hiệu năng thấp.
7. **CQRS (Command Query Responsibility Segregation)**: Tách biệt mô hình dữ liệu cho thao tác ghi (command) và thao tác đọc (query) — cho phép tối ưu mỗi mô hình độc lập. Thao tác ghi thường qua các command handler với validation nghiêm ngặt, trong khi thao tác đọc qua các query được tối ưu hiệu năng bằng cache, denormalization, hoặc materialized view.

#### 2.1.4. So sánh với các kiến trúc phần mềm thay thế

Việc lựa chọn kiến trúc phần mềm luôn là một quyết định đánh đổi giữa độ phức tạp vận hành và khả năng mở rộng. Bảng dưới đây so sánh microservices với ba kiến trúc thay thế phổ biến:

| Tiêu chí | Microservices | Monolithic | Serverless (FaaS) | SOA truyền thống |
|---|---|---|---|---|
| Độ phức tạp khởi tạo | Cao | Thấp | Trung bình | Cao |
| Độ phức tạp vận hành | Cao | Thấp | Thấp (nhà cung cấp lo) | Trung bình |
| Khả năng mở rộng độc lập | ✅ Mở rộng từng dịch vụ | ❌ Mở rộng toàn bộ | ✅ Tự động theo từng hàm | ⚠️ Giới hạn |
| Hỗ trợ đa ngôn ngữ | ✅ Mỗi dịch vụ tùy chọn | ❌ Một ngôn ngữ duy nhất | ⚠️ Giới hạn theo runtime vendor | ⚠️ Giới hạn |
| Cô lập lỗi | ✅ Dịch vụ lỗi không sập hệ thống | ❌ Một lỗi kéo sập toàn bộ | ✅ Cô lập ở cấp hàm | ⚠️ Tùy triển khai |
| Triển khai độc lập | ✅ Từng dịch vụ riêng | ❌ Toàn bộ mỗi lần | ✅ Từng hàm riêng | ❌ Thường toàn bộ |
| Khả năng quản lý giao dịch | ⚠️ Nhất quán dần dần (eventual consistency) | ✅ ACID trong một database | ⚠️ Nhất quán dần dần | ⚠️ Phức tạp (distributed transactions) |
| Chi phí hạ tầng | Cao (nhiều container) | Thấp | Thấp (pay per use) | Cao |
| Phù hợp với đội nhỏ | ❌ | ✅ | ✅ | ❌ |
| Phù hợp với đội lớn | ✅ | ❌ | ✅ | ✅ |

**Lý do ParkSmart lựa chọn kiến trúc Microservices** được đặt ngắn gọn trong một đoạn biện luận duy nhất (để tránh lặp nội dung sang Chương 3): đề tài yêu cầu đồng thời nhiều ngôn ngữ lập trình — Python cho các dịch vụ nghiệp vụ và AI inference, Go cho các dịch vụ hiệu năng cao xử lý gateway và kết nối thời gian thực — mà mô hình monolithic không thể hỗ trợ. Ngoài ra, các dịch vụ có yêu cầu tài nguyên khác biệt rõ rệt (dịch vụ AI cần nhiều RAM và GPU, dịch vụ xác thực chỉ cần tài nguyên tối thiểu), và tính cô lập lỗi là bắt buộc vì một sự cố ở dịch vụ chatbot không được phép làm gián đoạn luồng check-in/check-out phương tiện. Chi tiết phân rã mười microservice cụ thể của đề tài sẽ được trình bày tại **Chương 3, Mục 3.1.2 — Danh sách 10 Microservices**.

#### 2.1.5. Ưu và nhược điểm của kiến trúc Microservices

**Ưu điểm:**

- **Khả năng mở rộng độc lập**: Mỗi dịch vụ có thể được scale theo nhu cầu riêng — dịch vụ có tải cao được phân bổ nhiều instance, dịch vụ có tải thấp chỉ cần một instance. Điều này giúp tối ưu chi phí hạ tầng so với kiến trúc monolithic vốn phải scale toàn bộ ứng dụng.
- **Cô lập lỗi ở cấp dịch vụ**: Một dịch vụ gặp sự cố không kéo theo toàn bộ hệ thống sập. Khi kết hợp với các pattern như circuit breaker, hệ thống có thể tự phục hồi khỏi các sự cố cục bộ.
- **Triển khai độc lập và nhanh chóng**: Đội phát triển có thể triển khai từng dịch vụ riêng rẽ nhiều lần mỗi ngày mà không ảnh hưởng đến các dịch vụ khác — gọi là **continuous deployment**. Thời gian triển khai ngắn giảm đáng kể rủi ro và cho phép phản hồi nhanh với phản hồi từ người dùng.
- **Tự do lựa chọn công nghệ**: Mỗi dịch vụ có thể dùng ngôn ngữ, framework, hoặc cơ sở dữ liệu phù hợp nhất với bài toán của mình — tận dụng thế mạnh của từng công nghệ thay vì chọn một công nghệ đa năng có thể không phải là tốt nhất cho mọi trường hợp.
- **Hỗ trợ đội phát triển lớn**: Các đội nhỏ có thể làm việc độc lập trên các dịch vụ riêng biệt, giảm xung đột trong quá trình phát triển và triển khai. Mô hình này được các công ty công nghệ lớn áp dụng để cho phép hàng trăm đội kỹ thuật cùng làm việc trên một sản phẩm mà không cản trở nhau.

**Nhược điểm:**

- **Độ phức tạp vận hành cao**: Vận hành hàng chục dịch vụ với container, network, service discovery, message broker, và monitoring đòi hỏi đội ngũ có kinh nghiệm về DevOps và các công cụ hạ tầng hiện đại. Đây là rào cản lớn với các đội nhỏ hoặc dự án quy mô vừa.
- **Độ phức tạp gỡ lỗi và truy vết**: Một request từ người dùng có thể đi qua nhiều dịch vụ nối tiếp — khi lỗi xảy ra, việc xác định nguyên nhân cần các công cụ truy vết phân tán (distributed tracing) như Jaeger hoặc Zipkin. Trong khi đó, monolithic cho phép gỡ lỗi đơn giản bằng cách đọc stack trace trong một process duy nhất.
- **Quản lý giao dịch phân tán phức tạp**: Khi một quy trình nghiệp vụ cần cập nhật dữ liệu trên nhiều dịch vụ (ví dụ đặt chỗ, thu tiền, gửi thông báo), việc đảm bảo tính nhất quán ACID trên toàn bộ quy trình là không khả thi theo cách truyền thống. Cần áp dụng các pattern phức tạp hơn như Saga hoặc chấp nhận mô hình **nhất quán dần dần (eventual consistency)**.
- **Chi phí hạ tầng cao hơn**: Nhiều dịch vụ đồng nghĩa với nhiều container, nhiều process, nhiều kết nối mạng — tổng chi phí hạ tầng và tiêu thụ tài nguyên cao hơn so với monolithic. Với các dự án nhỏ, chi phí này không được bù đắp bởi các lợi ích mà microservices mang lại.
- **Chi phí phát triển ban đầu lớn**: Thiết lập một hệ thống microservices từ đầu đòi hỏi nhiều công sức hơn so với monolithic — cần thiết lập mạng giữa các dịch vụ, cấu hình API Gateway, triển khai message broker, thiết lập monitoring, và xây dựng các cơ chế service discovery. Trong giai đoạn đầu của dự án, monolithic thường cho phép ra sản phẩm nhanh hơn.

Mặc dù có nhiều nhược điểm, microservices vẫn là kiến trúc được lựa chọn khi dự án yêu cầu ít nhất một trong các đặc tính sau: đa ngôn ngữ lập trình, khả năng mở rộng độc lập từng thành phần, cô lập lỗi nghiêm ngặt, triển khai nhiều lần mỗi ngày, hoặc đội phát triển lớn chia thành nhiều nhóm nhỏ tự trị. Đây chính là lý do kiến trúc này được các công ty công nghệ lớn như Netflix, Amazon, Uber, Spotify áp dụng rộng rãi từ thập niên 2010, và trở thành mô hình chuẩn mực cho các hệ thống phần mềm quy mô trung bình đến lớn hiện nay.

---

## 6. Hướng dẫn rewrite các Mục 2.2 đến 2.10 theo nguyên tắc thuần lý thuyết

Phần này liệt kê **những gì cần cắt** khỏi mỗi mục trong phiên bản hiện tại, và **những gì giữ lại** để đảm bảo Chương 2 tuân thủ nguyên tắc "cơ sở lý thuyết thuần túy".

### 6.1. Quy tắc chung — áp dụng cho mọi mục

**CẮT khỏi Chương 2 (chuyển sang Chương 3 hoặc xóa):**

- Toàn bộ tiểu mục có tiêu đề dạng **"Các kỹ thuật chính áp dụng trong ParkSmart"**. Nội dung các tiểu mục này chuyển sang Chương 3 dưới dạng "Triển khai [dịch vụ] bằng [công nghệ]".
- Các đoạn văn bắt đầu bằng **"Trong dự án ParkSmart..."**, **"Trong ParkSmart, [công nghệ] được sử dụng cho..."**, **"ParkSmart tích hợp [công nghệ] với phiên bản X.Y.Z..."**. Các đoạn này được thay bằng câu giới thiệu công nghệ thuần túy.
- Các thông số cụ thể gắn với triển khai của đề tài: số hiệu cổng (8001, 8002, 8009…), phiên bản thư viện (Django 5.2.12, DRF 3.15.2, FastAPI 0.134.0…), tên file (`docker-compose.yml`, `settings.py`…), số lượng đối tượng cụ thể (4 microservices, 158 ô đỗ, 6 camera ảo…). Các chi tiết này chỉ xuất hiện ở Chương 3.
- Các câu có dạng **"Chi tiết… sẽ được trình bày ở Chương 3"** — câu này không cần thiết khi nội dung đã thuần lý thuyết; người đọc biết rằng phần áp dụng nằm ở Chương 3.

**GIỮ LẠI trong Chương 2:**

- Định nghĩa công nghệ, lịch sử, tác giả, năm ra đời.
- Kiến trúc chung của công nghệ (sơ đồ, các thành phần, luồng xử lý) — **kiến trúc của bản thân công nghệ**, không phải cách đề tài sắp xếp các dịch vụ.
- Bảng so sánh công nghệ với các phương án thay thế — đây là phần biện luận thuộc cơ sở lý thuyết.
- Một đoạn ngắn (tối đa 3–5 câu) nêu lý do đề tài lựa chọn công nghệ này, đặt ở cuối phần so sánh.
- Ưu và nhược điểm kỹ thuật vốn có của công nghệ (không riêng đề tài).

### 6.2. Mục 2.2 — Trí tuệ nhân tạo và Thị giác máy tính

Mục 2.2 trong phiên bản hiện tại đã có cấu trúc khá chuẩn lý thuyết: có lịch sử AI, định nghĩa Machine Learning/Deep Learning, kiến trúc CNN, giới thiệu YOLO và TrOCR và MobileNetV3 ở mức thuật toán. **Phần lớn nội dung này giữ nguyên**.

**CẦN CẮT:**

- Tiểu mục **2.2.5 — Ứng dụng AI và Computer Vision trong bãi xe thông minh**: phần này mô tả cụ thể các pipeline của ParkSmart, nên chuyển sang Chương 3 (dưới mục "3.3.2. Thiết kế AI Pipeline").
- Tiểu mục **2.2.10 — Kiến trúc AI/Computer Vision Pipeline** (phần mô tả pipeline cụ thể của ParkSmart với các bước cascade fallback): chuyển sang Chương 3 mục tương ứng.
- Tiểu mục **2.2.11 — Các kỹ thuật chính**: nếu các kỹ thuật này là thuần lý thuyết (ví dụ data augmentation, transfer learning) thì giữ lại; nếu là chi tiết triển khai của ParkSmart thì chuyển sang Chương 3.

**GIỮ LẠI:**

- 2.2.1 Trí tuệ nhân tạo (định nghĩa, lịch sử, phân loại)
- 2.2.2 Machine Learning và Deep Learning (các khái niệm nền tảng)
- 2.2.3 Computer Vision (lịch sử, các bài toán cơ bản)
- 2.2.4 Convolutional Neural Network (kiến trúc CNN)
- 2.2.6 YOLO (thuật toán, phát triển qua các phiên bản, nguyên lý real-time detection)
- 2.2.7 TrOCR (kiến trúc Transformer-based OCR)
- 2.2.8 MobileNetV3 (kiến trúc CNN nhẹ cho mobile)
- 2.2.9 OpenCV (thư viện nền tảng)
- 2.2.12 Ưu nhược điểm tổng thể

### 6.3. Mục 2.3 — Chatbot AI và Mô hình Ngôn ngữ Lớn (di chuyển từ 2.8 cũ)

**CẮT:**

- Tiểu mục **2.8.4 — Các kỹ thuật chính áp dụng trong ParkSmart** (pipeline 7 giai đoạn cụ thể): chuyển sang Chương 3.
- Các đoạn liệt kê 16 intent cụ thể của ParkSmart: chuyển sang Chương 3.
- Phần "**d) Kiến trúc Hexagonal (Ports & Adapters) cho Chatbot Service**" nếu có mô tả cấu trúc thư mục cụ thể: giữ phần định nghĩa Hexagonal Architecture, cắt phần mô tả cấu trúc thư mục ParkSmart.

**GIỮ LẠI:**

- 2.3.1 Giới thiệu Chatbot (định nghĩa, lịch sử chatbot từ ELIZA đến LLM)
- 2.3.2.a Kiến trúc tổng quan chatbot AI (các giai đoạn pipeline chung, không riêng ParkSmart)
- 2.3.2.b Kiến trúc Transformer — nền tảng LLM
- 2.3.2.c Google Gemini — LLM đa phương thức (giới thiệu model, kiến trúc, khả năng)
- 2.3.2.d Kiến trúc Hexagonal (giới thiệu pattern, định nghĩa Ports và Adapters)
- 2.3.3 Lý do lựa chọn Gemini (với bảng so sánh GPT-4, Claude, Gemini…)
- Ưu nhược điểm của Chatbot AI dùng LLM

### 6.4. Mục 2.4 — Internet of Things (di chuyển từ 2.3 cũ)

**CẮT:**

- Tiểu mục **2.3.4 — Các kỹ thuật chính áp dụng trong ParkSmart** (giao thức UART tự thiết kế, OLED I2C, HTTP REST từ ESP32…): chuyển sang Chương 3.
- Danh sách thiết bị IoT cụ thể của ParkSmart (ESP32, Arduino, servo SG90, OLED SSD1306, camera DroidCam…): rút ngắn thành một bảng tham chiếu chung các loại thiết bị IoT phổ biến, chuyển danh sách cụ thể sang Chương 3.

**GIỮ LẠI:**

- 2.4.1 Giới thiệu IoT (định nghĩa Kevin Ashton, lịch sử phát triển, vị trí trong Smart City)
- 2.4.2 Kiến trúc IoT tham chiếu (mô hình 3 lớp Perception–Network–Application, IoT Gateway pattern, Edge vs Cloud Computing)
- 2.4.3 So sánh các vi điều khiển phổ biến (ESP32, Raspberry Pi, STM32, ESP8266) — giữ vì là phần biện luận lựa chọn công nghệ
- 2.4.4 So sánh các giao thức truyền thông IoT (HTTP, MQTT, CoAP, LoRa) — giữ vì là lý thuyết giao thức
- Ưu nhược điểm của giải pháp IoT sử dụng vi điều khiển (phổ quát, không riêng ParkSmart)

### 6.5. Mục 2.5 — Unity Game Engine (di chuyển từ 2.9 cũ)

**CẮT:**

- Tiểu mục **2.9.4 — Kỹ thuật chủ yếu sử dụng trong ParkSmart** (30 C# scripts, 6 virtual cameras, 158 ô đỗ procedural…): chuyển sang Chương 3.
- Các chi tiết về số lượng và cấu trúc của ParkingSimulatorUnity: chuyển sang Chương 3.

**GIỮ LẠI:**

- 2.5.1 Giới thiệu Unity (lịch sử, phiên bản chính, thị phần trong ngành game)
- 2.5.2 So sánh Unity với Unreal Engine và Godot (bảng so sánh phục vụ biện luận)
- 2.5.3 Universal Render Pipeline (URP) — giới thiệu SRP, URP, HDRP ở mức kiến trúc
- 2.5.4 Khái niệm Digital Twin — định nghĩa, các ứng dụng phổ biến trong công nghiệp và đô thị thông minh
- 2.5.5 Ưu nhược điểm của Unity cho mô phỏng kỹ thuật

### 6.6. Mục 2.6 — Django REST Framework (di chuyển từ 2.4 cũ)

**CẮT:**

- Tiểu mục **2.4.3 — Các kỹ thuật chính áp dụng trong ParkSmart** (toàn bộ tiểu mục — chuyển sang Chương 3 dưới mục "Triển khai dịch vụ Django").
- Các đoạn nói "Trong ParkSmart, DRF phiên bản 3.15.2 kết hợp Django 5.2.12 là nền tảng cho 4 dịch vụ backend CRUD chính: auth-service (cổng 8001)…": thay bằng một câu ngắn gọn ở cuối mục như "Đề tài ParkSmart sử dụng Django REST Framework cho các dịch vụ backend nghiệp vụ; chi tiết triển khai được trình bày ở Chương 3."
- Các chi tiết về tên bảng, quan hệ cụ thể của ParkSmart (User, Vehicle, Booking, ParkingSlot…): chuyển sang Chương 3.

**GIỮ LẠI:**

- 2.6.1 Giới thiệu Django và DRF (lịch sử, tác giả Tom Christie, vị trí trong hệ sinh thái Python web)
- 2.6.2 Kiến trúc DRF (Model – Serializer – View – Router – Authentication – Permission – Throttling) — đây là kiến trúc của công nghệ, không phải của đề tài
- 2.6.3 So sánh DRF với Flask, Express.js, Spring Boot (bảng so sánh)
- 2.6.4 Ưu nhược điểm của DRF (phổ quát)

### 6.7. Mục 2.7 — FastAPI (di chuyển từ 2.5 cũ)

**CẮT:**

- Tiểu mục **2.5.4 — Các kỹ thuật chính áp dụng trong ParkSmart**: chuyển sang Chương 3.
- Các đoạn nói "ParkSmart tích hợp FastAPI cho 4 dịch vụ...": thay bằng câu ngắn ở cuối mục.

**GIỮ LẠI:**

- 2.7.1 Giới thiệu FastAPI (tác giả Sebastián Ramírez, năm 2018, vị trí trong hệ sinh thái Python)
- 2.7.2 Kiến trúc FastAPI (ASGI vs WSGI, Starlette, Pydantic, OpenAPI auto-generation, async/await native)
- 2.7.3 So sánh FastAPI với Flask, Django, Node.js Express
- 2.7.4 Ưu nhược điểm của FastAPI (phổ quát)

### 6.8. Mục 2.8 — Go, Gin Framework và Gorilla WebSocket (di chuyển từ 2.6 cũ)

**CẮT:**

- Tiểu mục **2.6.6 — Các kỹ thuật chính sử dụng trong Go Services**: chuyển sang Chương 3.
- Các đoạn nói "Gateway service và Realtime service của ParkSmart được viết bằng Go...": thay bằng câu ngắn ở cuối mục.

**GIỮ LẠI:**

- 2.8.1 Giới thiệu ngôn ngữ Go (tác giả Google — Rob Pike, Ken Thompson, Robert Griesemer; năm 2009; các đặc tính: goroutine, channel, compiled binary)
- 2.8.2 Giới thiệu Gin Framework (kiến trúc middleware, routing, performance benchmarks)
- 2.8.3 Giới thiệu Gorilla WebSocket (thư viện WebSocket chuẩn cho Go)
- 2.8.4 Kiến trúc Go Runtime (goroutine scheduling, garbage collector, mô hình concurrency)
- 2.8.5 So sánh Go với Python, Node.js, Rust cho các bài toán hiệu năng cao
- 2.8.6 Ưu nhược điểm của Go

### 6.9. Mục 2.9 — ReactJS (di chuyển từ 2.7 cũ)

**CẮT:**

- Tiểu mục **2.7.4 — Các kỹ thuật chính áp dụng trong ParkSmart**: chuyển sang Chương 3.
- Các đoạn nói "Frontend ParkSmart với 73 UI components...": thay bằng câu ngắn ở cuối mục.

**GIỮ LẠI:**

- 2.9.1 Giới thiệu React (Meta/Facebook, 2013, Jordan Walke, vị trí trong hệ sinh thái JavaScript frontend)
- 2.9.2 Kiến trúc React (Virtual DOM, Component-based, JSX, Hooks, Unidirectional Data Flow)
- 2.9.3 TypeScript (Microsoft, 2012, mối quan hệ với JavaScript, lợi ích type safety)
- 2.9.4 Redux Toolkit và React Query (state management patterns)
- 2.9.5 So sánh React với Vue, Angular, Svelte
- 2.9.6 Ưu nhược điểm của React

### 6.10. Mục 2.10 — Hạ tầng và các dịch vụ hỗ trợ

Mục này tổng hợp các tiểu mục 2.1.1 đến 2.1.5 cũ, đặt xuống cuối chương. Các tiểu mục con (2.10.1 MySQL, 2.10.2 Redis, 2.10.3 RabbitMQ, 2.10.4 Docker, 2.10.5 Nginx) cần được rà soát và cắt phần "trong ParkSmart" tương tự.

**CẮT:**

- Các đoạn nói "Trong kiến trúc ParkSmart, Redis đảm nhận năm vai trò đồng thời..." (mô tả chi tiết 7 logical database của ParkSmart): chuyển sang Chương 3 dưới mục "Triển khai hạ tầng ParkSmart".
- Chi tiết về 15 containers của ParkSmart: chuyển sang Chương 3.
- Các đoạn nói "Trong ParkSmart, MySQL đóng vai trò cơ sở dữ liệu duy nhất với database đơn `parksmartdb`...": rút gọn thành câu ngắn.

**GIỮ LẠI:**

- 2.10.1 MySQL (lịch sử, tác giả Oracle, ACID, InnoDB, các tính năng chính của MySQL 8.0)
- 2.10.2 Redis (lịch sử, tác giả Salvatore Sanfilippo, các cấu trúc dữ liệu, cơ chế Pub/Sub và persistence)
- 2.10.3 RabbitMQ (chuẩn AMQP, mô hình producer-exchange-queue-consumer, message persistence)
- 2.10.4 Docker (containerization, image vs container, Dockerfile, Docker Compose)
- 2.10.5 Nginx (event-driven architecture, reverse proxy, load balancing)
- Các bảng so sánh với công nghệ thay thế (PostgreSQL, Memcached, Kafka, Podman, Apache HTTP Server)

---

## 7. Các phần "áp dụng trong ParkSmart" sẽ được di chuyển sang Chương 3

Khi rewrite Chương 2 theo guide này, các phần sau cần được di chuyển sang Chương 3 — một số đã có sẵn vị trí phù hợp, một số cần tạo tiểu mục mới:

| Nội dung cắt khỏi Chương 2 | Vị trí đích ở Chương 3 |
|---|---|
| 2.1.6 cũ: 7 pattern microservices áp dụng trong ParkSmart | Mục 3.1 hoặc 3.4 — "Các pattern microservices áp dụng" |
| 2.1.7 cũ: Ưu nhược điểm tổng thể của hạ tầng ParkSmart | Mục 3.4.3 và 3.4.4 hiện có |
| 2.2.5, 2.2.10, 2.2.11 cũ: Ứng dụng AI và pipeline cụ thể | Mục 3.3 — thêm tiểu mục "Thiết kế AI Pipeline" |
| 2.3.4 cũ: Kỹ thuật IoT áp dụng (UART, OLED I2C, HTTP REST, heartbeat, anti-noise, auto-close) | Mục 3.3 — thêm tiểu mục "Thiết kế hệ thống IoT ParkSmart" |
| 2.4.3 cũ: Kỹ thuật DRF áp dụng (Serializer, ViewSet, Session-based auth, Celery, Filtering) | Mục 3.3 — thêm tiểu mục "Triển khai 4 dịch vụ DRF" |
| 2.5.4 cũ: Kỹ thuật FastAPI áp dụng | Mục 3.3 — thêm tiểu mục "Triển khai 4 dịch vụ FastAPI" |
| 2.6.6 cũ: Kỹ thuật Go áp dụng (Gateway proxy pattern, session store, WebSocket hub) | Mục 3.3 — thêm tiểu mục "Triển khai Gateway và Realtime Go" |
| 2.7.4 cũ: Kỹ thuật React áp dụng (Redux Toolkit slices, React Query, shadcn components) | Mục 3.3.3 (đã có "Thiết kế giao diện") |
| 2.8.4 cũ: Pipeline Chatbot 7 giai đoạn, 16 intents, Hexagonal directory structure | Mục 3.3 — thêm tiểu mục "Thiết kế Chatbot Service" |
| 2.9.4 cũ: Kỹ thuật Unity áp dụng (ParkingManager singleton, FSM, virtual cameras) | Mục 3.5.5 (đã có "Mô phỏng bãi xe 3D") |

Việc di chuyển này sẽ giúp Chương 3 **đầy đặn và đúng vai trò** — nơi trình bày chi tiết triển khai cụ thể — trong khi Chương 2 **tinh gọn và thuần lý thuyết** — nơi cung cấp nền tảng kiến thức.

---

## 8. Các bước thực thi trên VS Code (cập nhật v2)

### Bước 1: Sao lưu trước khi sửa

```bash
cp docs/BAO_CAO_PLAN.md docs/BAO_CAO_PLAN.md.bak-v2-$(date +%Y%m%d)
```

### Bước 2: Đã xong — câu mở Chương 2 đã được chèn inline

Câu mở đầu Chương 2 (dòng 307) đã được cập nhật ở phiên bản trước của guide. Xem `BAO_CAO_PLAN.md` dòng 307 để xác nhận.

### Bước 3: Chèn Mục 2.1 mới (Kiến trúc Microservices — thuần lý thuyết)

Dán toàn bộ nội dung **Mục 5** của guide này (từ `## 2.1. Kiến trúc Microservices...` đến hết tiểu mục 2.1.5) vào ngay sau câu mở Chương 2 trong `BAO_CAO_PLAN.md`. Nội dung này hoàn toàn không có đoạn "trong ParkSmart" ngoài một câu biện luận ngắn ở cuối tiểu mục 2.1.4.

### Bước 4: Rà soát và cắt phần "trong ParkSmart" ở các mục còn lại

Với mỗi mục 2.2 đến 2.9, áp dụng danh sách CẮT / GIỮ LẠI tại **Mục 6** của guide này. Cách làm trong VS Code:

1. Mở file `docs/BAO_CAO_PLAN.md`.
2. Dùng `Cmd/Ctrl+F` tìm chuỗi `"trong dự án ParkSmart"`, `"Trong ParkSmart"`, `"ParkSmart sử dụng"`, `"Các kỹ thuật chính áp dụng trong ParkSmart"`.
3. Với mỗi kết quả tìm được, đọc đoạn văn xung quanh và quyết định:
   - Nếu là **giới thiệu công nghệ** → xóa cụm "trong ParkSmart" và rewrite câu cho thuần lý thuyết.
   - Nếu là **chi tiết triển khai** → cắt toàn bộ đoạn và paste vào Chương 3 tại mục tương ứng (xem Mục 7 của guide).
4. Với các **tiểu mục có tiêu đề "Các kỹ thuật chính áp dụng trong ParkSmart"**: cắt nguyên cả tiểu mục (từ `### 2.X.N.` đến trước `### 2.X.(N+1).` hoặc `## 2.(X+1).`), paste vào Chương 3.

### Bước 5: Cắt–dán các mục lớn theo thứ tự ưu tiên mới

Thực hiện các thao tác move section như đã mô tả ở phiên bản v1 của guide:

1. Cắt Mục 2.8 cũ (Chatbot) → dán sau Mục 2.2 → đổi số thành 2.3.
2. Cắt Mục 2.3 cũ (IoT) → dán sau Mục 2.3 mới (Chatbot) → đổi số thành 2.4.
3. Cắt Mục 2.9 cũ (Unity) → dán sau Mục 2.4 mới (IoT) → đổi số thành 2.5.
4. Đổi số các mục 2.4 cũ → 2.6, 2.5 → 2.7, 2.6 → 2.8, 2.7 → 2.9.
5. Cắt toàn bộ 2.1.1 đến 2.1.5 cũ → dán vào cuối chương → đánh số 2.10.
6. Xóa các tiểu mục 2.1.6 và 2.1.7 cũ (đã được Mục 2.1 mới thay thế).

### Bước 6: Tạo các tiểu mục mới ở Chương 3

Mở Chương 3 (từ dòng khoảng 1834 của `BAO_CAO_PLAN.md`) và tạo các tiểu mục mới để chứa nội dung "áp dụng trong ParkSmart" đã cắt từ Chương 2:

- `### 3.3.X. Thiết kế AI Pipeline của ParkSmart` — chứa nội dung từ 2.2.5, 2.2.10, 2.2.11 cũ.
- `### 3.3.X. Thiết kế hệ thống IoT ParkSmart` — chứa nội dung từ 2.3.4 cũ.
- `### 3.3.X. Triển khai các dịch vụ DRF của ParkSmart` — chứa nội dung từ 2.4.3 cũ.
- `### 3.3.X. Triển khai các dịch vụ FastAPI của ParkSmart` — chứa nội dung từ 2.5.4 cũ.
- `### 3.3.X. Triển khai Gateway và Realtime Go` — chứa nội dung từ 2.6.6 cũ.
- `### 3.3.X. Triển khai Frontend React` — chứa nội dung từ 2.7.4 cũ.
- `### 3.3.X. Thiết kế Chatbot Service` — chứa nội dung từ 2.8.4 cũ.

### Bước 7: Kiểm tra tính nhất quán

1. Mở VS Code Outline panel, xác nhận Chương 2 có đúng 10 mục cấp 2 theo thứ tự 2.1 → 2.10.
2. Tìm trong Chương 2: chuỗi `"trong ParkSmart"` phải chỉ xuất hiện rất ít (tối đa 10 lần cho toàn bộ chương), và chỉ trong các câu biện luận ngắn ở cuối phần so sánh công nghệ.
3. Kiểm tra các tham chiếu chéo `[16]`, `[17]`, `[18]`, `[19]`, `[20]` vẫn đúng với danh sách tham khảo.
4. Xuất bản PDF nháp, đọc lướt Chương 2 xem có đọc được như một **giáo trình công nghệ** không — nếu còn nhiều đoạn "trong ParkSmart" thì cần cắt tiếp.

### Bước 8: Commit

```bash
git add docs/BAO_CAO_PLAN.md docs/BAO_CAO_PLAN_REORDER_GUIDE.md
git commit -m "docs(report): tái cấu trúc Chương 2 theo nguyên tắc lý thuyết thuần túy

- Sắp xếp lại 10 mục theo priority 'Core and Unique First'
- Cắt các tiểu mục 'Các kỹ thuật áp dụng trong ParkSmart' khỏi Chương 2
- Chuyển nội dung triển khai cụ thể sang Chương 3
- Chương 2 giờ tập trung thuần vào: định nghĩa, kiến trúc, so sánh, ưu/nhược điểm
  của từng công nghệ — không lẫn chi tiết dự án

Refs: docs/BAO_CAO_PLAN_REORDER_GUIDE.md v2"
```

---

## 9. Checklist kiểm tra chất lượng sau khi rewrite

Sau khi hoàn tất các bước 1–8, dùng checklist dưới đây để đảm bảo Chương 2 đạt chuẩn KLTN:

- [ ] Chương 2 có đúng 10 mục cấp 2 theo thứ tự mới (2.1 → 2.10).
- [ ] Mỗi mục 2.X có đủ 4 tiểu mục chuẩn: Giới thiệu, Kiến trúc/Nguyên lý, So sánh, Ưu/Nhược điểm.
- [ ] Không còn tiểu mục nào có tiêu đề `### 2.X.Y. Các kỹ thuật áp dụng trong ParkSmart`.
- [ ] Số lần xuất hiện chuỗi "ParkSmart" trong toàn Chương 2 **ít hơn 30 lần** (so với khoảng 150+ ở phiên bản cũ).
- [ ] Mỗi mục có **ít nhất một bảng so sánh công nghệ** với các phương án thay thế.
- [ ] Mỗi mục có trích dẫn tài liệu tham khảo (ít nhất một số [N]) cho phần định nghĩa hoặc lịch sử.
- [ ] Các số liệu cụ thể của ParkSmart (4 services, 158 ô đỗ, 6 camera…) không xuất hiện ở Chương 2, chỉ ở Chương 3.
- [ ] Các phiên bản thư viện cụ thể (Django 5.2.12, DRF 3.15.2…) không xuất hiện ở Chương 2, chỉ ở Chương 3 hoặc Phụ lục.
- [ ] Chương 3 đã có đủ các tiểu mục mới chứa phần "áp dụng trong ParkSmart" đã cắt từ Chương 2.
- [ ] Mục lục tự sinh đúng thứ tự và không trùng số.
- [ ] Giảng viên hướng dẫn hoặc bạn cùng lớp thử đọc Chương 2 và xác nhận: "đọc Chương 2 trước Chương 3 vẫn hiểu được các công nghệ nền tảng."

---

## 10. Tổng kết nguyên tắc vàng

> **Chương 2 trả lời câu hỏi: "Công nghệ này là gì và hoạt động ra sao?"**
>
> **Chương 3 trả lời câu hỏi: "Đề tài ParkSmart sử dụng công nghệ này như thế nào?"**

Giữ ranh giới rõ ràng giữa hai câu hỏi này là chìa khóa để Chương 2 đạt chuẩn cơ sở lý thuyết của một khóa luận tốt nghiệp. Một người đọc đọc Chương 2 mà chưa biết ParkSmart vẫn phải hiểu được bản chất công nghệ; một người đọc đọc Chương 3 sau khi đã đọc Chương 2 phải cảm nhận được tính ứng dụng cụ thể mà không cần quay lại giải thích công nghệ.

---

**File này được duy trì tại:** `docs/BAO_CAO_PLAN_REORDER_GUIDE.md`
**Liên quan đến:** `docs/BAO_CAO_PLAN.md`
**Phiên bản:** v2 — Nguyên tắc "Lý thuyết thuần túy"
**Ngày cập nhật:** 2026-04-15
