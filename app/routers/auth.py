import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import ACCESS_TOKEN_EXPIRE_MINUTES, create_access_token, get_password_hash, verify_password
from app.database import get_db
from app.models import UserDB
from app.schemas import TokenResponse, UserCreate, UserLogin

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Register a new user and return a JWT token."""
    db_user = db.query(UserDB).filter(UserDB.mobile_number == user_in.mobile_number).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Mobile number already registered")

    hashed_pwd = get_password_hash(user_in.password)
    new_user = UserDB(
        name=user_in.name,
        mobile_number=user_in.mobile_number,
        hashed_password=hashed_pwd,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token_expires = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(data={"sub": new_user.mobile_number}, expires_delta=token_expires)
    return {"access_token": token, "token_type": "bearer", "user": new_user}


@router.post("/login", response_model=TokenResponse)
def login(login_in: UserLogin, db: Session = Depends(get_db)):
    """Authenticate user and return a JWT token."""
    user = db.query(UserDB).filter(UserDB.mobile_number == login_in.mobile_number).first()
    if not user or not verify_password(login_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect mobile number or password",
        )
    token_expires = datetime.timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    token = create_access_token(data={"sub": user.mobile_number}, expires_delta=token_expires)
    return {"access_token": token, "token_type": "bearer", "user": user}
