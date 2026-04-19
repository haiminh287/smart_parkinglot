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

        // CHECK-OUT & VERIFY-SLOT reuse selectedBookingIdx (merged dropdown)

        // CASH-PAYMENT
        private string cashPlate = "";

        // PAYMENT popup (MoMo QR + Cash banknote AI) khi check-out amountDue > 0
        private bool showMomoQr;
        private Texture2D momoQrTexture;
        private double momoAmount;
        private string momoBookingId;
        private string momoPlate;
        private Rect momoWindowRect = new Rect(Screen.width / 2 - 260, 40, 520, 820);

        // Cash banknote AI detection state (tích luỹ tổng qua mỗi lần detect)
        private double cashAcceptedTotal = 0;
        private readonly List<string> cashHistory = new List<string>();
        private bool cashDetecting = false;
        private Vector2 cashScroll;
        private Texture2D lastBanknoteTexture;   // Ảnh tờ tiền vừa gửi AI
        private string lastBanknoteLabel;        // "Bấm 10k → AI: 10k (conf 92%)"

        // Banknote dataset root — Editor reads trực tiếp từ disk
        private static readonly string[] BANKNOTE_DENOMS = { "1000", "2000", "5000", "10000", "20000", "50000", "100000", "200000", "500000" };

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

            // Subscribe WS: khi ESP32 vật lý check-out gặp awaiting_payment,
            // backend broadcast → mở popup MoMo QR + cash detection tại Unity.
            if (apiService != null)
                apiService.OnAwaitingPayment += HandleAwaitingPayment;
        }

        private void OnDestroy()
        {
            if (apiService != null)
                apiService.OnAwaitingPayment -= HandleAwaitingPayment;
        }

        private void HandleAwaitingPayment(string bookingId, string plate, double amountDue)
        {
            if (amountDue <= 0 || string.IsNullOrEmpty(bookingId)) return;
            Debug.Log($"[FLOW] 💳 WS awaiting_payment → plate={plate} amount={amountDue:N0}đ booking={bookingId}");
            momoAmount = amountDue;
            momoBookingId = bookingId;
            momoPlate = plate ?? "";
            cashAcceptedTotal = 0;
            cashHistory.Clear();
            StartCoroutine(DownloadMomoQr());
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

        // ── BOOKINGS (single dropdown: ⏳ pending + ✓ checked-in) ──
        private void DrawCheckInSection()
        {
            GUILayout.Label("── ACTIVE BOOKINGS ──");

            var bookings = SharedBookingState.Instance != null
                ? SharedBookingState.Instance.GetAllActiveForDropdown()
                : new List<(string label, ActiveBooking booking)>();

            ActiveBooking selected = null;
            if (bookings.Count > 0)
            {
                string[] labels = new string[bookings.Count];
                for (int i = 0; i < bookings.Count; i++) labels[i] = bookings[i].label;
                selectedBookingIdx = Mathf.Clamp(selectedBookingIdx < 0 ? 0 : selectedBookingIdx, 0, bookings.Count - 1);
                selectedBookingIdx = GUILayout.SelectionGrid(selectedBookingIdx, labels, 1);
                selected = bookings[selectedBookingIdx].booking;
                checkInPlate = selected.LicensePlate ?? "";
                manualQrData = selected.QrCodeData ?? "";
                ActiveCheckInBookingId = selected.BookingId;
            }
            else
            {
                GUILayout.Label("Chưa có booking — Sync hoặc tạo từ web");
            }

            GUI.enabled = !isProcessing && !isSyncing;
            if (GUILayout.Button("🔄 Sync Bookings"))
                StartCoroutine(DoSyncBookings());
            GUI.enabled = true;

            if (selected != null)
            {
                GUILayout.Space(4);
                GUILayout.Label($"Plate: {checkInPlate} | Slot: {selected.SlotCode} | Status: {selected.CheckInStatus}");

                bool notCheckedIn = selected.CheckInStatus == "not_checked_in";
                GUI.enabled = !isProcessing && notCheckedIn;
                if (GUILayout.Button(notCheckedIn ? "📥 Check-In" : "📥 Check-In (đã check-in)"))
                    StartCoroutine(DoCheckIn());
                GUI.enabled = true;
            }
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
            // Single source of truth: lấy booking tại selectedBookingIdx của merged list
            var all = SharedBookingState.Instance != null
                ? SharedBookingState.Instance.GetAllActiveForDropdown()
                : new List<(string label, ActiveBooking booking)>();

            if (all.Count == 0 || selectedBookingIdx < 0 || selectedBookingIdx >= all.Count)
            { SetResult(false, "No booking selected. Sync hoặc tạo booking mới."); yield break; }

            var activeBooking = all[selectedBookingIdx].booking;
            if (activeBooking == null || string.IsNullOrEmpty(activeBooking.BookingId))
            { SetResult(false, "Selected booking không hợp lệ."); yield break; }
            if (activeBooking.CheckInStatus != "not_checked_in")
            { SetResult(false, $"Booking đã ở trạng thái {activeBooking.CheckInStatus}, không thể check-in lại."); yield break; }

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

            var selected = GetSelectedBooking();
            if (selected == null)
            {
                GUILayout.Label("Chọn booking ở trên");
            }
            else
            {
                bool isCheckedIn = selected.CheckInStatus == "checked_in";
                GUILayout.Label($"Plate: {selected.LicensePlate ?? "(unknown)"} | Status: {selected.CheckInStatus}");
                GUI.enabled = !isProcessing && isCheckedIn;
                if (GUILayout.Button(isCheckedIn ? "\ud83d\udce4 Check-Out" : "\ud83d\udce4 Check-Out (cần checked-in)"))
                    StartCoroutine(DoCheckOut());
                GUI.enabled = true;
            }
        }

        /// <summary>Lấy booking đang được chọn trong merged dropdown.</summary>
        private ActiveBooking GetSelectedBooking()
        {
            var all = SharedBookingState.Instance?.GetAllActiveForDropdown();
            if (all == null || all.Count == 0 || selectedBookingIdx < 0 || selectedBookingIdx >= all.Count)
                return null;
            return all[selectedBookingIdx].booking;
        }

        private IEnumerator DoCheckOut()
        {
            var booking = GetSelectedBooking();
            if (booking == null)
            { SetResult(false, "No booking selected."); yield break; }
            if (booking.CheckInStatus != "checked_in")
            { SetResult(false, $"Booking {booking.CheckInStatus} — không thể check-out."); yield break; }

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

            var selected = GetSelectedBooking();
            if (selected == null)
            {
                GUILayout.Label("Chọn booking ở trên");
            }
            else
            {
                bool isCheckedIn = selected.CheckInStatus == "checked_in";
                GUILayout.Label($"Slot: {selected.SlotCode ?? "(unknown)"} | Status: {selected.CheckInStatus}");
                string zone = string.IsNullOrEmpty(selected.ZoneId) ? MockIds.ZONE_CAR_PAINTED_F1 : selected.ZoneId;
                GUILayout.Label($"Zone: {zone.Substring(0, System.Math.Min(8, zone.Length))}...");
                GUI.enabled = !isProcessing && isCheckedIn;
                if (GUILayout.Button(isCheckedIn ? "\ud83d\udd0d Verify Slot" : "\ud83d\udd0d Verify Slot (cần checked-in)"))
                    StartCoroutine(DoVerifySlot());
                GUI.enabled = true;
            }
        }

        private IEnumerator DoVerifySlot()
        {
            var booking = GetSelectedBooking();
            if (booking == null)
            { SetResult(false, "No booking selected."); yield break; }
            if (booking.CheckInStatus != "checked_in")
            { SetResult(false, $"Booking {booking.CheckInStatus} — check-in trước khi verify."); yield break; }

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
                Debug.Log($"[FLOW] \ud83d\udcb3 MoMo QR sinh cho {momoAmount:F0}\u0111 — booking {shortId}");
            }
            else
            {
                Debug.LogWarning($"[FLOW] Kh\u00f4ng t\u1ea3i \u0111\u01b0\u1ee3c QR MoMo: {req.error}");
            }
            // Reset cash state + mở popup
            cashAcceptedTotal = 0;
            cashHistory.Clear();
            showMomoQr = true;
        }

        private void DrawMomoQrWindow(int id)
        {
            var headerStyle = new GUIStyle(GUI.skin.label)
            { fontSize = 13, fontStyle = FontStyle.Bold, alignment = TextAnchor.MiddleCenter };
            var amountStyle = new GUIStyle(GUI.skin.label)
            { fontSize = 20, fontStyle = FontStyle.Bold, alignment = TextAnchor.MiddleCenter };
            amountStyle.normal.textColor = new Color(1f, 0.3f, 0.5f);
            var okStyle = new GUIStyle(GUI.skin.label)
            { fontSize = 14, fontStyle = FontStyle.Bold, alignment = TextAnchor.MiddleCenter };
            okStyle.normal.textColor = cashAcceptedTotal >= momoAmount ? new Color(0.3f, 0.9f, 0.4f) : new Color(1f, 0.8f, 0.3f);

            GUILayout.Space(4);
            GUILayout.Label($"Cần thanh toán: {momoAmount:N0}đ", amountStyle, GUILayout.Height(30));
            string shortId = string.IsNullOrEmpty(momoBookingId) ? "?" : momoBookingId.Substring(0, System.Math.Min(8, momoBookingId.Length));
            GUILayout.Label($"Biển số: {momoPlate} · Mã đơn: BK-{shortId}", headerStyle);

            GUILayout.Space(6);
            GUILayout.Label("QR MoMo (quét app MoMo để chuyển khoản):", headerStyle);
            if (momoQrTexture != null)
            {
                GUILayout.BeginHorizontal();
                GUILayout.FlexibleSpace();
                GUILayout.Box(momoQrTexture, GUILayout.Width(200), GUILayout.Height(200));
                GUILayout.FlexibleSpace();
                GUILayout.EndHorizontal();
            }
            else
            {
                GUILayout.Label("Đang tải QR…", headerStyle, GUILayout.Height(24));
            }

            GUILayout.Space(6);
            GUILayout.Label("— HOẶC đưa tiền mặt (AI detect từng tờ) —", headerStyle);
            GUI.enabled = !cashDetecting && !isProcessing;
            // 9 nút: 3 hàng × 3 cột (1k/2k/5k, 10k/20k/50k, 100k/200k/500k)
            for (int row = 0; row < 3; row++)
            {
                GUILayout.BeginHorizontal();
                for (int col = 0; col < 3; col++)
                {
                    int i = row * 3 + col;
                    if (i >= BANKNOTE_DENOMS.Length) continue;
                    string d = BANKNOTE_DENOMS[i];
                    if (GUILayout.Button($"{int.Parse(d) / 1000}k", GUILayout.Height(28)))
                        StartCoroutine(DetectOneBanknote(d));
                }
                GUILayout.EndHorizontal();
            }
            GUI.enabled = true;

            GUILayout.Space(4);
            GUILayout.Label($"AI đã nhận: {cashAcceptedTotal:N0}đ / {momoAmount:N0}đ", okStyle);

            // Thối tiền khi quá
            double change = cashAcceptedTotal - momoAmount;
            if (change > 0)
            {
                var changeStyle = new GUIStyle(GUI.skin.label) { fontSize = 14, fontStyle = FontStyle.Bold, alignment = TextAnchor.MiddleCenter };
                changeStyle.normal.textColor = new Color(0.3f, 0.9f, 1f);
                GUILayout.Label($"💰 Thối lại: {change:N0}đ", changeStyle);
            }
            else if (cashAcceptedTotal > 0 && cashAcceptedTotal < momoAmount)
            {
                var shortStyle = new GUIStyle(GUI.skin.label) { fontSize = 13, fontStyle = FontStyle.Bold, alignment = TextAnchor.MiddleCenter };
                shortStyle.normal.textColor = new Color(1f, 0.5f, 0.3f);
                GUILayout.Label($"⚠️ Còn thiếu: {(momoAmount - cashAcceptedTotal):N0}đ", shortStyle);
            }

            // Preview ảnh vừa detect + kết quả AI để user thấy flow thực sự
            if (lastBanknoteTexture != null)
            {
                GUILayout.BeginHorizontal();
                GUILayout.FlexibleSpace();
                GUILayout.Box(lastBanknoteTexture, GUILayout.Width(160), GUILayout.Height(80));
                GUILayout.FlexibleSpace();
                GUILayout.EndHorizontal();
                if (!string.IsNullOrEmpty(lastBanknoteLabel))
                    GUILayout.Label(lastBanknoteLabel, headerStyle);
            }

            cashScroll = GUILayout.BeginScrollView(cashScroll, GUILayout.Height(80));
            foreach (var line in cashHistory)
                GUILayout.Label(line);
            GUILayout.EndScrollView();

            GUILayout.Space(4);
            bool canConfirm = cashAcceptedTotal >= momoAmount && !isProcessing;
            GUI.enabled = canConfirm;
            string payLabel = canConfirm
                ? $"\u2705 Xác nhận thanh toán ({cashAcceptedTotal:N0}đ)"
                : $"\u274c Chưa đủ (còn thiếu {System.Math.Max(0, momoAmount - cashAcceptedTotal):N0}đ)";
            if (GUILayout.Button(payLabel, GUILayout.Height(32)))
                StartCoroutine(ConfirmMomoPayment());
            GUI.enabled = true;

            if (GUILayout.Button("Đóng", GUILayout.Height(24)))
                CloseMomoQr();

            GUI.DragWindow();
        }

        // ── Cash banknote AI detection ──
        private static string BanknoteDatasetRoot =>
            System.IO.Path.Combine(Application.dataPath, "..", "..",
                "backend-microservices", "ai-service-fastapi", "ml",
                "datasets", "banknote_v1", "real");

        private byte[] LoadRandomBanknoteBytes(string denomFolder)
        {
            try
            {
                string dir = System.IO.Path.Combine(BanknoteDatasetRoot, denomFolder);
                if (!System.IO.Directory.Exists(dir)) return null;
                var files = System.IO.Directory.GetFiles(dir, "*.jpg");
                if (files.Length == 0) files = System.IO.Directory.GetFiles(dir, "*.jpeg");
                if (files.Length == 0) files = System.IO.Directory.GetFiles(dir, "*.png");
                if (files.Length == 0) return null;
                string pick = files[UnityEngine.Random.Range(0, files.Length)];
                return System.IO.File.ReadAllBytes(pick);
            }
            catch (System.Exception e)
            {
                Debug.LogWarning($"[FLOW] Load banknote thất bại ({denomFolder}): {e.Message}");
                return null;
            }
        }

        private IEnumerator DetectOneBanknote(string denom)
        {
            cashDetecting = true;
            byte[] bytes = LoadRandomBanknoteBytes(denom);
            if (bytes == null)
            {
                cashHistory.Add($"❌ Không tìm thấy ảnh mẫu cho {denom}đ");
                cashDetecting = false;
                yield break;
            }

            // Load ảnh vào texture preview để user thấy ảnh Unity vừa gửi AI
            if (lastBanknoteTexture != null) Destroy(lastBanknoteTexture);
            lastBanknoteTexture = new Texture2D(2, 2);
            lastBanknoteTexture.LoadImage(bytes);
            lastBanknoteLabel = $"Đang detect {int.Parse(denom) / 1000}k...";

            bool done = false;
            ApiResponse<BanknoteResult> result = null;
            StartCoroutine(apiService.DetectBanknote(bytes, r => { result = r; done = true; }));
            yield return WaitWithTimeout(() => done, 10f, () => { });
            cashDetecting = false;

            if (!done || result == null || !result.IsSuccess || result.Data == null)
            {
                string err = result?.ErrorMessage ?? "timeout";
                cashHistory.Add($"⚠️ {denom}đ → API lỗi: {err}");
                lastBanknoteLabel = $"⚠️ API lỗi: {err}";
                yield break;
            }

            var d = result.Data;
            string denomK = $"{int.Parse(denom) / 1000}k";
            if (d.Decision == "accept" && !string.IsNullOrEmpty(d.Denomination) &&
                double.TryParse(d.Denomination, out double value))
            {
                cashAcceptedTotal += value;
                string predK = $"{(int)value / 1000}k";
                bool correct = value.ToString("F0") == denom;
                string icon = correct ? "✅" : "⚠️";
                cashHistory.Add($"{icon} Bấm {denomK} → AI: {predK} (conf {d.Confidence:P0})");
                lastBanknoteLabel = $"{icon} Gửi: {denomK} | AI: {predK} (conf {d.Confidence:P0})";
            }
            else
            {
                cashHistory.Add($"❌ Bấm {denomK} → AI từ chối: {d.Decision}");
                lastBanknoteLabel = $"❌ Gửi: {denomK} | AI từ chối: {d.Decision}";
            }
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
            double refund = cashAcceptedTotal - momoAmount;
            string okMsg = refund > 0
                ? $"\u2705 Đã thanh toán {momoAmount:N0}đ. 💰 Thối lại: {refund:N0}đ. Đang mở cổng…"
                : $"\u2705 Đã thanh toán đủ {momoAmount:N0}đ. Đang mở cổng…";
            SetResult(ok, ok ? okMsg : (result.Data?.Message ?? "Thanh toán thất bại"));
            Debug.Log(ok ? $"[FLOW] {okMsg}" : $"[FLOW] ❌ Payment failed: {result.Data?.Message}");

            if (ok)
            {
                string paidBookingId = momoBookingId;
                string paidPlate = momoPlate;
                CloseMomoQr();

                // 1. Call check-out backend lần nữa (amountDue giờ = 0 → barrier=open).
                // Backend sẽ broadcast unity.depart_vehicle nhưng race-condition với
                // WS nên mình trigger StartDeparture TRỰC TIẾP ở Unity để chắc chắn
                // xe chạy ra ngoài.
                var bks = SharedBookingState.Instance?.GetAllActiveForDropdown();
                if (bks != null)
                {
                    int idx = bks.FindIndex(b => b.booking.BookingId == paidBookingId);
                    if (idx >= 0)
                    {
                        selectedBookingIdx = idx;
                        yield return new WaitForSeconds(0.3f);
                        StartCoroutine(DoCheckOut());
                    }
                }

                // 2. Trigger depart xe ngay (không đợi backend/WS): tìm xe parked với
                // plate đã thanh toán → StartDeparture → xe tự đi ra cổng exit.
                if (!string.IsNullOrEmpty(paidPlate))
                {
                    foreach (var v in FindObjectsOfType<ParkingSim.Vehicle.VehicleController>())
                    {
                        if (v == null) continue;
                        if (string.Equals(v.plateNumber, paidPlate, System.StringComparison.OrdinalIgnoreCase))
                        {
                            v.StartDeparture();
                            Debug.Log($"[FLOW] 🚗 Depart {paidPlate} sau thanh toán thành công");
                            break;
                        }
                    }
                }

                // 3. Cleanup local state
                SharedBookingState.Instance?.RemoveBooking(paidBookingId);
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
