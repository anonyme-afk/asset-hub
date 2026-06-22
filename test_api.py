import asyncio
import httpx

async def fetch():
    async with httpx.AsyncClient() as client:
        resp = await client.get("https://api.polyhaven.com/assets")
        assets = resp.json()
        print("TOTAL:", len(assets))
        first_key = list(assets.keys())[0]
        print(first_key, assets[first_key])

asyncio.run(fetch())
