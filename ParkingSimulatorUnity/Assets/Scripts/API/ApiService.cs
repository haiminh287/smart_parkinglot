using System;
using System.Collections;
using System.Collections.Generic;
using System.Text;
using UnityEngine;
using UnityEngine.Networking;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using NativeWebSocket;

namespace ParkingSim.API
{
    public class ApiService : MonoBehaviour
    {
        public static ApiService Instance { get; private set; }

        [SerializeField] private ApiConfig config;
        [SerializeField] private AuthManager authManager;

        private WebSocket webSocket;

        public bool IsWsConnected => webSocket?.State == WebSocketState.Open;

        public event Action<SlotStatusUpdate> OnSlotStatusUpdate;
        public event Action<CheckinSuccessData> OnCheckinSuccess;
        public event Action<string> OnDepartVehicle;  // arg = plate
        public event Action<string> OnWsError;
        public event Action OnWsConnected;
        public event Action OnWsDisconnected;

        private void Awake()
        {
            if (Instance != null && Instance != this) { Destroy(gameObject); return; }
            Instance = this;
            if (transform.parent == null)
                DontDestroyOnLoad(gameObject);

            if (config == null)
                config = Resources.Load<ApiConfig>("ApiConfig");
            if (authManager == null)
                authManager = FindObjectOfType<AuthManager>();
        }

        private void Update()
        {
#if !UNITY_WEBGL || UNITY_EDITOR
            webSocket?.DispatchMessageQueue();
#endif
        }
        private void OnDestroy() { DisconnectWebSocket(); }

        // ── Helpers ──
        private string GatewayUrl(string path) => $"{config.gatewayBaseUrl}/api/{path}";
        private string AiUrl(string path) => $"{config.aiServiceUrl}/{path}";
        private ApiResponse<T> MockOk<T>(T data) =>
            new ApiResponse<T> { IsSuccess = true, Data = data, StatusCode = 200 };
        private PaginatedResponse<T> Paginated<T>(List<T> items) =>
            new PaginatedResponse<T> { Count = items.Count, Results = items };

        private const int MAX_LOG_BODY = 500;

        private static string TruncateBody(string body)
        {
            if (string.IsNullOrEmpty(body) || body.Length <= MAX_LOG_BODY) return body;
            return body.Substring(0, MAX_LOG_BODY) + $"…[truncated {body.Length - MAX_LOG_BODY} chars]";
        }

        private UnityWebRequest BuildGet(string url)
        {
            var req = UnityWebRequest.Get(url);
            req.downloadHandler = new DownloadHandlerBuffer();
            return req;
        }

        private UnityWebRequest BuildPost(string url, object body)
        {
            string json = JsonConvert.SerializeObject(body);
            var req = new UnityWebRequest(url, "POST");
            req.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(json));
            req.downloadHandler = new DownloadHandlerBuffer();
            req.SetRequestHeader("Content-Type", "application/json");
            return req;
        }

        private UnityWebRequest BuildPatch(string url, object body)
        {
            string json = body != null ? JsonConvert.SerializeObject(body) : "{}";
            var req = new UnityWebRequest(url, "PATCH");
            req.uploadHandler = new UploadHandlerRaw(Encoding.UTF8.GetBytes(json));
            req.downloadHandler = new DownloadHandlerBuffer();
            req.SetRequestHeader("Content-Type", "application/json");
            return req;
        }

        private IEnumerator SendRequest<T>(UnityWebRequest req, Action<ApiResponse<T>> cb, bool isAi = false)
        {
            authManager.ApplyAuth(req, isAi);

            // Log outgoing request body for AI calls (helps debug verify-slot, check-in etc.)
            if (isAi && req.uploadHandler != null)
            {
                string reqBody = Encoding.UTF8.GetString(req.uploadHandler.data);
                Debug.Log($"[ApiService] REQ→ {req.method} {req.url}\n{TruncateBody(reqBody)}");
            }

            float start = Time.realtimeSinceStartup;
            using (req)
            {
                yield return req.SendWebRequest();
                float elapsed = (Time.realtimeSinceStartup - start) * 1000f;
                int status = (int)req.responseCode;

                if (req.result == UnityWebRequest.Result.Success)
                {
                    Debug.Log($"[ApiService] {req.method} {req.url} → {status} ({elapsed:F0}ms)");
                    if (isAi)
                        Debug.Log($"[ApiService] RSP← {TruncateBody(req.downloadHandler.text)}");
                    var data = JsonConvert.DeserializeObject<T>(req.downloadHandler.text);
                    cb?.Invoke(new ApiResponse<T> { IsSuccess = true, Data = data, StatusCode = status });
                }
                else
                {
                    string errBody = req.downloadHandler?.text ?? req.error;
                    string errMsg = ParseError(errBody, status);
                    string errCode = TryParseErrorCode(errBody);
                    Debug.LogWarning($"[ApiService] {req.method} {req.url} → {status} ({elapsed:F0}ms): {errMsg}");
                    if (isAi && !string.IsNullOrEmpty(errBody))
                        Debug.LogWarning($"[ApiService] ERR← {TruncateBody(errBody)}");
                    cb?.Invoke(new ApiResponse<T>
                    {
                        IsSuccess = false,
                        ErrorMessage = errMsg,
                        ErrorCode = errCode,
                        StatusCode = status
                    });
                }
            }
        }

        private string ParseError(string body, int status)
        {
            if (string.IsNullOrEmpty(body)) return $"HTTP {status}";
            try
            {
                var err = JsonConvert.DeserializeObject<ApiErrorResponse>(body);
                if (err?.Error != null) return err.Error.Message;
            }
            catch { /* ignore */ }
            try
            {
                var d = JsonConvert.DeserializeObject<DjangoErrorResponse>(body);
                if (!string.IsNullOrEmpty(d?.Detail)) return d.Detail;
                if (!string.IsNullOrEmpty(d?.Error)) return d.Error;
            }
            catch { /* ignore */ }
            try
            {
                var g = JsonConvert.DeserializeObject<GatewayErrorResponse>(body);
                if (!string.IsNullOrEmpty(g?.Error)) return $"[{g.Service}] {g.Error}";
            }
            catch { /* ignore */ }
            return $"HTTP {status}: {body}";
        }
        private string TryParseErrorCode(string body)
        {
            if (string.IsNullOrEmpty(body)) return null;
            try
            {
                var err = JsonConvert.DeserializeObject<ApiErrorResponse>(body);
                return err?.Error?.Code;
            }
            catch { return null; }
        }

        // ── Gateway API (Cookie Auth) ──
        public IEnumerator GetParkingLots(Action<ApiResponse<PaginatedResponse<LotData>>> cb)
        {
            if (config.useMockData) { cb?.Invoke(MockOk(Paginated(new List<LotData>()))); yield break; }
            yield return SendRequest(BuildGet(GatewayUrl("parking/lots/")), cb);
        }

        public IEnumerator GetSlots(string lotId, Action<ApiResponse<PaginatedResponse<SlotData>>> cb)
        {
            if (config.useMockData)
            {
                cb?.Invoke(MockOk(Paginated(MockDataProvider.GenerateMockSlots())));
                yield break;
            }
            yield return SendRequest(BuildGet(GatewayUrl($"parking/slots/?lot_id={lotId}&page_size=200")), cb);
        }

        public IEnumerator GetFloors(string lotId, Action<ApiResponse<PaginatedResponse<FloorData>>> cb)
        {
            if (config.useMockData)
            {
                cb?.Invoke(MockOk(Paginated(MockDataProvider.GenerateMockFloors())));
                yield break;
            }
            yield return SendRequest(BuildGet(GatewayUrl($"parking/floors/?lot_id={lotId}")), cb);
        }

        public IEnumerator CreateBooking(BookingCreateRequest data, Action<ApiResponse<BookingCreateResponse>> cb)
        {
            if (config.useMockData)
            {
                var bookingId = System.Guid.NewGuid().ToString();
                var qrData = $"{{\"booking_id\":\"{bookingId}\",\"user_id\":\"{MockIds.USER_1}\"}}";

                // Look up vehicle info for plate/type
                var mockVehicle = MockDataProvider.GenerateMockVehicles()
                    .Find(v => v.Id == data.VehicleId);
                // Look up slot info for code
                var mockSlot = MockDataProvider.GenerateMockSlots()
                    .Find(s => s.Id == data.SlotId);

                var booking = new BookingData
                {
                    Id = bookingId,
                    UserId = MockIds.USER_1,
                    Vehicle = new BookingVehicleInfo
                    {
                        Id = data.VehicleId,
                        LicensePlate = mockVehicle?.LicensePlate ?? "UNKNOWN",
                        VehicleType = mockVehicle?.VehicleType ?? "Car",
                        Name = mockVehicle?.Name
                    },
                    PackageType = data.PackageType ?? "hourly",
                    StartTime = data.StartTime,
                    EndTime = data.EndTime,
                    CarSlot = new BookingSlotInfo
                    {
                        Id = data.SlotId, ZoneId = data.ZoneId,
                        Code = mockSlot?.Code ?? "A-01", IsAvailable = false
                    },
                    Zone = new BookingZoneInfo { Id = data.ZoneId },
                    Floor = new BookingFloorInfo
                    {
                        Id = MockIds.FLOOR_1, Name = "Floor 1", Level = 1,
                        ParkingLotId = MockIds.LOT_1
                    },
                    ParkingLot = new BookingLotInfo
                    {
                        Id = MockIds.LOT_1, Name = "ParkSmart Central",
                        Address = "123 Nguyen Hue"
                    },
                    PaymentType = data.PaymentMethod ?? "on_exit",
                    PaymentStatus = "pending",
                    CheckInStatus = "not_checked_in",
                    Price = "20000.00",
                    QrCodeData = qrData,
                    CreatedAt = DateTime.UtcNow.ToString("o")
                };
                cb?.Invoke(MockOk(new BookingCreateResponse
                {
                    Booking = booking,
                    Message = "Mock booking created",
                    QrCode = qrData
                }));
                yield break;
            }
            yield return SendRequest(BuildPost(GatewayUrl("bookings/"), data), cb);
        }

        public IEnumerator GetBookings(Action<ApiResponse<PaginatedResponse<BookingData>>> cb)
        {
            if (config.useMockData)
            {
                cb?.Invoke(MockOk(Paginated(MockDataProvider.GenerateMockBookings())));
                yield break;
            }
            yield return SendRequest(BuildGet(GatewayUrl("bookings/")), cb);
        }

        public IEnumerator CancelBooking(string bookingId, Action<ApiResponse<object>> cb)
        {
            if (config.useMockData)
            {
                cb?.Invoke(MockOk<object>(new { success = true, message = "Mock booking cancelled" }));
                yield break;
            }
            yield return SendRequest(BuildPost(GatewayUrl($"bookings/{bookingId}/cancel/"), new { }), cb);
        }

        public IEnumerator GetVehicles(Action<ApiResponse<PaginatedResponse<VehicleData>>> cb)
        {
            if (config.useMockData)
            {
                cb?.Invoke(MockOk(Paginated(MockDataProvider.GenerateMockVehicles())));
                yield break;
            }
            yield return SendRequest(BuildGet(GatewayUrl("vehicles/")), cb);
        }

        // ── AI / ESP32 API (X-Gateway-Secret) ──
        public IEnumerator ESP32CheckIn(ESP32CheckInRequest request, Action<ApiResponse<ESP32Response>> cb)
        {
            if (config.useMockData)
            {
                string bookingId = null;
                try
                {
                    var qr = JObject.Parse(request.QrData ?? "{}");
                    bookingId = qr["booking_id"]?.ToString();
                }
                catch { /* ignore parse failure */ }
                bookingId ??= System.Guid.NewGuid().ToString();

                // Look up real booking to get actual slot code
                string slotCode = "A-01";
                var booking = SharedBookingState.Instance?.GetBookingById(bookingId);
                if (booking != null && !string.IsNullOrEmpty(booking.SlotCode))
                    slotCode = booking.SlotCode;

                var details = new JObject
                {
                    ["carSlot"] = new JObject { ["code"] = slotCode }
                };
                cb?.Invoke(MockOk(new ESP32Response
                {
                    Success = true,
                    Event = "checkin_success",
                    BarrierAction = "open",
                    Message = "Mock check-in successful",
                    GateId = request.GateId ?? MockIds.GATE_IN,
                    BookingId = bookingId,
                    Details = details
                }));
                yield break;
            }
            yield return SendRequest(BuildPost(
                AiUrl("ai/parking/esp32/check-in/"), request), cb, true);
        }

        public IEnumerator ESP32CheckOut(ESP32CheckOutRequest request, Action<ApiResponse<ESP32Response>> cb)
        {
            if (config.useMockData)
            {
                cb?.Invoke(MockOk(new ESP32Response
                {
                    Success = true,
                    Event = "checkout_success",
                    BarrierAction = "open",
                    Message = "Mock check-out successful",
                    GateId = request.GateId ?? MockIds.GATE_OUT,
                    AmountDue = 20000f,
                    AmountPaid = 20000f
                }));
                yield break;
            }
            yield return SendRequest(BuildPost(
                AiUrl("ai/parking/esp32/check-out/"), request), cb, true);
        }

        public IEnumerator ESP32VerifySlot(ESP32VerifySlotRequest request, Action<ApiResponse<ESP32Response>> cb)
        {
            if (config.useMockData)
            {
                cb?.Invoke(MockOk(new ESP32Response
                {
                    Success = true,
                    Event = "slot_verified",
                    Message = $"Mock slot {request.SlotCode} verified",
                    GateId = request.GateId
                }));
                yield break;
            }
            yield return SendRequest(BuildPost(
                AiUrl("ai/parking/esp32/verify-slot/"), request), cb, true);
        }

        public IEnumerator ESP32CashPayment(ESP32CashPaymentRequest request, Action<ApiResponse<ESP32Response>> cb)
        {
            if (config.useMockData)
            {
                cb?.Invoke(MockOk(new ESP32Response
                {
                    Success = true,
                    Event = "cash_payment_success",
                    BarrierAction = "open",
                    Message = "Mock cash payment accepted",
                    GateId = request.GateId,
                    BookingId = request.BookingId,
                    AmountDue = 20000f,
                    AmountPaid = 20000f
                }));
                yield break;
            }
            yield return SendRequest(BuildPost(
                AiUrl("ai/parking/esp32/cash-payment/"), request), cb, true);
        }

        public IEnumerator ESP32RegisterDevice(ESP32DeviceRegisterRequest request,
            Action<ApiResponse<ESP32AckResponse>> cb)
        {
            yield return SendRequest(BuildPost(
                AiUrl("ai/parking/esp32/register"), request), cb, true);
        }

        public IEnumerator ESP32Heartbeat(ESP32HeartbeatRequest request,
            Action<ApiResponse<ESP32AckResponse>> cb)
        {
            yield return SendRequest(BuildPost(
                AiUrl("ai/parking/esp32/heartbeat"), request), cb, true);
        }

        public IEnumerator ESP32SendLog(ESP32LogRequest request,
            Action<ApiResponse<ESP32AckResponse>> cb)
        {
            yield return SendRequest(BuildPost(
                AiUrl("ai/parking/esp32/log"), request), cb, true);
        }

        public IEnumerator AIRecognizePlate(byte[] imageBytes, Action<ApiResponse<PlateScanResult>> cb)
        {
            string url = AiUrl("ai/parking/scan-plate/");
            var form = new List<IMultipartFormSection>
            {
                new MultipartFormFileSection("image", imageBytes, "plate.jpg", "image/jpeg")
            };
            using (var req = UnityWebRequest.Post(url, form))
            {
                req.SetRequestHeader("X-Gateway-Secret", config.gatewaySecret);
                yield return req.SendWebRequest();
                int status = (int)req.responseCode;
                if (req.result == UnityWebRequest.Result.Success)
                {
                    var data = JsonConvert.DeserializeObject<PlateScanResult>(req.downloadHandler.text);
                    cb?.Invoke(new ApiResponse<PlateScanResult>
                        { IsSuccess = true, Data = data, StatusCode = status });
                }
                else
                {
                    string errMsg = ParseError(req.downloadHandler?.text, status);
                    cb?.Invoke(new ApiResponse<PlateScanResult>
                        { IsSuccess = false, ErrorMessage = errMsg, StatusCode = status });
                }
            }
        }

        public IEnumerator DetectBanknote(byte[] imageBytes, Action<ApiResponse<BanknoteResult>> cb)
        {
            string url = AiUrl("ai/detect/banknote/?mode=full");
            var form = new List<IMultipartFormSection>
            {
                new MultipartFormFileSection("image", imageBytes, "banknote.jpg", "image/jpeg")
            };
            using (var req = UnityWebRequest.Post(url, form))
            {
                req.SetRequestHeader("X-Gateway-Secret", config.gatewaySecret);
                yield return req.SendWebRequest();
                int status = (int)req.responseCode;
                if (req.result == UnityWebRequest.Result.Success)
                {
                    var data = JsonConvert.DeserializeObject<BanknoteResult>(req.downloadHandler.text);
                    cb?.Invoke(new ApiResponse<BanknoteResult>
                        { IsSuccess = true, Data = data, StatusCode = status });
                }
                else
                {
                    string errMsg = ParseError(req.downloadHandler?.text, status);
                    cb?.Invoke(new ApiResponse<BanknoteResult>
                        { IsSuccess = false, ErrorMessage = errMsg, StatusCode = status });
                }
            }
        }

        public IEnumerator ScanQr(string cameraId, Action<ApiResponse<QrScanResult>> cb)
        {
            string url = AiUrl($"ai/cameras/scan-qr?camera_id={UnityWebRequest.EscapeURL(cameraId)}");
            using (var req = BuildGet(url))
            {
                req.SetRequestHeader("X-Gateway-Secret", config.gatewaySecret);
                yield return req.SendWebRequest();
                int status = (int)req.responseCode;
                if (req.result == UnityWebRequest.Result.Success)
                {
                    var data = JsonConvert.DeserializeObject<QrScanResult>(req.downloadHandler.text);
                    cb?.Invoke(new ApiResponse<QrScanResult>
                        { IsSuccess = true, Data = data, StatusCode = status });
                }
                else
                {
                    cb?.Invoke(new ApiResponse<QrScanResult>
                        { IsSuccess = false, ErrorMessage = req.error, StatusCode = status });
                }
            }
        }

        // ── Virtual Camera Streaming ──
        public IEnumerator PostCameraFrame(string cameraId, byte[] jpegData, Action<bool> cb = null)
        {
            string url = AiUrl("ai/cameras/frame");
            var req = new UnityWebRequest(url, "POST");
            req.uploadHandler = new UploadHandlerRaw(jpegData);
            req.downloadHandler = new DownloadHandlerBuffer();
            req.SetRequestHeader("Content-Type", "image/jpeg");
            req.SetRequestHeader("X-Camera-ID", cameraId);
            req.SetRequestHeader("X-Gateway-Secret", config.gatewaySecret);

            using (req)
            {
                yield return req.SendWebRequest();
                bool ok = req.result == UnityWebRequest.Result.Success;
                if (!ok)
                    Debug.Log($"[ApiService] PostCameraFrame {cameraId} failed: {req.responseCode}"); // use Log not LogWarning — VirtualCamera handles backoff
                cb?.Invoke(ok);
            }
        }

        public IEnumerator PostSlotDetection(string cameraId, object[] slots, Action<bool> cb = null)
        {
            string url = $"{config.realtimeWsUrl.Replace("ws://", "http://").Replace("/ws/parking", "")}/api/broadcast/camera-status/";
            var body = new { camera_id = cameraId, slots = slots };
            string json = JsonConvert.SerializeObject(body);
            var req = new UnityWebRequest(url, "POST");
            req.uploadHandler = new UploadHandlerRaw(System.Text.Encoding.UTF8.GetBytes(json));
            req.downloadHandler = new DownloadHandlerBuffer();
            req.SetRequestHeader("Content-Type", "application/json");
            req.SetRequestHeader("X-Gateway-Secret", config.gatewaySecret);

            using (req)
            {
                yield return req.SendWebRequest();
                bool ok = req.result == UnityWebRequest.Result.Success;
                if (!ok)
                    Debug.LogWarning($"[ApiService] PostSlotDetection {cameraId} failed: {req.responseCode}");
                cb?.Invoke(ok);
            }
        }

        // ── WebSocket ──
        public async void ConnectWebSocket()
        {
            if (webSocket != null) return;
            webSocket = new WebSocket(config.realtimeWsUrl);

            webSocket.OnOpen += () =>
            {
                Debug.Log("[ApiService] WS connected");
                var sub = new WsSubscribeMessage
                {
                    Type = "subscribe",
                    Data = new WsSubscribeData
                    {
                        Channel = $"parking.lot.{config.targetParkingLotId}"
                    }
                };
                webSocket.SendText(JsonConvert.SerializeObject(sub));
                Debug.Log($"[ApiService] WS subscribed to parking.lot.{config.targetParkingLotId}");
                OnWsConnected?.Invoke();
            };
            webSocket.OnMessage += ParseWsMessage;
            webSocket.OnError += (err) =>
            {
                Debug.LogWarning($"[ApiService] WS error: {err}");
                OnWsError?.Invoke(err);
            };
            webSocket.OnClose += (code) =>
            {
                Debug.Log($"[ApiService] WS closed: {code}");
                OnWsDisconnected?.Invoke();
            };

            await webSocket.Connect();
        }

        private void ParseWsMessage(byte[] bytes)
        {
            string json = Encoding.UTF8.GetString(bytes);
            Debug.Log($"[ApiService] WS recv: {json}");
            try
            {
                var obj = JObject.Parse(json);
                string type = obj["type"]?.ToString();
                if (type == "slot.status_update")
                {
                    var update = obj["data"]?.ToObject<SlotStatusUpdate>();
                    if (update != null) OnSlotStatusUpdate?.Invoke(update);
                }
                else if (type == "unity.spawn_vehicle")
                {
                    var data = obj["data"]?.ToObject<CheckinSuccessData>();
                    if (data != null) OnCheckinSuccess?.Invoke(data);
                }
                else if (type == "unity.depart_vehicle")
                {
                    string plate = obj["data"]?["plate"]?.ToString();
                    if (!string.IsNullOrEmpty(plate)) OnDepartVehicle?.Invoke(plate);
                }
            }
            catch (Exception ex)
            {
                Debug.LogWarning($"[ApiService] WS parse error: {ex.Message}");
            }
        }

        public async void DisconnectWebSocket()
        {
            if (webSocket != null && webSocket.State == WebSocketState.Open)
                await webSocket.Close();
            webSocket = null;
        }
    }
}
