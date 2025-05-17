from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Body, Header
from pydantic import BaseModel
from models.user import User, pwd_context
import jwt
from config import settings
from typing import Optional

router = APIRouter()

class UserCreate(BaseModel):
    username: str
    password: str
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    username: str
    
    class Config:
        from_attributes = True

@router.post('/register', status_code=status.HTTP_201_CREATED, response_model=Token)
async def register(user: UserCreate):
    try:
        # Check if username already exists
        existing_user = await User.filter(username=user.username).first()
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        # Create new user with default values for new fields
        hashed_password = pwd_context.hash(user.password)
        new_user = await User.create(
            username=user.username,
            password_hash=hashed_password,
            last_login=datetime.now(),
            trades=0,
            balance="0 BTC"
        )
        
        # Generate token for immediate login
        token = jwt.encode({"sub": new_user.username}, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "username": new_user.username
        }
    except Exception as e:
        print(f"Registration error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post('/login', response_model=Token)
async def login(user: UserCreate):
    try:
        # Find user
        db_user = await User.filter(username=user.username).first()
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Verify password
        if not db_user.verify_password(user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password"
            )
        
        # Update last login time
        db_user.last_login = datetime.now()
        await db_user.save()
        
        # Generate token
        token = jwt.encode({"sub": db_user.username}, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "username": db_user.username
        }
    except Exception as e:
        print(f"Login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.post('/admin/login', response_model=Token)
async def admin_login(user: UserCreate):
    try:
        # Find user
        db_user = await User.filter(username=user.username).first()
        if not db_user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin credentials"
            )
        
        # Verify password
        if not db_user.verify_password(user.password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid admin credentials"
            )
        
        # Check if user is an admin
        if not db_user.is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User is not an admin"
            )
        
        # Generate admin token with admin claim
        token = jwt.encode(
            {"sub": db_user.username, "is_admin": True}, 
            settings.JWT_SECRET, 
            algorithm=settings.JWT_ALGORITHM
        )
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "username": db_user.username
        }
    except Exception as e:
        print(f"Admin login error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.get('/me')
async def get_current_user(token: str = Depends(lambda x: x)):
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        username = payload.get("sub")
        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )
        user = await User.filter(username=username).first()
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        return {"username": user.username}
    except jwt.JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

@router.get('/admin/users')
async def get_all_users(authorization: Optional[str] = Header(None)):
    try:
        if not authorization or not authorization.startswith('Bearer '):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header"
            )
        
        token = authorization.split(' ')[1]
        
        # Verify admin token
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            if not payload.get("is_admin"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to access user data"
                )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Fetch all users
        users = await User.all()
        return [
            {
                "id": user.id,
                "username": user.username,
                "lastLogin": user.last_login.isoformat() if user.last_login else None,
                "status": "active",
                "trades": user.trades,
                "balance": user.balance
            }
            for user in users
        ]
    except Exception as e:
        print(f"Error fetching users: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

@router.delete('/admin/users/{user_id}')
async def delete_user(user_id: int, authorization: Optional[str] = Header(None)):
    try:
        if not authorization or not authorization.startswith('Bearer '):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header"
            )
        
        token = authorization.split(' ')[1]
        
        # Verify admin token
        try:
            payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
            if not payload.get("is_admin"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Not authorized to delete users"
                )
        except jwt.JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        
        # Find the user
        user = await User.filter(id=user_id).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Delete the user
        await user.delete()
        
        return {"message": f"User with ID {user_id} has been deleted successfully"}
    except Exception as e:
        print(f"Error deleting user: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
