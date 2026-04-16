using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using ParkingSim.API;
using ParkingSim.Parking;
using ParkingSim.Vehicle;
using ParkingSim.Camera;
using ParkingSim.Utility;

namespace ParkingSim.Core.Flow
{
    /// <summary>
    /// Handles check-in/out flows, ANPR verification, barrier control.
    /// Extracted from ParkingManager lines 387-662, 721-740.
    /// </summary>
    public class GateFlowController
    {
        // === Dependencies ===
        private readonly ApiConfig _config;
        private readonly ApiService _apiService;
        private readonly VirtualCameraManager _cameraManager;
        private readonly BarrierController _entryBarrier;
        private readonly BarrierController _exitBarrier;
        private readonly MonoBehaviour _coroutineHost;

        // === State ===
        private readonly List<VehicleController> _vehiclesWaitingAtGate = new List<VehicleController>();

        // === Events (raised to ParkingManager) ===
        public event Action<string> OnStatusMessage;
        public event Action<VehicleController> OnVehicleCheckedIn;
        public event Action<VehicleController> OnVehicleCheckedOut;

        public GateFlowController(
            ApiConfig config,
            ApiService apiService,
            VirtualCameraManager cameraManager,
            BarrierController entryBarrier,
            BarrierController exitBarrier,
            MonoBehaviour coroutineHost)
        {
            _config = config;
            _apiService = apiService;
            _cameraManager = cameraManager;
            _entryBarrier = entryBarrier;
            _exitBarrier = exitBarrier;
            _coroutineHost = coroutineHost;
        }

        // === Public Entry Points ===

        /// <summary>Subscribe to check-in success WS events.</summary>
        public void SubscribeWebSocket()
        {
            if (_apiService != null)
                _apiService.OnCheckinSuccess += HandleCheckinSuccessInternal;
        }

        public void UnsubscribeWebSocket()
        {
            if (_apiService != null)
                _apiService.OnCheckinSuccess -= HandleCheckinSuccessInternal;
        }

        /// <summary>
        /// Called when vehicle reaches entry gate.
        /// If pre-checked-in → ANPR flow; otherwise wait for QR scan.
        /// </summary>
        public void HandleVehicleAtEntry(VehicleController vehicle)
        {
            if (vehicle.alreadyCheckedIn)
            {
                _coroutineHost.StartCoroutine(CheckInWithANPR(vehicle));
                return;
            }
            _vehiclesWaitingAtGate.Add(vehicle);
            Debug.Log($"[GateFlowController] {vehicle.plateNumber} waiting at gate for QR");
        }

        /// <summary>
        /// Called by ESP32Simulator after QR scan success.
        /// Finds waiting vehicle, triggers ANPR flow.
        /// </summary>
        public bool CheckInWaitingVehicle(string plate)
        {
            var vehicle = _vehiclesWaitingAtGate.Find(v =>
                string.Equals(v.plateNumber, plate, StringComparison.OrdinalIgnoreCase));

            if (vehicle == null)
            {
                Debug.LogWarning($"[GateFlowController] No vehicle at gate with plate {plate}");
                return false;
            }

            _vehiclesWaitingAtGate.Remove(vehicle);
            _coroutineHost.StartCoroutine(CheckInWithANPR(vehicle));
            return true;
        }

        /// <summary>Handle vehicle at exit gate (mock or real check-out).</summary>
        public void HandleVehicleAtExit(VehicleController vehicle)
        {
            if (_config.useMockData)
            {
                _coroutineHost.StartCoroutine(_exitBarrier.OpenThenClose(3f));
                vehicle.ProceedFromExit();
            }
            else
            {
                _coroutineHost.StartCoroutine(ESP32CheckOutFlow(vehicle));
            }
        }

        /// <summary>Handle vehicle parked — verify slot with backend.</summary>
        public void HandleVehicleParked(VehicleController vehicle, Action<VehicleController, float> onAutoDepartCallback)
        {
            Debug.Log($"[GateFlowController] {vehicle.plateNumber} parked at slot");

            var booking = SharedBookingState.Instance?.GetBookingById(vehicle.bookingId);
            if (booking == null)
            {
                // Random spawn — auto depart after random duration
                float duration = UnityEngine.Random.Range(10f, 30f);
                onAutoDepartCallback?.Invoke(vehicle, duration);
                return;
            }

            // Slot verification
            string actualSlot = vehicle.TargetSlot?.slotCode ?? "unknown";
            string bookedSlot = booking.SlotCode ?? "unknown";
            bool match = string.Equals(actualSlot, bookedSlot, StringComparison.OrdinalIgnoreCase);

            if (match)
            {
                Debug.Log($"[GateFlowController] ✅ SLOT VERIFIED: {vehicle.plateNumber} at {actualSlot} " +
                          $"(matches booking {vehicle.bookingId.Substring(0, Math.Min(8, vehicle.bookingId.Length))})");
            }
            else
            {
                Debug.LogWarning($"[GateFlowController] ⚠️ SLOT MISMATCH: parked {actualSlot}, booked {bookedSlot}");
            }

            if (!_config.useMockData)
                _coroutineHost.StartCoroutine(VerifySlotFlow(vehicle, actualSlot, booking));
        }

        /// <summary>Parse WS check-in success data for spawning. Called from ParkingManager.</summary>
        public (string plate, string bookingId, string qrData, string slotCode, string vehicleType)
            ParseCheckinSuccess(CheckinSuccessData data)
        {
            return (
                data?.Plate ?? "UNKNOWN",
                data?.BookingId ?? Guid.NewGuid().ToString(),
                data?.QrData ?? $"{{\"booking_id\":\"{data?.BookingId}\"}}",
                data?.SlotCode ?? "A-01",
                data?.VehicleType ?? "Car"
            );
        }

        // === Internal WS Handler ===

        private void HandleCheckinSuccessInternal(CheckinSuccessData data)
        {
            if (data == null) return;
            OnVehicleCheckedIn?.Invoke(null); // Signal to ParkingManager
        }

        // === Internal Flows ===

        private IEnumerator CheckInWithANPR(VehicleController vehicle)
        {
            Debug.Log($"[GateFlowController] 🔍 ANPR verification for {vehicle.plateNumber}...");

            string detectedPlate = null;
            float confidence = 0f;

            var streamer = _cameraManager?.GetStreamer("virtual-anpr-entry")
                        ?? _cameraManager?.GetStreamer("virtual-gate-in");

            if (streamer != null)
            {
                yield return null;
                yield return null; // 2 frames settle

                byte[] snapshot = streamer.SnapshotJpeg();
                if (snapshot != null && snapshot.Length > 0)
                {
                    bool anprDone = false;
                    ApiResponse<PlateScanResult> scanResult = null;
                    _coroutineHost.StartCoroutine(_apiService.AIRecognizePlate(snapshot,
                        r => { scanResult = r; anprDone = true; }));

                    yield return CoroutineHelpers.WaitUntilOrTimeout(
                        () => anprDone, 5f, null, "ANPR");

                    if (scanResult?.IsSuccess == true && scanResult.Data != null)
                    {
                        detectedPlate = scanResult.Data.PlateText;
                        confidence = scanResult.Data.Confidence;
                    }
                }
            }

            bool plateMatch = !string.IsNullOrEmpty(detectedPlate) &&
                string.Equals(detectedPlate, vehicle.plateNumber, StringComparison.OrdinalIgnoreCase);

            if (plateMatch)
                Debug.Log($"[GateFlowController] ✅ ANPR MATCH: {detectedPlate}, conf={confidence:P0}");
            else if (!string.IsNullOrEmpty(detectedPlate))
                Debug.LogWarning($"[GateFlowController] ⚠️ ANPR MISMATCH: {detectedPlate} vs {vehicle.plateNumber}");
            else
                Debug.LogWarning($"[GateFlowController] ⚠️ ANPR failed — no plate detected");

            // Open barrier: plate match OK, or no detection (fallback)
            bool shouldOpen = plateMatch || string.IsNullOrEmpty(detectedPlate);
            if (shouldOpen)
            {
                _coroutineHost.StartCoroutine(_entryBarrier.OpenThenClose(3f));
                vehicle.ProceedFromGate();
                Debug.Log($"[GateFlowController] ✅ Gate opened for {vehicle.plateNumber}" +
                          (plateMatch ? " (ANPR verified)" : " (ANPR unverified)"));
            }
            else
            {
                Debug.LogWarning($"[GateFlowController] 🚫 Gate BLOCKED: mismatch");
                OnStatusMessage?.Invoke($"Gate blocked: plate mismatch");
            }
        }

        private IEnumerator ESP32CheckOutFlow(VehicleController vehicle)
        {
            bool done = false;
            ApiResponse<ESP32Response> result = null;
            var request = new ESP32CheckOutRequest
            {
                GateId = MockIds.GATE_OUT,
                QrData = vehicle.qrData
            };
            _coroutineHost.StartCoroutine(_apiService.ESP32CheckOut(request,
                r => { result = r; done = true; }));

            yield return CoroutineHelpers.WaitUntilOrTimeout(
                () => done, 10f, null, "ESP32CheckOut");

            if (!done)
            {
                OnStatusMessage?.Invoke("Check-out timeout");
                yield break;
            }

            if (result?.IsSuccess == true && result.Data?.Success == true)
            {
                Debug.Log($"[GateFlowController] Check-out OK: {vehicle.plateNumber}");
                _coroutineHost.StartCoroutine(_exitBarrier.OpenThenClose(3f));
                yield return new WaitForSeconds(1f);
                vehicle.ProceedFromExit();
                OnVehicleCheckedOut?.Invoke(vehicle);
            }
            else
            {
                var msg = result?.Data?.Message ?? result?.ErrorMessage ?? "Unknown";
                Debug.LogWarning($"[GateFlowController] Check-out FAILED: {msg}");
                OnStatusMessage?.Invoke($"Check-out failed: {msg}");
            }
        }

        private IEnumerator VerifySlotFlow(VehicleController vehicle, string slotCode, ActiveBooking booking)
        {
            string qrData = vehicle.qrData ?? booking.QrCodeData;
            if (string.IsNullOrEmpty(qrData))
            {
                Debug.LogWarning($"[GateFlowController] No QR data for slot verify");
                yield break;
            }

            bool done = false;
            ApiResponse<ESP32Response> result = null;
            var request = new ESP32VerifySlotRequest
            {
                SlotCode = slotCode,
                ZoneId = MockIds.ZONE_CAR_PAINTED_F1,
                GateId = MockIds.GATE_IN,
                QrData = qrData
            };
            _coroutineHost.StartCoroutine(_apiService.ESP32VerifySlot(request,
                r => { result = r; done = true; }));

            yield return CoroutineHelpers.WaitUntilOrTimeout(
                () => done, 10f, null, "VerifySlot");

            if (result?.IsSuccess == true && result.Data?.Success == true)
                Debug.Log($"[GateFlowController] ✅ Backend verified slot {slotCode}");
            else
                Debug.LogWarning($"[GateFlowController] ⚠️ Slot verify failed");
        }
    }
}
