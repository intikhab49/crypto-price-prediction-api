from tortoise import BaseDBAsyncClient
from tortoise.backends.base.schema_generator import BaseSchemaGenerator
from tortoise.migration import Migration

class MigrationSchemaGenerator(BaseSchemaGenerator):
    def __init__(self, client: BaseDBAsyncClient) -> None:
        super().__init__(client)

class Migration(Migration):
    async def up(self, db: BaseDBAsyncClient) -> str:
        return """
        ALTER TABLE "user" ADD COLUMN "is_active" BOOLEAN NOT NULL DEFAULT True;
        ALTER TABLE "user" ADD COLUMN "created_at" TIMESTAMP NULL;
        ALTER TABLE "user" ADD COLUMN "updated_at" TIMESTAMP NULL;
        ALTER TABLE "user" ADD COLUMN "email" VARCHAR(255) NOT NULL DEFAULT 'admin@example.com';
        """

    async def down(self, db: BaseDBAsyncClient) -> str:
        return """
        ALTER TABLE "user" DROP COLUMN "is_active";
        ALTER TABLE "user" DROP COLUMN "created_at";
        ALTER TABLE "user" DROP COLUMN "updated_at";
        ALTER TABLE "user" DROP COLUMN "email";
        """