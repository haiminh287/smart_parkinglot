import asyncio
import json

from httpx import ASGITransport, AsyncClient

from app.main import app


async def main() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health/")
        payload = {
            "status": response.status_code,
            "body": response.json(),
        }
        print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
