import asyncio
from db.database import db_manager
import psycopg2

async def sanitize():
    # Execute delete for exact matches
    def run_sync():
        with db_manager.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    DELETE FROM progress_logs 
                    WHERE topics = 'Uncategorized' 
                       OR topics ~ '^[0-9.]+$'
                """)
                deleted = cur.rowcount
                print(f"Deleted {deleted} garbage rows.")
                
    await asyncio.to_thread(run_sync)

if __name__ == "__main__":
    asyncio.run(sanitize())
