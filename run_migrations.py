import asyncio
from tortoise import Tortoise
from config import settings, TORTOISE_ORM

async def run_migrations():
    # Initialize Tortoise ORM
    await Tortoise.init(config=TORTOISE_ORM)
    
    # Create the new columns
    conn = Tortoise.get_connection("default")
    
    # Get existing columns
    columns = await conn.execute_query("PRAGMA table_info(user)")
    existing_columns = [col[1] for col in columns[1]]  # col[1] is the column name
    
    # Add columns if they don't exist
    if "last_login" not in existing_columns:
        await conn.execute_query('ALTER TABLE "user" ADD COLUMN "last_login" TIMESTAMP NULL')
    
    if "trades" not in existing_columns:
        await conn.execute_query('ALTER TABLE "user" ADD COLUMN "trades" INT NOT NULL DEFAULT 0')
    
    if "balance" not in existing_columns:
        await conn.execute_query('ALTER TABLE "user" ADD COLUMN "balance" VARCHAR(50) NOT NULL DEFAULT "0 BTC"')
    
    print("Migrations completed successfully!")
    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(run_migrations()) 