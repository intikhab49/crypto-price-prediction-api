import asyncio
from tortoise import Tortoise
from config import settings, TORTOISE_ORM

async def run_migrations():
    # Initialize Tortoise ORM
    await Tortoise.init(config=TORTOISE_ORM)
    
    # Create schema
    await Tortoise.generate_schemas(safe=True)
    
    print("Migrations completed successfully!")
    await Tortoise.close_connections()

if __name__ == "__main__":
    asyncio.run(run_migrations())