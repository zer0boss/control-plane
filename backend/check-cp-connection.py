"""
Check Control Plane connection to AO Plugin
"""
import asyncio
import sys
sys.path.insert(0, '.')

from app.connectors.ao_plugin import AoPluginConnector, AoConnectionConfig, AoConnectorPool
from app.services.instance_manager import InstanceService
from app.database import AsyncSessionLocal
from app.models import Instance, InstanceStatus
from sqlalchemy import select

async def check_connection():
    # Check database for connected instances
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Instance).where(Instance.status == InstanceStatus.CONNECTED)
        )
        connected = result.scalars().all()

        print(f"Connected instances in DB: {len(connected)}")
        for inst in connected:
            print(f"  - {inst.name} ({inst.id}): {inst.status}")
            print(f"    Host: {inst.host}:{inst.port}")

        # Try to get connector pool
        from app.connectors.ao_plugin import get_connector_pool
        pool = get_connector_pool()
        print(f"\nConnector pool: {pool}")
        print(f"Pool connectors: {pool._connectors if pool else 'N/A'}")

if __name__ == "__main__":
    asyncio.run(check_connection())
