import asyncio
from app.database import AsyncSessionLocal
from app.models import Message
from sqlalchemy import select

async def check():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Message)
            .order_by(Message.created_at.desc())
            .limit(10)
        )
        messages = result.scalars().all()
        for m in messages:
            print(f"[{m.created_at}] {m.role}: {m.content[:80]}...")

asyncio.run(check())
