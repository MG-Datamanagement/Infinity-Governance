"""
Database utilities for Infinity Governance API
"""
import asyncpg
from app.config import PG_HOST, PG_PORT, PG_DB, PG_USER, PG_PASS

# Global database pool
db_pool = None


async def get_db_pool():
    """Get or create the database connection pool"""
    global db_pool
    if db_pool is None:
        db_pool = await asyncpg.create_pool(
            host=PG_HOST,
            port=int(PG_PORT),
            database=PG_DB,
            user=PG_USER,
            password=PG_PASS
        )
    return db_pool


async def close_db_pool():
    """Close the database connection pool"""
    global db_pool
    if db_pool is not None:
        await db_pool.close()
        db_pool = None
