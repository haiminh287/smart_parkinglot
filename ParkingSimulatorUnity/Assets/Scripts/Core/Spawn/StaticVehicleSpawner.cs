using System;
using System.Collections.Generic;
using UnityEngine;
using ParkingSim.API;
using ParkingSim.Parking;
using ParkingSim.Vehicle;

namespace ParkingSim.Core.Spawn
{
    /// <summary>
    /// Spawns static (already-parked) vehicles for occupied slots at startup.
    /// Extracted from ParkingManager lines 221-268, 681-705.
    /// </summary>
    public class StaticVehicleSpawner
    {
        private readonly ParkingLotGenerator _generator;
        private readonly GameObject _carPrefab;
        private readonly GameObject _motorbikePrefab;

        public StaticVehicleSpawner(
            ParkingLotGenerator generator,
            GameObject carPrefab,
            GameObject motorbikePrefab)
        {
            _generator = generator;
            _carPrefab = carPrefab;
            _motorbikePrefab = motorbikePrefab;
        }

        /// <summary>
        /// Spawn static vehicle for occupied slot from API sync.
        /// Called during MapApiDataToSlots.
        /// </summary>
        public void SpawnForOccupiedSlot(ParkingSlot slot, string plateNumber = null)
        {
            if (slot == null) return;
            var prefab = slot.slotType == ParkingSlot.SlotType.Motorbike
                ? _motorbikePrefab
                : _carPrefab;
            if (prefab == null) return;

            // Place at slot centre at floor level
            Vector3 slotPos = slot.transform.position;
            float floorY = slotPos.y - 0.12f + 0.1f;
            Vector3 slotFwd = slot.transform.forward;
            Quaternion parkRot = slotFwd.sqrMagnitude > 0.01f
                ? Quaternion.LookRotation(-slotFwd)
                : Quaternion.identity;

            var go = UnityEngine.Object.Instantiate(
                prefab,
                new Vector3(slotPos.x, floorY, slotPos.z),
                parkRot);
            go.name = $"StaticVehicle_{slot.slotCode}";

            // URP material fix
            if (go.GetComponent<VehicleVisualEnhancer>() == null)
                go.AddComponent<VehicleVisualEnhancer>();

            var vc = go.GetComponent<VehicleController>();
            if (vc != null)
            {
                vc.state = VehicleController.VehicleState.Parked;
                vc.plateNumber = plateNumber ?? $"MOCK-{slot.slotCode}";
                vc.enabled = false;
            }

            var rb = go.GetComponent<Rigidbody>();
            if (rb != null) rb.isKinematic = true;

            AttachPlateText(go, vc?.plateNumber ?? "UNKNOWN");
            Debug.Log($"[StaticVehicleSpawner] Spawned at {slot.slotCode} plate={vc?.plateNumber}");
        }

        /// <summary>Apply mock statuses and spawn vehicles for occupied mock slots.</summary>
        public void ApplyMockStatuses()
        {
            var mockSlots = MockDataProvider.GenerateMockSlots();
            int matched = 0;
            foreach (var apiSlot in mockSlots)
            {
                if (_generator.slotRegistry.TryGetValue(apiSlot.Code, out var slot))
                {
                    var status = ParkingSlot.ParseStatus(apiSlot.Status);
                    slot.slotId = apiSlot.Id;
                    slot.UpdateState(status);
                    matched++;

                    if (status == ParkingSlot.SlotStatus.Occupied)
                        SpawnForOccupiedSlot(slot, $"SIM-{apiSlot.Code}");
                }
            }
            Debug.Log($"[StaticVehicleSpawner] Mock applied: {matched}/{mockSlots.Count}");
        }

        /// <summary>
        /// After sync completes, spawn vehicles for all occupied slots.
        /// Call this from ParkingManager after ParkingDataSync.ApplySlotMapping.
        /// </summary>
        public void SpawnOccupiedVehicles(List<SlotData> slots)
        {
            if (slots == null || _generator == null) return;
            foreach (var apiSlot in slots)
            {
                if (!string.Equals(apiSlot.Status, "occupied", StringComparison.OrdinalIgnoreCase))
                    continue;
                if (!_generator.slotRegistry.TryGetValue(apiSlot.Code, out var slot))
                    continue;

                string plate = SharedBookingState.Instance?.GetBookingBySlotCode(apiSlot.Code)?.LicensePlate;
                SpawnForOccupiedSlot(slot, plate);
            }
        }

        private void AttachPlateText(GameObject vehicle, string plateText)
        {
            LicensePlateCreator.CreateRearPlate(vehicle.transform, plateText);
        }
    }
}
