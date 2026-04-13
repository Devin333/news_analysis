"""Reset raw items parse_status to pending."""
import asyncio
from app.storage.db.session import SessionFactory
from sqlalchemy import text

async def main():
    session = SessionFactory()
    try:
        await session.execute(text("UPDATE raw_items SET parse_status='pending'"))
        await session.commit()
        print("Reset done - all raw items set to pending")
    finally:
        await session.close()

asyncio.run(main())
