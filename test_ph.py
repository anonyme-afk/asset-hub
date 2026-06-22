import asyncio
import sys
sys.path.insert(0, '/app/applet/asset-hub')
from asset_hub.connectors.polyhaven import PolyHavenConnector
async def foo():
    try:
        conn = PolyHavenConnector()
        res = await conn.search('rock')
        print(res)
    except Exception as e:
        print("ERROR:", e)
        raise
asyncio.run(foo())
