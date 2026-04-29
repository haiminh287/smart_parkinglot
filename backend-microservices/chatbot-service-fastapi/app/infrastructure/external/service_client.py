"""
Service Client — HTTP calls to internal microservices.

Consumed by:
  - ActionService (book, cancel, check-in/out, pricing, etc.)
  - SafetyService (validate booking existence, slot availability)

All calls include X-Gateway-Secret + X-User-ID for service-to-service auth.
"""

import logging
from typing import Any, Optional

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)


class ServiceClient:
    """
    HTTP client for calling booking / parking / vehicle / payment services.

    Every request includes X-Gateway-Secret (service auth) and
    X-User-ID (user context) so Django services can authenticate.

    Usage:
        client = ServiceClient()
        result = await client.get_available_slots(vehicle_type="car")
    """

    def __init__(
        self,
        booking_url: Optional[str] = None,
        parking_url: Optional[str] = None,
        vehicle_url: Optional[str] = None,
        payment_url: Optional[str] = None,
        gateway_secret: Optional[str] = None,
    ):
        self.booking_url = (booking_url or settings.BOOKING_SERVICE_URL).rstrip("/")
        self.parking_url = (parking_url or settings.PARKING_SERVICE_URL).rstrip("/")
        self.vehicle_url = (vehicle_url or settings.VEHICLE_SERVICE_URL).rstrip("/")
        self.payment_url = (payment_url or settings.PAYMENT_SERVICE_URL).rstrip("/")
        self.gateway_secret = gateway_secret or settings.GATEWAY_SECRET
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=_DEFAULT_TIMEOUT,
                headers={
                    "X-Gateway-Secret": self.gateway_secret,
                    "Content-Type": "application/json",
                },
            )
        return self._client

    def _user_headers(self, user_id: Optional[str] = None) -> dict[str, str]:
        """Build per-request headers with X-User-ID for Django auth."""
        headers: dict[str, str] = {}
        if user_id:
            headers["X-User-ID"] = str(user_id)
            headers["X-User-Email"] = f"user-{user_id}@parksmart.com"
        return headers

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    # ─── GENERIC HELPERS ──────────────────────────

    async def _get(
        self,
        base_url: str,
        path: str,
        params: Optional[dict] = None,
        user_id: Optional[str] = None,
    ) -> dict:
        client = await self._get_client()
        url = f"{base_url}{path}"
        try:
            resp = await client.get(
                url, params=params, headers=self._user_headers(user_id),
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} from {url}: {e.response.text[:300]}")
            msg = self._extract_error_message(e.response)
            return {"status": "error", "error": msg, "statusCode": e.response.status_code}
        except Exception as e:
            logger.error(f"Request failed to {url}: {e}")
            return {"status": "error", "error": str(e)}

    @staticmethod
    def _extract_error_message(response: httpx.Response) -> str:
        """Extract user-friendly error message from HTTP error response."""
        try:
            body = response.json()
            # Django DRF error formats
            if isinstance(body, dict):
                for key in ("detail", "error", "message", "non_field_errors"):
                    val = body.get(key)
                    if val:
                        if isinstance(val, list):
                            return str(val[0])
                        return str(val)
                # Flatten field errors: {"field": ["msg"]}
                msgs = []
                for k, v in body.items():
                    if isinstance(v, list) and v:
                        msgs.append(f"{k}: {v[0]}")
                if msgs:
                    return "; ".join(msgs)
            if isinstance(body, list) and body:
                return str(body[0])
        except Exception:
            pass
        text = response.text[:200].strip()
        return text if text else f"HTTP {response.status_code}"

    async def _post(
        self,
        base_url: str,
        path: str,
        data: Optional[dict] = None,
        user_id: Optional[str] = None,
    ) -> dict:
        client = await self._get_client()
        url = f"{base_url}{path}"
        try:
            resp = await client.post(
                url, json=data or {}, headers=self._user_headers(user_id),
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} from {url}: {e.response.text[:300]}")
            msg = self._extract_error_message(e.response)
            return {"status": "error", "error": msg, "statusCode": e.response.status_code}
        except Exception as e:
            logger.error(f"Request failed to {url}: {e}")
            return {"status": "error", "error": str(e)}

    async def _patch(
        self,
        base_url: str,
        path: str,
        data: Optional[dict] = None,
        user_id: Optional[str] = None,
    ) -> dict:
        client = await self._get_client()
        url = f"{base_url}{path}"
        try:
            resp = await client.patch(
                url, json=data or {}, headers=self._user_headers(user_id),
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} from {url}: {e.response.text[:300]}")
            msg = self._extract_error_message(e.response)
            return {"status": "error", "error": msg, "statusCode": e.response.status_code}
        except Exception as e:
            logger.error(f"Request failed to {url}: {e}")
            return {"status": "error", "error": str(e)}

    async def _delete(
        self,
        base_url: str,
        path: str,
        user_id: Optional[str] = None,
    ) -> dict:
        client = await self._get_client()
        url = f"{base_url}{path}"
        try:
            resp = await client.delete(url, headers=self._user_headers(user_id))
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} from {url}: {e.response.text[:300]}")
            msg = self._extract_error_message(e.response)
            return {"status": "error", "error": msg, "statusCode": e.response.status_code}
        except Exception as e:
            logger.error(f"Request failed to {url}: {e}")
            return {"status": "error", "error": str(e)}

    # ─── BOOKING SERVICE ──────────────────────────

    async def get_active_bookings(self, user_id: str) -> list[dict]:
        """Get user's active bookings (used by SafetyService).

        Only returns bookings with not_checked_in or checked_in status,
        excluding cancelled, checked_out, and no_show bookings.
        """
        result = await self._get(
            self.booking_url, "/bookings/",
            user_id=user_id,
        )
        all_bookings: list[dict] = []
        if isinstance(result, list):
            all_bookings = result
        else:
            all_bookings = result.get("results", result.get("bookings", []))

        # Filter to truly active bookings only
        active_statuses = {"not_checked_in", "checked_in"}
        return [
            b for b in all_bookings
            if (b.get("checkInStatus") or b.get("check_in_status", "")) in active_statuses
        ]

    async def get_booking(self, user_id: str, booking_id: str) -> Optional[dict]:
        """Get a specific booking by ID."""
        result = await self._get(
            self.booking_url, f"/bookings/{booking_id}/",
            user_id=user_id,
        )
        if result.get("status") == "error":
            return None
        return result

    async def create_booking(
        self,
        user_id: str,
        vehicle_id: Optional[str] = None,
        zone_id: Optional[str] = None,
        parking_lot_id: Optional[str] = None,
        slot_id: Optional[str] = None,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        package_type: str = "hourly",
        payment_method: str = "on_exit",
    ) -> dict:
        """Create a new booking.

        Args:
            user_id: User making the booking.
            vehicle_id: UUID or license plate of the vehicle.
            zone_id: UUID of the parking zone (REQUIRED by booking-service).
            parking_lot_id: UUID of the parking lot (REQUIRED by booking-service).
            slot_id: UUID of specific slot (optional).
            start_time: ISO datetime string (REQUIRED).
            end_time: ISO datetime string (optional).
            package_type: hourly/daily/weekly/monthly.
            payment_method: online/on_exit.

        Returns:
            Booking result dict from booking-service.
        """
        # booking-service Django uses snake_case field names
        payload: dict[str, Any] = {
            "vehicle_id": vehicle_id,
            "zone_id": zone_id,
            "parking_lot_id": parking_lot_id,
            "start_time": start_time,
            "package_type": package_type,
            "payment_method": payment_method,
        }
        if slot_id:
            payload["slot_id"] = slot_id
        if end_time:
            payload["end_time"] = end_time

        logger.info(f"create_booking payload: {payload}")
        result = await self._post(
            self.booking_url, "/bookings/", data=payload, user_id=user_id,
        )
        return {**result, "status": result.get("status", "ok")}

    async def cancel_booking(self, user_id: str, booking_id: str) -> dict:
        """Cancel a booking."""
        result = await self._post(
            self.booking_url, f"/bookings/{booking_id}/cancel/",
            data={}, user_id=user_id,
        )
        return {**result, "status": result.get("status", "ok")}

    async def rebook_previous(self, user_id: str) -> dict:
        """Rebook the last booking for the user."""
        result = await self._post(
            self.booking_url, "/bookings/rebook/",
            data={}, user_id=user_id,
        )
        return {**result, "status": result.get("status", "ok")}

    async def check_in(self, user_id: str, booking_id: str) -> dict:
        """Check in to a booking."""
        result = await self._post(
            self.booking_url, f"/bookings/{booking_id}/checkin/",
            data={}, user_id=user_id,
        )
        return {**result, "status": result.get("status", "ok")}

    async def check_out(self, user_id: str, booking_id: str) -> dict:
        """Check out of a booking."""
        result = await self._post(
            self.booking_url, f"/bookings/{booking_id}/checkout/",
            data={}, user_id=user_id,
        )
        return {**result, "status": result.get("status", "ok")}

    async def get_user_bookings(self, user_id: str) -> dict:
        """Get all bookings for a user."""
        result = await self._get(
            self.booking_url, "/bookings/",
            user_id=user_id,
        )
        bookings = result if isinstance(result, list) else result.get("results", [])
        return {"status": "ok", "bookings": bookings}

    # ─── PARKING SERVICE ──────────────────────────

    async def get_available_slots(
        self,
        vehicle_type: Optional[str] = None,
        lot_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> dict:
        """Get available parking slots.

        user_id cần để parking-service's IsGatewayAuthenticated permission
        pass (middleware set request.user_id từ X-User-ID header).
        """
        params: dict[str, Any] = {"status": "available", "limit": 500}
        if vehicle_type:
            params["vehicle_type"] = vehicle_type
        if lot_id:
            # Parking-service dùng snake_case query param (lot_id), không phải lotId
            params["lot_id"] = lot_id

        result = await self._get(
            self.parking_url, "/parking/slots/", params=params, user_id=user_id,
        )
        slots = result if isinstance(result, list) else result.get("results", result.get("slots", []))
        return {"status": "ok", "slots": slots, "totalAvailable": len(slots)}

    async def get_zones(
        self,
        vehicle_type: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> list[dict]:
        """Get parking zones, optionally filtered by vehicle type.

        Args:
            vehicle_type: 'Car' or 'Motorcycle' to filter zones.
            user_id: User ID for auth header (parking-service requires it).

        Returns:
            List of zone dicts with id, name, floorId, vehicleType, etc.
        """
        params: dict[str, Any] = {}
        if vehicle_type:
            params["vehicle_type"] = vehicle_type
        result = await self._get(
            self.parking_url, "/parking/zones/", params=params, user_id=user_id,
        )
        if isinstance(result, list):
            return result
        return result.get("results", [])

    async def get_parking_lots(self, user_id: Optional[str] = None) -> list[dict]:
        """Get all parking lots.

        Args:
            user_id: User ID for auth header (parking-service requires it).

        Returns:
            List of parking lot dicts with id, name, address, etc.
        """
        result = await self._get(
            self.parking_url, "/parking/lots/", user_id=user_id,
        )
        if isinstance(result, list):
            return result
        return result.get("results", [])

    async def get_floors(
        self,
        lot_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> list[dict]:
        """Get parking floors with nested zones.

        The parking-service /parking/floors/ endpoint returns floors with
        nested zone data including availableSlots counts.

        Args:
            lot_id: Optional parking lot ID to filter floors.
            user_id: User ID for auth header.

        Returns:
            List of floor dicts with id, name, level, zones (nested).
        """
        params: dict[str, Any] = {}
        if lot_id:
            params["parking_lot_id"] = lot_id
        result = await self._get(
            self.parking_url, "/parking/floors/", params=params, user_id=user_id,
        )
        if isinstance(result, list):
            return result
        return result.get("results", [])

    async def check_slot_available(self, slot_id: str) -> bool:
        """Check if a specific slot is available."""
        result = await self._get(self.parking_url, f"/parking/slots/{slot_id}/")
        if result.get("status") == "error":
            return False
        return result.get("status") == "available"

    async def get_slots_by_zone(
        self,
        zone_id: str,
        vehicle_type: Optional[str] = None,
    ) -> list[dict]:
        """Get available slots filtered by zone.

        Args:
            zone_id: UUID of the zone to get slots for.
            vehicle_type: 'Car' or 'Motorcycle' filter.

        Returns:
            List of available slot dicts in the specified zone.
        """
        params: dict[str, Any] = {"status": "available", "zone_id": zone_id}
        if vehicle_type:
            params["vehicle_type"] = vehicle_type
        result = await self._get(self.parking_url, "/parking/slots/", params=params)
        slots = result if isinstance(result, list) else result.get("results", result.get("slots", []))
        return [s for s in slots if str(s.get("zoneId") or s.get("zone_id", "")) == zone_id]

    async def get_current_parking(self, user_id: str) -> dict:
        """Get user's current parking location via booking service."""
        result = await self._get(
            self.booking_url, "/bookings/",
            user_id=user_id,
        )
        # Find active booking with check-in
        bookings = result if isinstance(result, list) else result.get("results", [])
        active = None
        for b in bookings:
            check_in_status = b.get("checkInStatus") or b.get("check_in_status", "")
            if check_in_status == "checked_in":
                active = b
                break
        return {"status": "ok", "parking": active}

    # ─── VEHICLE SERVICE ──────────────────────────

    async def get_user_vehicles(self, user_id: str) -> list[dict]:
        """Get user's registered vehicles."""
        result = await self._get(
            self.vehicle_url, "/vehicles/",
            user_id=user_id,
        )
        if isinstance(result, list):
            return result
        return result.get("results", result.get("vehicles", []))

    # ─── PAYMENT SERVICE ──────────────────────────

    async def get_pricing(self, vehicle_type: Optional[str] = None) -> dict:
        """Get pricing information."""
        params: dict[str, Any] = {}
        if vehicle_type:
            params["vehicleType"] = vehicle_type
        result = await self._get(self.payment_url, "/api/payments/pricing/", params=params)
        pricing = result if isinstance(result, list) else result.get("results", result.get("pricing", []))
        return {"status": "ok", "pricing": pricing}
