from tortoise import BaseDBAsyncClient


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS "user" (
            "id" INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
            "username" VARCHAR(50) NOT NULL UNIQUE,
            "email" VARCHAR(255) NOT NULL UNIQUE,
            "password_hash" VARCHAR(128) NOT NULL,
            "is_admin" BOOLEAN NOT NULL DEFAULT FALSE,
            "is_active" BOOLEAN NOT NULL DEFAULT TRUE,
            "created_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "updated_at" TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
            "last_login" TIMESTAMP NULL,
            "trades" INTEGER NOT NULL DEFAULT 0,
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
        DROP TABLE IF EXISTS "user";
        DROP TABLE IF EXISTS "aerich";
    """
