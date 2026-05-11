## 3.3.4. Thiết kế xử lý các giao diện chính

Phần này mô tả các sự kiện (handler) chính của 8 giao diện trọng yếu trong ứng dụng web ParkSmart, kèm theo điều kiện kích hoạt và ý nghĩa nghiệp vụ tương ứng. Các bảng được trích xuất trực tiếp từ mã nguồn React (TypeScript + Vite) tại `spotlove-ai/src/pages/`, tập trung vào các handler có tác động đến trạng thái ứng dụng (Redux store), gọi API qua tầng `services/business/*`, hoặc điều hướng giữa các trang.

### 1. Trang Index (Landing Page) — `/`

Trang `Index.tsx` đóng vai trò trang chủ sau đăng nhập, làm nhiệm vụ điều hướng người dùng dựa trên vai trò (role) đã xác thực.

**Bảng 3.4: Thiết kế xử lý giao diện Index (Trang chủ định tuyến)**

| STT | Tên xử lý | Điều kiện gọi thực hiện | Ý nghĩa thực hiện |
|-----|-----------|------------------------|-------------------|
| 1 | Load_Page_Init | Khi giao diện Index được mở (mount component) | Đọc trạng thái xác thực `useAuth()` từ context, chờ cờ `isLoading` chuyển về `false` để xác định người dùng. |
| 2 | AuthState_Change | Khi `user` hoặc `isLoading` thay đổi (useEffect deps) | Nếu `user.role === "admin"` thì gọi `navigate("/admin/dashboard", { replace: true })` để chuyển trang quản trị, tránh thêm vào lịch sử trình duyệt. |
| 3 | Loading_Render | Khi `isLoading === true` | Hiển thị màn hình "Loading..." chiếm toàn bộ viewport, chặn người dùng tương tác trước khi có dữ liệu auth. |
| 4 | UserDashboard_Mount | Khi `isLoading === false` và `role !== "admin"` | Render component `<UserDashboard />` để hiển thị giao diện dành cho người dùng cuối. |

---

### 2. Trang User Dashboard — `/`

Trang `UserDashboard.tsx` là bảng điều khiển cá nhân hiển thị xe đang đậu, thống kê nhanh, danh sách xe đã lưu và hoạt động gần đây.

**Bảng 3.5: Thiết kế xử lý giao diện User Dashboard**

| STT | Tên xử lý | Điều kiện gọi thực hiện | Ý nghĩa thực hiện |
|-----|-----------|------------------------|-------------------|
| 1 | Load_Page_Init | Khi giao diện UserDashboard được mở | Gọi đồng thời `loadCurrentParking()`, `loadBookings()`, `loadNotifications()` (Redux thunks), đồng thời `vehicleService.getAll()` để đếm số xe đã lưu, cập nhật state `vehicleCount`. |
| 2 | XemCamera_Click | Người dùng nhấn nút "Xem camera" trên thẻ xe đang đậu | Tra cứu `ZONE_CAMERA_MAP` để chuyển tên zone (Nam/Bắc/A/B) thành `cameraId`, sau đó `navigate("/cameras?camera=<id>")`. |
| 3 | BaoSuCo_Click | Người dùng nhấn nút "Báo sự cố" | Điều hướng `navigate("/panic")` để mở trang báo cáo sự cố khẩn cấp. |
| 4 | DatChoMoi_Click | Người dùng nhấn nút "Đặt chỗ ngay" hoặc "Đặt chỗ mới" | Điều hướng `navigate("/booking")` để mở wizard đặt chỗ 5 bước. |
| 5 | XemBanDo_Click | Người dùng nhấn nút "Xem bản đồ" | Điều hướng `navigate("/map")` để xem bản đồ bãi và đường đi tới slot. |
| 6 | LichSu_Click | Người dùng nhấn vào thẻ thống kê "Sắp tới" | Điều hướng `navigate("/history")` để xem chi tiết các booking sắp tới và lịch sử. |

---

### 3. Trang Booking (Đặt chỗ) — `/booking`

Trang `BookingPage.tsx` triển khai wizard đặt chỗ 5 bước (Chọn bãi → Chọn xe → Chọn vị trí → Thời gian → Thanh toán) với 3 chế độ tab: Chuẩn, Auto-Guarantee và Calendar Auto-Hold.

**Bảng 3.6: Thiết kế xử lý giao diện Booking (Đặt chỗ)**

| STT | Tên xử lý | Điều kiện gọi thực hiện | Ý nghĩa thực hiện |
|-----|-----------|------------------------|-------------------|
| 1 | Load_Page_Init | Khi giao diện Booking được mở | Gọi `loadParkingLots()` (Redux thunk) để nạp danh sách bãi đỗ, đồng thời `vehicleService.getAll()` để hiển thị danh sách xe đã lưu và auto-chọn xe mặc định (`isDefault === true`). |
| 2 | ParkingLot_Change | Khi `selectedParkingLot` thay đổi | Gọi `parkingService.getFloors(lotId)` để nạp danh sách tầng (kèm zones lồng nhau) của bãi vừa chọn, cập nhật state `floors`. |
| 3 | Zone_Change | Khi `selectedZone` thay đổi | Gọi `loadSlots(zoneId)` (Redux thunk) để nạp slot trong zone, đồng thời `subscribeToZone(zoneId)` qua WebSocket để nhận realtime occupancy; khi unmount sẽ tự `unsubscribeFromZone`. |
| 4 | SlotRealtime_Change | Khi mảng `slots` từ Redux cập nhật và slot đang chọn không còn `available` | Tự động xoá slot đã chọn (`setSelectedSlot(null)`) và bật toast cảnh báo "Vị trí không còn trống" để người dùng chọn lại. |
| 5 | LoaiXe_Change | Người dùng nhấn nút "Ô tô" hoặc "Xe máy" | Cập nhật `vehicleType`, đồng thời reset `selectedFloor`, `selectedZone`, `selectedSlot`, `selectedVehicleId` để tránh chọn nhầm vị trí của loại xe khác. |
| 6 | XeDaLuu_Click | Người dùng nhấn vào một xe trong "Xe đã sử dụng gần đây" | Gọi `handleSelectSavedVehicle(vehicle)` để điền `licensePlate`, `vehicleType` và lưu `selectedVehicleId`, đồng thời reset vị trí để chọn lại theo loại xe. |
| 7 | TiepTuc_Click | Người dùng nhấn nút "Tiếp tục" tại các bước 1-4 | Kiểm tra `canProceed()`, nếu hợp lệ tăng `currentStep` lên bước kế tiếp. |
| 8 | DatCho_Submit | Người dùng nhấn "Thanh toán ngay" / "Xác nhận đặt chỗ" tại bước 5 | Gọi `handleSubmit()` validate dữ liệu, dựng `bookingData`, sau đó `create(bookingData)` (Redux thunk → `POST /api/bookings/`). Nếu thành công và là online → `navigate("/payment?bookingId=...")`; nếu trả sau → mở dialog QR code. |

---

### 4. Trang Map (Bản đồ bãi xe) — `/map`

Trang `MapPage.tsx` hiển thị sơ đồ SVG của bãi xe và sử dụng thuật toán Dijkstra (`@/lib/dijkstra`) để vẽ đường đi từ cổng vào tới slot đã đặt, kèm hoạt cảnh xe di chuyển.

**Bảng 3.7: Thiết kế xử lý giao diện Map (Bản đồ và chỉ đường)**

| STT | Tên xử lý | Điều kiện gọi thực hiện | Ý nghĩa thực hiện |
|-----|-----------|------------------------|-------------------|
| 1 | Load_Page_Init | Khi giao diện Map được mở | Bật cờ `isLoading`, gọi `loadCurrentParking()` để lấy booking đang hoạt động; nếu không có sẽ tự fallback sang `generateDemoData()` để vẫn render bản đồ minh hoạ. |
| 2 | CurrentParking_Change | Khi `currentParking` thay đổi | Cập nhật `currentBooking` từ dữ liệu API và gọi `loadZones(lotId)` để nạp toàn bộ zone của bãi tương ứng. |
| 3 | Zones_Change | Khi `zones` được nạp xong | Lặp qua từng zone gọi `parkingService.getSlotsForZone(zone.id)`, dồn kết quả vào state `allSlots` để tính toán layout SVG. |
| 4 | Floor_Change | Người dùng đổi giá trị trong `<select>` Tầng | Cập nhật `selectedFloor`, kéo theo `mapZones` và `mapSlots` được tính lại qua `useMemo`, làm SVG render lại tầng mới. |
| 5 | ChiDuong_Click | Người dùng nhấn nút "Chỉ đường" (toggle) | Bật/tắt `showDirections` để hiển thị/ẩn panel `<DirectionsPanel>` cùng đường đi tĩnh trên SVG. |
| 6 | StartNavigation_Click | Người dùng nhấn nút "Bắt đầu" trong DirectionsPanel | Gọi `handleStartNavigation()`: bật `isNavigating`, reset `currentStepIndex`, khởi động `requestAnimationFrame` chạy hoạt cảnh xe di chuyển dọc `pathWaypoints` trong 8 giây. |
| 7 | StopNavigation_Click | Người dùng nhấn nút "Dừng" trong floating banner | Gọi `handleStopNavigation()`: tắt `isNavigating`, huỷ `cancelAnimationFrame` để dừng hoạt cảnh và trở về trạng thái xem tĩnh. |
| 8 | DatChoNgay_Click | Người dùng nhấn nút "Đặt chỗ ngay" trên banner demo | Điều hướng `navigate("/booking")` để người dùng tạo booking thật thay cho dữ liệu mẫu. |

---

### 5. Trang History (Lịch sử & Thống kê) — `/history`

Trang `HistoryPage.tsx` hiển thị danh sách booking, biểu đồ chi tiêu theo tháng (Recharts), và cho phép thao tác hủy/xem QR/chuyển sang thanh toán.

**Bảng 3.8: Thiết kế xử lý giao diện History (Lịch sử đặt chỗ)**

| STT | Tên xử lý | Điều kiện gọi thực hiện | Ý nghĩa thực hiện |
|-----|-----------|------------------------|-------------------|
| 1 | Load_Page_Init | Khi giao diện History được mở | Gọi `loadBookings({ status })` (Redux thunk → `GET /api/bookings/`) và `getBookingStats()` để lấy `totalSpent`, `monthlyExpenses` cho biểu đồ chi tiêu. |
| 2 | FilterStatus_Change | Khi `filterStatus` thay đổi (nút Tất cả / Đang đậu / Đã xác nhận / Hoàn thành) | Re-trigger `loadBookings({ status })` để fetch lại danh sách booking theo trạng thái mới. |
| 3 | Search_Change | Người dùng nhập vào ô "Tìm theo biển số" | Cập nhật state `searchQuery`, lọc client-side `filteredHistory` theo `licensePlate.includes(searchQuery)`. |
| 4 | XemQR_Click | Người dùng nhấn nút "Xem QR" trên thẻ booking | Gọi `handleViewQR(booking)`: lưu `selectedBooking` và mở `<Dialog>` chứa `<BookingQRCode>` để khách quét tại cổng. |
| 5 | Huy_Click | Người dùng nhấn nút "Hủy" (chỉ enable cho status pending/confirmed) | Gọi `handleCancel(booking)` để mở dialog xác nhận, lưu `bookingToCancel`. |
| 6 | XacNhanHuy_Click | Người dùng nhấn "Xác nhận hủy" trong dialog | Gọi `cancel(bookingId)` (Redux thunk → `POST /api/bookings/{id}/cancel/`), bật toast thông báo, đóng dialog. |
| 7 | ThanhToan_Click | Người dùng nhấn nút "Thanh toán" (chỉ với booking `paymentStatus === pending`) | Điều hướng `navigate("/payment?bookingId=" + booking.id)` để hoàn tất thanh toán cho booking dở dang. |
| 8 | ChiDuong_Click | Người dùng nhấn nút "Chỉ đường" (cho booking đang parked/checked_in/confirmed) | Điều hướng `navigate("/map")` để mở bản đồ và đường đi tới slot. |

---

### 6. Trang Support (Chatbot AI) — `/support`

Trang `SupportPage.tsx` triển khai giao diện chat với chatbot AI v3.0, hỗ trợ confidence breakdown, safety codes, gợi ý nhanh và phản hồi đánh giá.

**Bảng 3.9: Thiết kế xử lý giao diện Support (Chatbot AI)**

| STT | Tên xử lý | Điều kiện gọi thực hiện | Ý nghĩa thực hiện |
|-----|-----------|------------------------|-------------------|
| 1 | Load_Page_Init | Khi giao diện Support được mở | Khởi tạo state với `welcomeMessage`, gọi `chatbotService.getChatHistory()` (`GET /api/chatbot/history/`) để khôi phục hội thoại cũ kèm metadata (suggestions, confidence, safetyCode). |
| 2 | Messages_Change | Khi mảng `messages` cập nhật | Tự động cuộn xuống cuối khung chat qua `messagesEndRef.scrollIntoView({ behavior: "smooth" })`. |
| 3 | Send_Click | Người dùng nhấn nút Send hoặc Enter trong input | Gọi `handleSend()`: thêm tin nhắn user + loading bubble, sau đó `chatbotService.sendMessage(content, conversationId)` (`POST /api/chatbot/message/`), bind response (intent, confidence, suggestions, showMap, showQrCode) vào message của bot. |
| 4 | QuickAction_Click | Người dùng nhấn 1 trong 4 quick actions ("Đặt chỗ ô tô", "Tìm chỗ trống", …) | Gọi `handleSend(action.prompt)` với prompt định sẵn để chatbot xử lý ngay không cần gõ. |
| 5 | Suggestion_Click | Người dùng nhấn vào chip gợi ý (suggestions) trong response của bot | Gọi `handleSuggestionClick(suggestion)` → `handleSend(suggestion)` để tiếp tục cuộc hội thoại theo nhánh gợi ý. |
| 6 | XacNhan_Click | Khi `confirmationNeeded === true` và người dùng nhấn "Xác nhận" | Gọi `handleConfirm()` → `handleSend("Xác nhận")` để chatbot thực thi action đang chờ (vd: tạo booking, hủy booking). |
| 7 | HuyBo_Click | Khi `confirmationNeeded === true` và người dùng nhấn "Hủy bỏ" | Gọi `handleCancel()`: reset `pendingConfirmation` và gửi text "Hủy bỏ" để chatbot cập nhật trạng thái dialog. |
| 8 | DanhGia_Submit | Người dùng nhấn "Gửi đánh giá" trong panel feedback | Gọi `chatbotService.submitFeedback({ conversationId, rating, comment })` (`POST /api/chatbot/feedback/`), bật toast "Cảm ơn bạn đã phản hồi" và đóng panel. |

---

### 7. Trang Payment (Thanh toán) — `/payment`

Trang `PaymentPage.tsx` hiển thị mã VietQR, đếm ngược 15 phút và polling trạng thái thanh toán theo chu kỳ thay đổi (10s thường, 3s sau khi user xác nhận).

**Bảng 3.10: Thiết kế xử lý giao diện Payment (Thanh toán đặt chỗ)**

| STT | Tên xử lý | Điều kiện gọi thực hiện | Ý nghĩa thực hiện |
|-----|-----------|------------------------|-------------------|
| 1 | Load_Page_Init | Khi giao diện Payment được mở (mount với `?bookingId=...`) | Đọc `bookingId` từ query params, gọi `bookingService.getById(bookingId)` (`GET /api/bookings/{id}/`); nếu không có id hoặc lỗi → toast lỗi và `navigate("/history")`. |
| 2 | Booking_Change | Khi state `booking` được set xong | Khởi tạo `setInterval` mỗi 1s để cập nhật `timeLeft` (deadline = `createdAt + 15 phút`); khi diff ≤ 0 thì set `isExpired = true`. |
| 3 | PaymentPolling_Init | Khi `bookingId`, `booking` sẵn sàng và chưa `paymentConfirmed` | Khởi tạo `setInterval` polling `bookingService.pollPaymentStatus(bookingId)` (`GET /api/bookings/{id}/payment-status/`) — chu kỳ 10s mặc định, 3s khi `isVerifying`; nếu `paymentStatus === "completed"` → bật `paymentConfirmed`, toast thành công, sau 2s `navigate("/history")`. |
| 4 | Copy_Click | Người dùng nhấn nút copy bên cạnh số tài khoản hoặc mã đặt chỗ | Gọi `handleCopy(text, field)`: `navigator.clipboard.writeText(text)`, hiển thị icon Check trong 2s và bật toast "Đã sao chép". |
| 5 | DaThanhToan_Click | Người dùng nhấn nút "Tôi đã thanh toán" | Gọi `handleConfirmPayment()`: bật `isVerifying = true` để chuyển sang màn hình loading và rút chu kỳ polling xuống 3s nhằm xác minh nhanh. |
| 6 | Back_Click | Người dùng nhấn icon mũi tên ArrowLeft ở header | Gọi `navigate(-1)` để quay về trang trước (thường là `/booking` hoặc `/history`). |
| 7 | XemLichSu_Click | Người dùng nhấn "Xem lịch sử đặt chỗ" sau khi thanh toán thành công | Điều hướng `navigate("/history")` để xem booking vừa hoàn tất. |

---

### 8. Trang Admin Dashboard — `/admin/dashboard`

Trang `AdminDashboard.tsx` là trang quản trị tổng quan: hiển thị KPI (người dùng, doanh thu, occupancy), tỉ lệ lấp đầy realtime từ AI camera, slot overview, recent bookings và shortcuts đến các trang quản trị con.

**Bảng 3.11: Thiết kế xử lý giao diện Admin Dashboard**

| STT | Tên xử lý | Điều kiện gọi thực hiện | Ý nghĩa thực hiện |
|-----|-----------|------------------------|-------------------|
| 1 | Load_Page_Init | Khi giao diện Admin Dashboard được mở | Gọi song song `Promise.all([adminService.getDashboardStats(), adminService.getRecentActivities(8)])` (`GET /api/admin/dashboard/stats/` + `/activities/`), set state `stats` và `activities`. |
| 2 | NguoiDung_Click | Người dùng nhấn nút "Người dùng" trong khối Truy cập nhanh | Điều hướng `navigate("/admin/users")` để mở trang quản lý tài khoản người dùng. |
| 3 | Camera_Click | Người dùng nhấn nút "Camera" | Điều hướng `navigate("/admin/cameras")` để mở trang cấu hình danh sách camera EZVIZ và virtual cameras. |
| 4 | GiamSatLive_Click | Người dùng nhấn nút "Giám sát live" | Điều hướng `navigate("/cameras")` để mở trang xem stream realtime của tất cả camera (chia sẻ với user). |
| 5 | BaoCao_Click | Người dùng nhấn nút "Báo cáo" | Điều hướng `navigate("/admin/reports")` để mở trang biểu đồ doanh thu, occupancy theo thời gian. |
| 6 | OccupancyBar_Render | Khi `stats.occupancyRate` được nạp | Render thanh tiến trình với màu thay đổi theo ngưỡng (≤50% xanh, 50-80% vàng, >80% đỏ) để cảnh báo trực quan tình trạng quá tải bãi. |
| 7 | AILiveOccupancy_Mount | Sau khi `stats` nạp xong | Render `<AILiveOccupancyCard totalSlots={stats.activeParkings}>` — component này tự subscribe stream AI từ camera tổng để cập nhật realtime. |
| 8 | RecentActivity_Render | Khi mảng `activities` được nạp | Lặp tối đa 6 hoạt động gần nhất, mapping `type` (check_in / check_out / booking / payment / incident) sang icon tương ứng qua `getActivityIcon(type)`. |
