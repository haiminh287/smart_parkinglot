import json
from unittest.mock import AsyncMock

import pytest
from app.schemas.esp32 import BarrierAction, ESP32CheckInRequest, GateEvent
from app.services import esp32_checkin_service


@pytest.mark.anyio
async def test_process_checkin_should_call_booking_service_without_local_early_reject(
    monkeypatch,
    tmp_path,
):
    payload = ESP32CheckInRequest(
        gate_id="GATE-IN-01",
        qr_data=json.dumps(
            {
                "booking_id": "11111111-1111-1111-1111-111111111111",
                "user_id": "22222222-2222-2222-2222-222222222222",
            }
        ),
    )

    booking_response = {
        "id": "11111111-1111-1111-1111-111111111111",
        "checkInStatus": "not_checked_in",
        "paymentMethod": "on_exit",
        "vehicle": {"licensePlate": "51A-123.45", "vehicleType": "Car"},
        "startTime": "2099-01-01T10:00:00Z",
        "slotId": "33333333-3333-3333-3333-333333333333",
        "carSlot": {"code": "A-01"},
    }

    call_booking_checkin_mock = AsyncMock(
        return_value={
            "status_code": 200,
            "data": {
                "booking": {
                    "id": booking_response["id"],
                    "slotId": booking_response["slotId"],
                    "carSlot": {"code": "A-01"},
                }
            },
        }
    )

    monkeypatch.setattr(
        esp32_checkin_service, "auto_register_device", lambda _gate_id: None
    )
    monkeypatch.setattr(
        esp32_checkin_service, "get_booking", AsyncMock(return_value=booking_response)
    )
    monkeypatch.setattr(
        esp32_checkin_service, "call_booking_checkin", call_booking_checkin_mock
    )
    monkeypatch.setattr(
        esp32_checkin_service, "update_slot_status", AsyncMock(return_value=True)
    )
    monkeypatch.setattr(
        esp32_checkin_service, "broadcast_gate_event", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        esp32_checkin_service, "broadcast_unity_spawn", AsyncMock(return_value=None)
    )
    monkeypatch.setattr(
        esp32_checkin_service, "log_prediction", lambda *args, **kwargs: None
    )
    monkeypatch.setattr(esp32_checkin_service, "TEST_IMAGES_DIR", tmp_path)

    response = await esp32_checkin_service.process_checkin(payload, db=None)

    assert response.success is True
    assert response.event == GateEvent.CHECK_IN_SUCCESS
    assert response.barrier_action == BarrierAction.OPEN
    call_booking_checkin_mock.assert_awaited_once_with(
        "11111111-1111-1111-1111-111111111111",
        "22222222-2222-2222-2222-222222222222",
    )
