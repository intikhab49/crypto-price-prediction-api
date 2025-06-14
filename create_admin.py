import asyncio
import os
from datetime import datetime
from tortoise import Tortoise, run_async
from models.user import User, pwd_context
from config import settings

async def create_admin_user(username, password, email):
    # Connect to the database
    DATABASE_URL = os.getenv("DATABASE_URL", settings.DATABASE_URL)

    # Initialize Tortoise ORM
    await Tortoise.init(
        db_url=DATABASE_URL,
        modules={"models": ["models.user"]}
    )

    # Generate schema (this will create all tables)
    await Tortoise.generate_schemas(safe=True)

    try:
        # Create new admin user
        hashed_password = pwd_context.hash(password)
        now = datetime.now()

        await User.create(
            username=username,
            password_hash=hashed_password,
            email=email,
            is_admin=True,
            is_active=True,
            created_at=now,
            updated_at=now,
            last_login=now,
            trades=0,
            balance='0 BTC'
        )
        print(f"Admin user '{username}' created successfully.")

    except Exception as e:
        print(f"Error creating admin user: {str(e)}")
        raise
    finally:
        await Tortoise.close_connections()

if __name__ == "__main__":
    import sys

    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("Usage: python create_admin.py <username> <password> [email]")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    email = sys.argv[3] if len(sys.argv) > 3 else f"{username}@example.com"

    asyncio.run(create_admin_user(username, password, email))
