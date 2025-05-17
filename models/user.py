from tortoise.models import Model
from tortoise import fields
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import timedelta
from passlib.context import CryptContext

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class User(Model):
    id = fields.IntField(pk=True)
    username = fields.CharField(max_length=50, unique=True)
    password_hash = fields.CharField(max_length=128)
    is_admin = fields.BooleanField(default=False)
    last_login = fields.DatetimeField(null=True)
    trades = fields.IntField(default=0)
    balance = fields.CharField(max_length=50, default="0 BTC")

    def verify_password(self, plain_password: str):
        return pwd_context.verify(plain_password, self.password_hash)
