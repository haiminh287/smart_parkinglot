import asyncio
import json

from httpx import ASGITransport, AsyncClient

from app.main import app


def fake_jpeg_bytes() -> bytes:
    # Minimal JPEG SOI/EOI markers; enough for parser attempt in negative-path tests.
    return b"\xff\xd8\xff\xd9"


async def main() -> None:
    results = {}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        client.headers["X-Gateway-Secret"] = "gateway-internal-secret-key"
        client.headers["X-User-ID"] = "qa-user"
        client.headers["X-User-Email"] = "qa@example.com"

        # Missing params
        r1 = await client.post("/ai/parking/detect-occupancy/")
        results["missing_all"] = {
            "status": r1.status_code,
            "body": r1.text,
        }

        # Invalid slots JSON
        files = {"image": ("test.jpg", fake_jpeg_bytes(), "image/jpeg")}
        data = {
            "camera_id": "cam-1",
            "slots": "{not json}",
        }
        r2 = await client.post("/ai/parking/detect-occupancy/", files=files, data=data)
        results["invalid_slots_json"] = {
            "status": r2.status_code,
            "body": r2.text,
        }

        # Valid form shape (business may still fail due model/decode/runtime dependencies)
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
        data_valid = {
            "camera_id": "cam-1",
            "slots": valid_slots,
        }
        r3 = await client.post("/ai/parking/detect-occupancy/", files=files, data=data_valid)
        body = r3.text
        try:
            parsed = r3.json()
        except Exception:
            parsed = None

        results["valid_form"] = {
            "status": r3.status_code,
            "body": body,
            "json_keys": sorted(list(parsed.keys())) if isinstance(parsed, dict) else None,
        }

    print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
