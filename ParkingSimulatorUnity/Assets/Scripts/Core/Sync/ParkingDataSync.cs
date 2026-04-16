using System;
using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using ParkingSim.API;
using ParkingSim.Parking;
using ParkingSim.Utility;

namespace ParkingSim.Core.Sync
{
    /// <summary>
    /// Handles data synchronization: login, fetch floors/slots, WS updates, polling fallback.
    /// Extracted from ParkingManager lines 146-335.
    /// </summary>
    public class ParkingDataSync
    {
        // === Dependencies (injected via constructor) ===
        private readonly ApiConfig _config;
        private readonly ApiService _apiService;
        private readonly AuthManager _authManager;
        private readonly ParkingLotGenerator _generator;
        private readonly MonoBehaviour _coroutineHost;

        // === Cached Data ===
        public List<SlotData> CachedSlots { get; private set; } = new List<SlotData>();
        public List<FloorData> CachedFloors { get; private set; } = new List<FloorData>();
        public List<BookingData> CachedBookings { get; private set; } = new List<BookingData>();

        // === Events ===
        public event Action<List<SlotData>> OnSlotsUpdated;
        public event Action OnSyncComplete;

        // === State ===
        public bool IsInitialized { get; private set; }
        private Coroutine _pollCoroutine;

        public ParkingDataSync(
            ApiConfig config,
            ApiService apiService,
            AuthManager authManager,
            ParkingLotGenerator generator,
            MonoBehaviour coroutineHost)
        {
            _config = config;
            _apiService = apiService;
            _authManager = authManager;
            _generator = generator;
            _coroutineHost = coroutineHost;
        }

        // === Public API ===

        /// <summary>
        /// Full initialization: login → fetch booking → fetch slots/floors → map to scene.
        /// Call from ParkingManager.Start().
        /// </summary>
        public IEnumerator InitializeAsync()
        {
            yield return _coroutineHost.StartCoroutine(LoginCoroutine());
            yield return _coroutineHost.StartCoroutine(FetchDataCoroutine());
            yield return _coroutineHost.StartCoroutine(FetchBookingsCoroutine());
            ApplySlotMapping();
            IsInitialized = true;
            OnSyncComplete?.Invoke();
        }

        /// <summary>Subscribe to WS events. Call after InitializeAsync.</summary>
        public void SubscribeWebSocket()
        {
            if (_apiService != null)
            {
                _apiService.ConnectWebSocket();
                _apiService.OnSlotStatusUpdate += HandleSlotStatusUpdate;
            }
        }

        /// <summary>Unsubscribe from WS events. Call from OnDestroy.</summary>
        public void UnsubscribeWebSocket()
        {
            if (_apiService != null)
                _apiService.OnSlotStatusUpdate -= HandleSlotStatusUpdate;
        }

        /// <summary>Start fallback polling (only kicks in when WS is down).</summary>
        public void StartPolling()
        {
            if (_pollCoroutine != null) return;
            _pollCoroutine = _coroutineHost.StartCoroutine(PollCoroutine());
        }

        public void StopPolling()
        {
            if (_pollCoroutine != null)
            {
                _coroutineHost.StopCoroutine(_pollCoroutine);
                _pollCoroutine = null;
            }
        }

        /// <summary>Get SlotData for a code from cached data.</summary>
        public SlotData GetSlotDataByCode(string code)
            => CachedSlots?.Find(s => s.Code == code);

        /// <summary>List occupied slots from cache.</summary>
        public List<SlotData> GetOccupiedSlots()
            => CachedSlots?.FindAll(s =>
                string.Equals(s.Status, "occupied", StringComparison.OrdinalIgnoreCase))
               ?? new List<SlotData>();

        // === Internal Coroutines ===

        private IEnumerator LoginCoroutine()
        {
            bool done = false, success = false;
            Action successHandler = () => { success = true; done = true; };
            Action<string> failHandler = _ => { done = true; };
            _authManager.OnLoginSuccess += successHandler;
            _authManager.OnLoginFailed += failHandler;

            yield return _coroutineHost.StartCoroutine(
                _authManager.Login(_config.testEmail, _config.testPassword));

            // Timeout 10s
            yield return CoroutineHelpers.WaitUntilOrTimeout(
                () => done, 10f, null, "Login");

            _authManager.OnLoginSuccess -= successHandler;
            _authManager.OnLoginFailed -= failHandler;
            Debug.Log(success ? "[ParkingDataSync] Login OK" : "[ParkingDataSync] Login FAILED");
        }

        private IEnumerator FetchDataCoroutine()
        {
            // Fetch Slots
            bool slotsDone = false;
            ApiResponse<PaginatedResponse<SlotData>> slotsResult = null;
            _coroutineHost.StartCoroutine(_apiService.GetSlots(
                _config.targetParkingLotId,
                r => { slotsResult = r; slotsDone = true; }));

            yield return CoroutineHelpers.WaitUntilOrTimeout(
                () => slotsDone, 10f, null, "FetchSlots");

            CachedSlots = slotsResult?.IsSuccess == true
                ? slotsResult.Data?.Results ?? new List<SlotData>()
                : new List<SlotData>();
            Debug.Log($"[ParkingDataSync] Fetched {CachedSlots.Count} slots");

            // Fetch Floors
            bool floorsDone = false;
            ApiResponse<PaginatedResponse<FloorData>> floorsResult = null;
            _coroutineHost.StartCoroutine(_apiService.GetFloors(
                _config.targetParkingLotId,
                r => { floorsResult = r; floorsDone = true; }));

            yield return CoroutineHelpers.WaitUntilOrTimeout(
                () => floorsDone, 10f, null, "FetchFloors");

            CachedFloors = floorsResult?.IsSuccess == true
                ? floorsResult.Data?.Results ?? new List<FloorData>()
                : new List<FloorData>();
            Debug.Log($"[ParkingDataSync] Fetched {CachedFloors.Count} floors");
        }

        private IEnumerator FetchBookingsCoroutine()
        {
            bool done = false;
            ApiResponse<PaginatedResponse<BookingData>> result = null;
            _coroutineHost.StartCoroutine(_apiService.GetBookings(
                r => { result = r; done = true; }));

            yield return CoroutineHelpers.WaitUntilOrTimeout(
                () => done, 10f, null, "FetchBookings");

            if (result?.IsSuccess == true && result.Data?.Results != null)
            {
                CachedBookings = result.Data.Results;
                int synced = SharedBookingState.Instance?.SyncFromApi(CachedBookings) ?? 0;
                Debug.Log($"[ParkingDataSync] Pre-synced {synced} bookings");
            }
        }

        private void ApplySlotMapping()
        {
            if (CachedSlots == null || _generator == null) return;

            int matched = 0;
            foreach (var apiSlot in CachedSlots)
            {
                if (_generator.slotRegistry.TryGetValue(apiSlot.Code, out var slot))
                {
                    slot.slotId = apiSlot.Id;
                    slot.UpdateState(ParkingSlot.ParseStatus(apiSlot.Status));
                    matched++;
                }
            }
            Debug.Log($"[ParkingDataSync] Mapped {matched}/{CachedSlots.Count} slots");
        }

        private void HandleSlotStatusUpdate(SlotStatusUpdate update)
        {
            if (_generator == null) return;
            foreach (var kvp in _generator.slotRegistry)
            {
                if (kvp.Value.slotId == update.SlotId)
                {
                    kvp.Value.UpdateState(ParkingSlot.ParseStatus(update.Status));
                    Debug.Log($"[ParkingDataSync] WS: slot {kvp.Key} → {update.Status}");
                    return;
                }
            }
        }

        private IEnumerator PollCoroutine()
        {
            while (true)
            {
                yield return new WaitForSeconds(_config.deltaPollInterval);

                // Skip if WS is healthy
                if (_apiService != null && _apiService.IsWsConnected)
                    continue;

                bool done = false;
                ApiResponse<PaginatedResponse<SlotData>> result = null;
                _coroutineHost.StartCoroutine(_apiService.GetSlots(
                    _config.targetParkingLotId,
                    r => { result = r; done = true; }));

                yield return CoroutineHelpers.WaitUntilOrTimeout(
                    () => done, 10f, null, "PollSlots");

                if (!done) continue; // Timeout — skip tick

                if (result?.IsSuccess == true && result.Data?.Results != null)
                {
                    foreach (var apiSlot in result.Data.Results)
                    {
                        if (_generator.slotRegistry.TryGetValue(apiSlot.Code, out var slot))
                            slot.UpdateState(ParkingSlot.ParseStatus(apiSlot.Status));
                    }
                    OnSlotsUpdated?.Invoke(result.Data.Results);
                }
            }
        }
    }
}
