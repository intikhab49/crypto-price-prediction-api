from tortoise import fields, models
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(models.Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=50, unique=True)
    email = fields.CharField(max_length=255, unique=True)
    password_hash = fields.CharField(max_length=128)
    is_admin = fields.BooleanField(default=False)
    is_active = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)
    last_login = fields.DatetimeField(null=True)
    trades = fields.IntField(default=0)
    balance = fields.CharField(max_length=50, default='0 BTC')

    def verify_password(self, password: str) -> bool:
        return pwd_context.verify(password, self.password_hash)

    @staticmethod
    def get_password_hash(password: str) -> str:
        return pwd_context.hash(password)

    class Meta:
        table = "user"  # Match the table name in migrations

    def __str__(self):
        return f"{self.username}"