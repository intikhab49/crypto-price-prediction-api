from tortoise import BaseDBAsyncClient, run_async
from tortoise.backends.base.schema_generator import BaseSchemaGenerator
from tortoise.migration import Migration

class MigrationSchemaGenerator(BaseSchemaGenerator):
    def __init__(self, client: BaseDBAsyncClient) -> None:
        super().__init__(client)

class Migration(Migration):
    async def up(self, db: BaseDBAsyncClient) -> str:
        return """
        ALTER TABLE "user" ADD COLUMN "last_login" TIMESTAMP NULL;
        ALTER TABLE "user" ADD COLUMN "trades" INT NOT NULL DEFAULT 0;
        ALTER TABLE "user" ADD COLUMN "balance" VARCHAR(50) NOT NULL DEFAULT '0 BTC';
        """

    async def down(self, db: BaseDBAsyncClient) -> str:
        return """
        ALTER TABLE "user" DROP COLUMN "last_login";
        ALTER TABLE "user" DROP COLUMN "trades";
        ALTER TABLE "user" DROP COLUMN "balance";
        """ 