"""Parking AI routers — license plate recognition + occupancy detection."""

from fastapi import APIRouter

from .check_in import router as checkin_router
from .check_out import router as checkout_router
from .detect_occupancy import router as occupancy_router
from .scan_plate import router as scan_plate_router

router = APIRouter(prefix="/ai/parking", tags=["parking"])
router.include_router(scan_plate_router)
router.include_router(checkin_router)
router.include_router(checkout_router)
router.include_router(occupancy_router)
