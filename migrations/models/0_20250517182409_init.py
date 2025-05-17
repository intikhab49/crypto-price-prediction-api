from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "user" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "username" VARCHAR(50) NOT NULL UNIQUE,
    "password_hash" VARCHAR(128) NOT NULL,
    "is_admin" INT NOT NULL DEFAULT 0,
    "last_login" TIMESTAMP,
    "trades" INT NOT NULL DEFAULT 0,
    "balance" VARCHAR(50) NOT NULL DEFAULT '0 BTC'
);
CREATE TABLE IF NOT EXISTS "aerich" (
    "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
    "version" VARCHAR(255) NOT NULL,
    "app" VARCHAR(100) NOT NULL,
    "content" JSON NOT NULL
);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        """
