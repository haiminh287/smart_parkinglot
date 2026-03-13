/**
 * useParking Hook
 * Provides parking-related functionality using Redux store
 */

import { useCallback, useEffect } from "react";
import { useAppDispatch, useAppSelector } from "@/store/hooks";
import {
  fetchParkingLots,
  fetchZones,
  fetchSlots,
  setSelectedLot,
  setSelectedZone,
  clearError,
  updateSlotStatus,
  updateZoneAvailability,
  updateLotAvailability,
} from "@/store/slices/parkingSlice";
import type { ParkingZone, ParkingSlot } from "@/store/slices/parkingSlice";
import type { ParkingLot } from "@/types/parking";

export function useParking() {
  const dispatch = useAppDispatch();

  const { lots, zones, slots, selectedLot, selectedZone, isLoading, error } =
    useAppSelector((state) => state.parking);

  // Fetch parking lots
  const loadParkingLots = useCallback(
    (params?: { lat?: number; lng?: number }) => {
      return dispatch(fetchParkingLots(params));
    },
    [dispatch],
  );

  // Fetch zones for a lot
  const loadZones = useCallback(
    (lotId: string) => {
      return dispatch(fetchZones(lotId));
    },
    [dispatch],
  );

  // Fetch slots for a zone
  const loadSlots = useCallback(
    (zoneId: string) => {
      return dispatch(fetchSlots(zoneId));
    },
    [dispatch],
  );

  // Select parking lot
  const selectLot = useCallback(
    (lot: ParkingLot | null) => {
      dispatch(setSelectedLot(lot));
      if (lot) {
        dispatch(fetchZones(lot.id));
      }
    },
    [dispatch],
  );

  // Select zone
  const selectZone = useCallback(
    (zone: ParkingZone | null) => {
      dispatch(setSelectedZone(zone));
      if (zone) {
        dispatch(fetchSlots(zone.id));
      }
    },
    [dispatch],
  );

  // Clear parking error
  const clearParkingError = useCallback(() => {
    dispatch(clearError());
  }, [dispatch]);

  // Filter available slots
  const availableSlots = slots.filter((slot) => slot.status === "available");

  // Filter slots by vehicle type
  const getSlotsByVehicleType = useCallback(
    (vehicleType: "Car" | "Motorbike") => {
      return slots.filter((slot) => slot.vehicleType === vehicleType);
    },
    [slots],
  );

  // Get zones by vehicle type
  const getZonesByVehicleType = useCallback(
    (vehicleType: "Car" | "Motorbike") => {
      return zones.filter((zone) => zone.vehicleType === vehicleType);
    },
    [zones],
  );

  // Get available count for a zone
  const getZoneAvailability = useCallback(
    (zoneId: string) => {
      const zone = zones.find((z) => z.id === zoneId);
      return zone
        ? {
            total: zone.capacity,
            available: zone.availableSlots,
            occupied: zone.occupiedSlots,
            reserved: zone.reservedSlots,
          }
        : null;
    },
    [zones],
  );

  return {
    // State
    lots,
    zones,
    slots,
    selectedLot,
    selectedZone,
    isLoading,
    error,
    availableSlots,

    // Actions
    loadParkingLots,
    loadZones,
    loadSlots,
    selectLot,
    selectZone,
    clearError: clearParkingError,

    // Helpers
    getSlotsByVehicleType,
    getZonesByVehicleType,
    getZoneAvailability,
  };
}
