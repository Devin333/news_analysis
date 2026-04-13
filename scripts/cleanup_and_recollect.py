"""Clean up all data and prepare for fresh collection."""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main():
    from sqlalchemy import text
    from app.storage.db.session import SessionFactory

    async with SessionFactory() as session:
        # Delete in correct order (foreign keys)
        await session.execute(text("DELETE FROM topic_items"))
        await session.execute(text("DELETE FROM normalized_items"))
        await session.execute(text("DELETE FROM topics"))
        await session.execute(text("DELETE FROM raw_items"))
        await session.commit()
        print("All data cleaned successfully.")


if __name__ == "__main__":
    asyncio.run(main())
