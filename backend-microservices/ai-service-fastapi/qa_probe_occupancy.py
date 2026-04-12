import asyncio
import json
from pathlib import Path

from httpx import ASGITransport, AsyncClient

from app.main import app
from app.config import settings


def fake_jpeg_bytes() -> bytes:
    fixture = Path(__file__).resolve().parent / "test_annotated.jpg"
    if fixture.exists():
        return fixture.read_bytes()
    return b"\xff\xd8\xff\xd9"


async def main() -> None:
    results = {}
    auth_headers = {
        "X-Gateway-Secret": settings.GATEWAY_SECRET,
        "X-User-ID": "qa-user",
        "X-User-Email": "qa@example.com",
    }

    results["runtime_secret"] = settings.GATEWAY_SECRET

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r1 = await client.post("/ai/parking/detect-occupancy/", headers=auth_headers)
        results["missing_all"] = {"status": r1.status_code, "body": r1.text}

        files = {"image": ("test.jpg", fake_jpeg_bytes(), "image/jpeg")}
        r2 = await client.post(
            "/ai/parking/detect-occupancy/",
            headers=auth_headers,
            files=files,
            data={"camera_id": "cam-1", "slots": "{not json}"},
        )
        results["invalid_slots_json"] = {"status": r2.status_code, "body": r2.text}

        valid_slots = json.dumps([
            {
                "slot_id": "slot-1",
                "slot_code": "A1",
                "zone_id": "z1",
                "x1": 0,
                "y1": 0,
                "x2": 10,
                "y2": 10,
            }
        ])
        r3 = await client.post(
            "/ai/parking/detect-occupancy/",
            headers=auth_headers,
            files=files,
            data={"camera_id": "cam-1", "slots": valid_slots},
        )
        try:
            parsed = r3.json()
        except Exception:
            parsed = None
        results["valid_form"] = {
            "status": r3.status_code,
            "body": r3.text,
            "json_keys": sorted(list(parsed.keys())) if isinstance(parsed, dict) else None,
        }

    print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
