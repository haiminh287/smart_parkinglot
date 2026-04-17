using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.Networking;
using ParkingSim.API;
using ParkingSim.Core;
using ParkingSim.Parking;

namespace ParkingSim.IoT
{
    public class ESP32Simulator : MonoBehaviour
    {
        [SerializeField] private ApiService apiService;
        [SerializeField] private ApiConfig config;

        // CHECK-IN — dropdown shows not_checked_in bookings
        private string checkInPlate = "";
        private int selectedBookingIdx = -1;
        private string manualQrData = "";

        /// <summary>
        /// ID của booking user đang chọn trong Check-In dropdown — cho
        /// VehicleQueue biết để spawn đúng xe cho booking đó (không random).
        /// </summary>
        public static string ActiveCheckInBookingId { get; private set; }

        // CHECK-OUT & VERIFY-SLOT — dropdown shows checked_in bookings (separate index)
        private int selectedCheckedInIdx = -1;

        // CASH-PAYMENT
        private string cashPlate = "";

        // MOMO QR popup (shown when check-out returns amountDue > 0)
        private bool showMomoQr;
        private Texture2D momoQrTexture;
        private double momoAmount;
        private string momoBookingId;
        private string momoPlate;
        private Rect momoWindowRect = new Rect(Screen.width / 2 - 200, 120, 400, 560);

        // DEVICE
        private string deviceId = "ESP32-SIM-001";

        // UI
        private string lastResult = "";
        private bool lastSuccess;
        private Vector2 scrollPosition;
        private bool showWindow = true;
        private Rect windowRect = new Rect(Screen.width - 370, 10, 360, 460);
        private bool isProcessing;

        // Detection image (downloaded after check-in / check-out)
        private Texture2D _lastDetectTexture;
        private string _lastDetectImageSavedPath;

        // Auto-poll
        private float syncTimer = 0f;
        private const float SYNC_INTERVAL = 10f;
        private bool isSyncing = false;

        private void Start()
        {
            if (config == null)
                config = Resources.Load<ApiConfig>("ApiConfig");
            if (apiService == null)
                apiService = ApiService.Instance ?? FindObjectOfType<ApiService>();
        }

        private void Update()
        {
            syncTimer += Time.deltaTime;
            if (syncTimer >= SYNC_INTERVAL && !isSyncing && !isProcessing)
            {
                syncTimer = 0f;
                StartCoroutine(DoSyncBookings());
            }
        }

        private void OnGUI()
        {
            if (!showWindow)
            {
                if (GUI.Button(new Rect(Screen.width - 160, 10, 150, 30), "Show ESP32"))
                    showWindow = true;
                return;
            }
            windowRect = GUILayout.Window(101, windowRect, DrawWindow, "\ud83d\udd0c ESP32 Simulator");

            if (showMomoQr)
                momoWindowRect = GUILayout.Window(102, momoWindowRect, DrawMomoQrWindow,
                    "\ud83d\udcb3 Thanh to\u00e1n MoMo");
        }

        private void DrawWindow(int id)
        {
            scrollPosition = GUILayout.BeginScrollView(scrollPosition);

            if (GUILayout.Button("Hide", GUILayout.Width(50)))
            { showWindow = false; }

            DrawResultArea();

            DrawCheckInSection();
            DrawCheckOutSection();
            DrawVerifySlotSection();
            DrawCashPaymentSection();
            DrawDeviceSection();

            GUILayout.EndScrollView();
            GUI.DragWindow();
        }

        // ── CHECK-IN ──
        private void DrawCheckInSection()
        {
            GUILayout.Label("── CHECK-IN ──");

            // Active bookings info
            var bookings = SharedBookingState.Instance != null
                ? SharedBookingState.Instance.GetActiveBookingsForDropdown()
                : new List<(string label, ActiveBooking booking)>();

            if (bookings.Count > 0)
            {
                GUILayout.Label("Active Bookings:");
                string[] labels = new string[bookings.Count];
                for (int i = 0; i < bookings.Count; i++) labels[i] = bookings[i].label;
                selectedBookingIdx = Mathf.Clamp(selectedBookingIdx, 0, bookings.Count - 1);
                selectedBookingIdx = GUILayout.SelectionGrid(selectedBookingIdx, labels, 1);
                var selected = bookings[selectedBookingIdx].booking;
                checkInPlate = selected.LicensePlate ?? "";
                manualQrData = selected.QrCodeData ?? "";
                ActiveCheckInBookingId = selected.BookingId;
            }
            else
            {
                GUILayout.Label("No active bookings — sync or create via web");
            }

            GUI.enabled = !isProcessing && !isSyncing;
            if (GUILayout.Button("🔄 Sync Bookings"))
                StartCoroutine(DoSyncBookings());
            GUI.enabled = true;

            if (bookings.Count > 0)
            {
                GUILayout.Space(4);
                GUILayout.Label($"Plate: {checkInPlate}");
                GUILayout.Label($"QR: {(string.IsNullOrEmpty(manualQrData) ? "(none)" : manualQrData.Substring(0, Mathf.Min(manualQrData.Length, 36)) + "...")}");
            }

            GUI.enabled = !isProcessing;
            if (GUILayout.Button("📥 Check-In"))
                StartCoroutine(DoCheckIn());
            GUI.enabled = true;
        }

        private IEnumerator DoSyncBookings()
        {
            if (isSyncing) yield break;
            isSyncing = true;
            bool done = false;
            ApiResponse<PaginatedResponse<BookingData>> result = null;
            StartCoroutine(apiService.GetBookings(r => { result = r; done = true; }));
            yield return WaitWithTimeout(() => done, 10f, () => { });
            isSyncing = false;
            if (!done) yield break;

            if (result != null && result.IsSuccess && result.Data?.Results != null)
            {
                int added = SharedBookingState.Instance?.SyncFromApi(result.Data.Results) ?? 0;
                if (added > 0)
                    Debug.Log($"[ESP32] Auto-sync: {added} new booking(s) loaded");
            }
        }

        private IEnumerator DoCheckIn()
        {
            // Dùng booking tại selectedBookingIdx TRỰC TIẾP, không lookup bằng plate
            // (plate có thể trùng giữa nhiều booking → GetBookingByPlate trả first match
            // không phải cái user chọn trong dropdown).
            var pendingBookings = SharedBookingState.Instance != null
                ? SharedBookingState.Instance.GetActiveBookingsForDropdown()
                : new List<(string label, ActiveBooking booking)>();

            if (pendingBookings.Count == 0 || selectedBookingIdx < 0 || selectedBookingIdx >= pendingBookings.Count)
            { SetResult(false, "No pending booking selected. Sync hoặc tạo booking mới."); yield break; }

            var activeBooking = pendingBookings[selectedBookingIdx].booking;
            if (activeBooking == null || string.IsNullOrEmpty(activeBooking.BookingId))
            { SetResult(false, "Selected booking không hợp lệ."); yield break; }

            checkInPlate = activeBooking.LicensePlate ?? checkInPlate;
            string qr = !string.IsNullOrEmpty(manualQrData) ? manualQrData : activeBooking.QrCodeData;
            if (string.IsNullOrEmpty(qr))
            { SetResult(false, $"No QR data for booking {activeBooking.BookingId.Substring(0, 8)}. Sync lại."); yield break; }

            ActiveCheckInBookingId = activeBooking.BookingId;
            Debug.Log($"[FLOW] Selected booking → {activeBooking.BookingId.Substring(0, 8)} plate={checkInPlate} slot={activeBooking.SlotCode}");

            isProcessing = true;
            SetResult(false, $"Checking in {checkInPlate}...");
            Debug.Log($"[FLOW] \u25b6 Check-In \u2192 plate={checkInPlate} qr={qr.Substring(0, System.Math.Min(qr.Length, 36))}...");
            bool done = false;
            ApiResponse<ESP32Response> result = null;
            var request = new ESP32CheckInRequest
            {
                GateId = MockIds.GATE_IN,
                QrData = qr
            };
            StartCoroutine(apiService.ESP32CheckIn(request, r => { result = r; done = true; }));
            try
            {
            yield return WaitWithTimeout(() => done, 10f, () => { });

            if (!done)
            { SetResult(false, "Check-in timeout — backend không phản hồi"); yield break; }

            if (result != null && result.IsSuccess && result.Data != null && result.Data.Success)
            {
                string slot = result.Data.Details?["carSlot"]?["code"]?.ToString()
                    ?? activeBooking?.SlotCode ?? "unknown";
                SetResult(true, $"{result.Data.Message}\nAction: {result.Data.BarrierAction}\nSlot: {slot}");
                Debug.Log($"[FLOW] \u2705 Check-In: {checkInPlate} \u2192 slot={slot} barrier={result.Data.BarrierAction}");

                // Use local activeBooking.BookingId first — guaranteed to match SharedBookingState
                // entry. result.Data.BookingId may be formatted differently (dashes) and miss.
                string bookingIdToUpdate = activeBooking?.BookingId ?? result.Data.BookingId;
                if (!string.IsNullOrEmpty(bookingIdToUpdate))
                {
                    SharedBookingState.Instance?.UpdateStatus(bookingIdToUpdate, "checked_in");
                    SharedBookingState.Instance?.UpdateSlotCode(bookingIdToUpdate, slot);
                    Debug.Log($"[FLOW] Local booking {bookingIdToUpdate.Substring(0, System.Math.Min(8, bookingIdToUpdate.Length))} → checked_in");
                }

                // Download detection image if AI returned one
                if (!string.IsNullOrEmpty(result.Data.PlateImageUrl))
                    StartCoroutine(DownloadAndSavePlateImage(result.Data.PlateImageUrl, "checkin"));

                if (ParkingManager.Instance != null)
                {
                    // Release the vehicle already waiting at the gate (spawned by "+Spawn Car")
                    bool released = ParkingManager.Instance.CheckInWaitingVehicle(checkInPlate);

                    if (!released)
                    {
                        // Fallback: no vehicle at gate yet — spawn pre-checked-in
                        ParkingManager.Instance.SpawnVehiclePreCheckedIn(
                            checkInPlate,
                            result.Data.BookingId ?? activeBooking?.BookingId ?? "",
                            qr, slot,
                            activeBooking?.VehicleType ?? "Car");
                    }
                }
            }
            else
            {
                SetResult(false, result?.ErrorMessage ?? result?.Data?.Message ?? "Check-in failed");
            }
            } finally { isProcessing = false; }
        }

        // ── CHECK-OUT ──
        private void DrawCheckOutSection()
        {
            GUILayout.Space(5);
            GUILayout.Label("── CHECK-OUT ──");

            var bookings = SharedBookingState.Instance != null
                ? SharedBookingState.Instance.GetCheckedInBookingsForDropdown()
                : new List<(string label, ActiveBooking booking)>();

            if (bookings.Count > 0)
            {
                GUILayout.Label("Checked-in Bookings:");
                string[] labels = new string[bookings.Count];
                for (int i = 0; i < bookings.Count; i++) labels[i] = bookings[i].label;
                selectedCheckedInIdx = Mathf.Clamp(selectedCheckedInIdx < 0 ? 0 : selectedCheckedInIdx, 0, bookings.Count - 1);
                selectedCheckedInIdx = GUILayout.SelectionGrid(selectedCheckedInIdx, labels, 1);
                var bk = bookings[selectedCheckedInIdx].booking;
                GUILayout.Label($"Plate: {bk.LicensePlate ?? "(unknown)"}");
            }
            else
            {
                GUILayout.Label("No checked-in bookings");
            }

            GUI.enabled = !isProcessing && bookings.Count > 0;
            if (GUILayout.Button("\ud83d\udce4 Check-Out"))
                StartCoroutine(DoCheckOut());
            GUI.enabled = true;
        }

        private IEnumerator DoCheckOut()
        {
            var bookings = SharedBookingState.Instance != null
                ? SharedBookingState.Instance.GetCheckedInBookingsForDropdown()
                : new List<(string label, ActiveBooking booking)>();

            if (bookings.Count == 0 || selectedCheckedInIdx < 0 || selectedCheckedInIdx >= bookings.Count)
            { SetResult(false, "No checked-in booking selected."); yield break; }

            var booking = bookings[selectedCheckedInIdx].booking;

            if (string.IsNullOrEmpty(booking.QrCodeData))
            { SetResult(false, $"No QR data for plate {booking.LicensePlate}."); yield break; }

            isProcessing = true;
            Debug.Log($"[FLOW] \u25b6 Check-Out \u2192 plate={booking.LicensePlate} id={booking.BookingId}");

            bool done = false;
            ApiResponse<ESP32Response> result = null;
            var request = new ESP32CheckOutRequest
            {
                GateId = MockIds.GATE_OUT,
                QrData = booking.QrCodeData
            };
            StartCoroutine(apiService.ESP32CheckOut(request, r => { result = r; done = true; }));
            try
            {
            yield return WaitWithTimeout(() => done, 10f, () => { });

            if (!done)
            { SetResult(false, "Check-out timeout — backend không phản hồi"); yield break; }

            if (result.IsSuccess && result.Data != null)
            {
                bool ok = result.Data.Success;
                string msg = result.Data.Message ?? "Check-out response received";
                if (result.Data.AmountDue > 0)
                {
                    msg += $"\n\ud83d\udcb0 C\u00f2n n\u1ee3: {result.Data.AmountDue:F0}\u0111 \u2014 Qu\u00e9t QR MoMo \u0111\u1ec3 thanh to\u00e1n";
                    momoAmount = (double)(result.Data.AmountDue ?? 0f);
                    momoBookingId = result.Data.BookingId ?? booking.BookingId;
                    momoPlate = booking.LicensePlate;
                    StartCoroutine(DownloadMomoQr());
                }
                SetResult(ok, msg);
                Debug.Log($"[FLOW] {(ok ? "\u2705" : "\u274c")} Check-Out: {result.Data.Event} | amountDue={result.Data.AmountDue}");
                if (ok && result.Data.BookingId != null && result.Data.AmountDue <= 0)
                    SharedBookingState.Instance?.RemoveBooking(result.Data.BookingId);
                if (ok && !string.IsNullOrEmpty(result.Data.PlateImageUrl))
                    StartCoroutine(DownloadAndSavePlateImage(result.Data.PlateImageUrl, "checkout"));
            }
            else
            {
                SetResult(false, result.ErrorMessage ?? "Check-out failed");
            }
            } finally { isProcessing = false; }
        }

        // ── VERIFY-SLOT ──
        private void DrawVerifySlotSection()
        {
            GUILayout.Space(5);
            GUILayout.Label("── VERIFY SLOT ──");

            var bookings = SharedBookingState.Instance != null
                ? SharedBookingState.Instance.GetCheckedInBookingsForDropdown()
                : new List<(string label, ActiveBooking booking)>();

            if (bookings.Count > 0)
            {
                selectedCheckedInIdx = Mathf.Clamp(selectedCheckedInIdx < 0 ? 0 : selectedCheckedInIdx, 0, bookings.Count - 1);
                var bk = bookings[selectedCheckedInIdx].booking;
                GUILayout.Label($"Slot: {bk.SlotCode ?? "(unknown)"}");
                GUILayout.Label($"Zone: {(string.IsNullOrEmpty(bk.ZoneId) ? MockIds.ZONE_CAR_PAINTED_F1 : bk.ZoneId).Substring(0, 8)}...");
            }
            else
            {
                GUILayout.Label("No checked-in booking — Check-In first");
            }

            GUI.enabled = !isProcessing && bookings.Count > 0;
            if (GUILayout.Button("\ud83d\udd0d Verify Slot"))
                StartCoroutine(DoVerifySlot());
            GUI.enabled = true;
        }

        private IEnumerator DoVerifySlot()
        {
            var bookings = SharedBookingState.Instance != null
                ? SharedBookingState.Instance.GetCheckedInBookingsForDropdown()
                : new List<(string label, ActiveBooking booking)>();

            if (bookings.Count == 0 || selectedCheckedInIdx < 0 || selectedCheckedInIdx >= bookings.Count)
            { SetResult(false, "No checked-in booking selected."); Debug.LogWarning("[FLOW] ❌ Verify Slot blocked: no checked-in booking"); yield break; }

            var booking = bookings[selectedCheckedInIdx].booking;

            if (string.IsNullOrEmpty(booking.SlotCode))
            { SetResult(false, "Selected booking has no slot — Check-In first."); Debug.LogWarning($"[FLOW] ❌ Verify Slot blocked: SlotCode empty for booking={booking.BookingId}"); yield break; }

            if (string.IsNullOrEmpty(booking.QrCodeData))
            { SetResult(false, "No QR data for selected booking. Sync bookings first."); Debug.LogWarning($"[FLOW] ❌ Verify Slot blocked: QrCodeData empty for booking={booking.BookingId}"); yield break; }

            isProcessing = true;
            Debug.Log($"[FLOW] \u25b6 Verify Slot \u2192 slot={booking.SlotCode} zone={booking.ZoneId} plate={booking.LicensePlate}");

            bool done = false;
            ApiResponse<ESP32Response> result = null;
            var request = new ESP32VerifySlotRequest
            {
                SlotCode = booking.SlotCode,
                ZoneId = string.IsNullOrEmpty(booking.ZoneId) ? MockIds.ZONE_CAR_PAINTED_F1 : booking.ZoneId,
                GateId = MockIds.GATE_IN,
                QrData = booking.QrCodeData
            };
            StartCoroutine(apiService.ESP32VerifySlot(request, r => { result = r; done = true; }));
            try
            {
            yield return WaitWithTimeout(() => done, 10f, () => { });

            if (!done)
            { SetResult(false, "Verify timeout — backend không phản hồi"); yield break; }

            bool ok = result.IsSuccess && result.Data?.Success == true;
            SetResult(ok, result.Data?.Message ?? result.ErrorMessage ?? "Verify failed");
            Debug.Log($"[FLOW] {(ok ? "\u2705" : "\u274c")} Verify Slot: {result.Data?.Event} | {result.Data?.Message}");

            if (ok)
            {
                ParkingManager.Instance?.OpenSlotBarrier(booking.SlotCode);
            }
            } finally { isProcessing = false; }
        }

        // ── CASH PAYMENT ──
        private void DrawCashPaymentSection()
        {
            GUILayout.Space(5);
            GUILayout.Label("── CASH PAYMENT ──");
            GUILayout.BeginHorizontal();
            GUILayout.Label("Plate:", GUILayout.Width(50));
            cashPlate = GUILayout.TextField(cashPlate);
            GUILayout.EndHorizontal();

            GUI.enabled = !isProcessing;
            if (GUILayout.Button("\ud83d\udcb2 Cash Payment"))
                StartCoroutine(DoCashPayment());
            GUI.enabled = true;
        }

        private IEnumerator DoCashPayment()
        {
            if (string.IsNullOrEmpty(cashPlate))
            { SetResult(false, "Plate number required"); yield break; }

            var booking = SharedBookingState.Instance?.GetBookingByPlate(cashPlate);
            if (booking == null)
            { SetResult(false, $"No active booking for plate {cashPlate}"); yield break; }

            isProcessing = true;
            bool done = false;
            ApiResponse<ESP32Response> result = null;
            var request = new ESP32CashPaymentRequest
            {
                BookingId = booking.BookingId,
                GateId = MockIds.GATE_OUT
            };
            StartCoroutine(apiService.ESP32CashPayment(request,
                r => { result = r; done = true; }));
            yield return WaitWithTimeout(() => done, 10f, () => { });
            isProcessing = false;

            if (!done)
            { SetResult(false, "Cash payment timeout — backend không phản hồi"); yield break; }

            SetResult(result.IsSuccess && result.Data?.Success == true,
                result.Data?.Message ?? result.ErrorMessage ?? "Payment failed");
        }

        // ── MOMO QR POPUP (triggered when DoCheckOut returns AmountDue > 0) ──
        private IEnumerator DownloadMomoQr()
        {
            // Build a MoMo-style payload. For demo we use text so any QR scanner can read it;
            // MoMo production uses a deep-link or VietQR string — same pipeline otherwise.
            string shortId = string.IsNullOrEmpty(momoBookingId)
                ? "N/A" : momoBookingId.Substring(0, System.Math.Min(8, momoBookingId.Length));
            string payload = $"MOMO|ParkSmart|{momoAmount:F0}VND|BK-{shortId}|{momoPlate}";
            string qrUrl = $"https://api.qrserver.com/v1/create-qr-code/?data={UnityWebRequest.EscapeURL(payload)}&size=340x340&margin=4";

            using var req = UnityWebRequestTexture.GetTexture(qrUrl);
            yield return req.SendWebRequest();
            if (req.result == UnityWebRequest.Result.Success)
            {
                if (momoQrTexture != null) Destroy(momoQrTexture);
                momoQrTexture = DownloadHandlerTexture.GetContent(req);
                showMomoQr = true;
                Debug.Log($"[FLOW] \ud83d\udcb3 MoMo QR sinh cho {momoAmount:F0}\u0111 — booking {shortId}");
            }
            else
            {
                Debug.LogWarning($"[FLOW] Kh\u00f4ng t\u1ea3i \u0111\u01b0\u1ee3c QR MoMo: {req.error}");
                SetResult(false, "Không tải được QR MoMo — dùng Cash Payment thủ công");
            }
        }

        private void DrawMomoQrWindow(int id)
        {
            var headerStyle = new GUIStyle(GUI.skin.label)
            { fontSize = 14, fontStyle = FontStyle.Bold, alignment = TextAnchor.MiddleCenter };
            var amountStyle = new GUIStyle(GUI.skin.label)
            { fontSize = 22, fontStyle = FontStyle.Bold, alignment = TextAnchor.MiddleCenter };
            amountStyle.normal.textColor = new Color(1f, 0.3f, 0.5f);

            GUILayout.Space(6);
            GUILayout.Label("Quét QR bằng app MoMo để thanh toán", headerStyle);
            GUILayout.Label($"{momoAmount:N0}đ", amountStyle, GUILayout.Height(38));

            if (!string.IsNullOrEmpty(momoPlate))
                GUILayout.Label($"Biển số: {momoPlate}", headerStyle);
            if (!string.IsNullOrEmpty(momoBookingId))
            {
                string shortId = momoBookingId.Substring(0, System.Math.Min(8, momoBookingId.Length));
                GUILayout.Label($"Mã đơn: BK-{shortId}", headerStyle);
            }

            GUILayout.Space(6);
            if (momoQrTexture != null)
            {
                GUILayout.BeginHorizontal();
                GUILayout.FlexibleSpace();
                GUILayout.Box(momoQrTexture, GUILayout.Width(340), GUILayout.Height(340));
                GUILayout.FlexibleSpace();
                GUILayout.EndHorizontal();
            }
            else
            {
                GUILayout.Label("Đang tải QR…", headerStyle, GUILayout.Height(340));
            }

            GUILayout.Space(6);
            GUI.enabled = !isProcessing;
            if (GUILayout.Button("\u2705 Đã thanh toán", GUILayout.Height(32)))
                StartCoroutine(ConfirmMomoPayment());
            GUI.enabled = true;

            if (GUILayout.Button("Đóng", GUILayout.Height(26)))
                CloseMomoQr();

            GUI.DragWindow();
        }

        private IEnumerator ConfirmMomoPayment()
        {
            if (string.IsNullOrEmpty(momoBookingId))
            { SetResult(false, "Thiếu bookingId"); yield break; }

            isProcessing = true;
            bool done = false;
            ApiResponse<ESP32Response> result = null;
            var request = new ESP32CashPaymentRequest
            {
                BookingId = momoBookingId,
                GateId = MockIds.GATE_OUT
            };
            StartCoroutine(apiService.ESP32CashPayment(request, r => { result = r; done = true; }));
            yield return WaitWithTimeout(() => done, 10f, () => { });
            isProcessing = false;

            if (!done) { SetResult(false, "Timeout xác nhận thanh toán"); yield break; }

            bool ok = result.IsSuccess && result.Data?.Success == true;
            SetResult(ok, ok
                ? $"\u2705 Thanh toán MoMo thành công — {momoAmount:N0}đ. Đang mở cổng…"
                : (result.Data?.Message ?? "Thanh toán thất bại"));

            if (ok)
            {
                string paidBookingId = momoBookingId;
                CloseMomoQr();

                // Auto-trigger check-out lần nữa để backend mở barrier (amountDue giờ = 0)
                var bks = SharedBookingState.Instance?.GetCheckedInBookingsForDropdown();
                if (bks != null)
                {
                    int idx = bks.FindIndex(b => b.booking.BookingId == paidBookingId);
                    if (idx >= 0)
                    {
                        selectedCheckedInIdx = idx;
                        yield return new WaitForSeconds(0.5f);
                        StartCoroutine(DoCheckOut());
                    }
                }
            }
        }

        private void CloseMomoQr()
        {
            showMomoQr = false;
            if (momoQrTexture != null) { Destroy(momoQrTexture); momoQrTexture = null; }
        }

        // ── DEVICE MANAGEMENT ──
        private void DrawDeviceSection()
        {
            GUILayout.Space(5);
            GUILayout.Label("── DEVICE ──");
            GUILayout.BeginHorizontal();
            GUILayout.Label("ID:", GUILayout.Width(50));
            deviceId = GUILayout.TextField(deviceId);
            GUILayout.EndHorizontal();

            GUI.enabled = !isProcessing;
            GUILayout.BeginHorizontal();
            if (GUILayout.Button("Register"))
                StartCoroutine(DoRegisterDevice());
            if (GUILayout.Button("Heartbeat"))
                StartCoroutine(DoHeartbeat());
            if (GUILayout.Button("Log"))
                StartCoroutine(DoSendLog());
            GUILayout.EndHorizontal();
            GUI.enabled = true;
        }

        private IEnumerator DoRegisterDevice()
        {
            isProcessing = true;
            bool done = false;
            ApiResponse<ESP32AckResponse> result = null;
            var request = new ESP32DeviceRegisterRequest
            {
                DeviceId = deviceId, Ip = "192.168.1.100", Firmware = "1.0.0"
            };
            StartCoroutine(apiService.ESP32RegisterDevice(request,
                r => { result = r; done = true; }));
            yield return WaitWithTimeout(() => done, 10f, () => { });
            isProcessing = false;
            if (!done) { SetResult(false, "Register timeout"); yield break; }
            SetResult(result.IsSuccess && result.Data?.Success == true,
                result.Data?.Message ?? result.ErrorMessage ?? "Register failed");
        }

        private IEnumerator DoHeartbeat()
        {
            isProcessing = true;
            bool done = false;
            ApiResponse<ESP32AckResponse> result = null;
            var request = new ESP32HeartbeatRequest
            {
                DeviceId = deviceId, Status = "ready", WifiRssi = -45
            };
            StartCoroutine(apiService.ESP32Heartbeat(request,
                r => { result = r; done = true; }));
            yield return WaitWithTimeout(() => done, 10f, () => { });
            isProcessing = false;
            if (!done) { SetResult(false, "Heartbeat timeout"); yield break; }
            SetResult(result.IsSuccess && result.Data?.Success == true,
                result.Data?.Message ?? result.ErrorMessage ?? "Heartbeat failed");
        }

        private IEnumerator DoSendLog()
        {
            isProcessing = true;
            bool done = false;
            ApiResponse<ESP32AckResponse> result = null;
            var request = new ESP32LogRequest
            {
                DeviceId = deviceId, Level = "info", Message = "Simulator log test"
            };
            StartCoroutine(apiService.ESP32SendLog(request,
                r => { result = r; done = true; }));
            yield return WaitWithTimeout(() => done, 10f, () => { });
            isProcessing = false;
            if (!done) { SetResult(false, "Log timeout"); yield break; }
            SetResult(result.IsSuccess && result.Data?.Success == true,
                result.Data?.Message ?? result.ErrorMessage ?? "Log failed");
        }

        // ── Result Display ──
        private void DrawResultArea()
        {
            GUILayout.Space(10);
            GUILayout.Label("── RESULT ──");
            var prevColor = GUI.contentColor;
            GUI.contentColor = lastSuccess ? Color.green : Color.red;
            GUILayout.Label(lastResult, GUILayout.MaxWidth(340));
            GUI.contentColor = prevColor;

            // Show detection image thumbnail if available
            if (_lastDetectTexture != null)
            {
                float aspect = (float)_lastDetectTexture.width / Mathf.Max(1, _lastDetectTexture.height);
                float thumbW = 320f;
                float thumbH = thumbW / aspect;
                GUILayout.Label("Detection image:");
                GUILayout.Label(new GUIContent(_lastDetectTexture),
                    GUILayout.Width(thumbW), GUILayout.Height(thumbH));
                GUILayout.Label($"Saved: {_lastDetectImageSavedPath}", GUILayout.MaxWidth(340));
            }
        }

        // ── Image Download ──
        private IEnumerator DownloadAndSavePlateImage(string relativeUrl, string label)
        {
            string fullUrl = config.aiServiceUrl.TrimEnd('/') + relativeUrl;
            Debug.Log($"[FLOW] \ud83d\uddbc Downloading detection image: {fullUrl}");

            using var req = UnityWebRequestTexture.GetTexture(fullUrl);
            yield return req.SendWebRequest();

            if (req.result != UnityWebRequest.Result.Success)
            {
                Debug.LogWarning($"[ESP32] Image download failed: {req.error}");
                yield break;
            }

            var tex = DownloadHandlerTexture.GetContent(req);
            if (tex == null) yield break;

            // Save to central Project_Main/logs/unity/
#if UNITY_EDITOR
            string saveDir = Path.GetFullPath(Path.Combine(Application.dataPath, "..", "..", "logs", "unity"));
            Directory.CreateDirectory(saveDir);
#else
            string saveDir = Application.persistentDataPath;
#endif
            string filename = $"detect_{label}_{DateTime.Now:yyyyMMdd_HHmmss}.jpg";
            string savePath = Path.Combine(saveDir, filename);
            try
            {
                File.WriteAllBytes(savePath, tex.EncodeToJPG());
                Debug.Log($"[FLOW] \ud83d\uddbc Detection image saved \u2192 {savePath}");
                FlowLogger.Instance?.WriteRaw($"[IMAGE] {label.ToUpper()} capture: {savePath}");
            }
            catch (Exception e)
            {
                Debug.LogWarning($"[ESP32] Image save failed: {e.Message}");
            }

            // Destroy previous texture to avoid memory leak
            if (_lastDetectTexture != null)
                Destroy(_lastDetectTexture);

            _lastDetectTexture = tex;
            _lastDetectImageSavedPath = savePath;
        }

        private void SetResult(bool success, string message)
        {
            lastSuccess = success;
            lastResult = $"[{DateTime.Now:HH:mm:ss}] {(success ? "\u2705" : "\u274c")} {message}";
        }

        private IEnumerator WaitWithTimeout(System.Func<bool> condition, float timeoutSec, System.Action onTimeout)
        {
            float elapsed = 0f;
            while (!condition() && elapsed < timeoutSec)
            {
                elapsed += Time.deltaTime;
                yield return null;
            }
            if (!condition()) onTimeout?.Invoke();
        }

        public void SetPlateFromCamera(string plateText)
        {
            checkInPlate = plateText;
            Debug.Log($"[ESP32] Plate set from camera: {plateText}");
        }
    }
}
