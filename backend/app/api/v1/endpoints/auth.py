from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.core.security import verify_password, get_password_hash, create_access_token
from app.models.user import User
from app.models.role import Role
from app.schemas.user_schema import UserLogin, UserCreate, UserOut, Token

router = APIRouter()

@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_user(
    user_in: UserCreate,
    db: Session = Depends(get_db)
) -> Any:
    """
    Registers a new user into the system.
    By default, new users receive the 'Usuario' role pending administrator assignment.
    """
    # Check if username already exists
    existing_username = db.query(User).filter(User.username == user_in.username).first()
    if existing_username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El nombre de usuario ya está registrado."
        )

    # Check if email exists
    if user_in.email:
        existing_email = db.query(User).filter(User.email == user_in.email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="El correo electrónico ya está registrado."
            )

    # Automatically assign default 'Usuario' role
    default_role = db.query(Role).filter(Role.name == "Usuario").first()
    assigned_role_id = default_role.id if default_role else None
    role_name = default_role.name if default_role else "Usuario"

    # Hash password
    hashed_pwd = get_password_hash(user_in.password)

    # Create new User instance (Not admin, role='Usuario')
    new_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hashed_pwd,
        is_admin=False,
        is_active=True,
        role_id=assigned_role_id
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    user_out = UserOut.model_validate(new_user)
    user_out.role_name = role_name
    return user_out

@router.post("/login", response_model=Token)
def login_user(
    login_data: UserLogin,
    db: Session = Depends(get_db)
) -> Any:
    """Authenticates user against PostgreSQL metadata database and returns JWT token."""
    user = db.query(User).filter(User.username == login_data.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos."
        )

    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos."
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La cuenta de usuario está desactivada."
        )

    access_token = create_access_token(subject=user.id)

    role_name = user.role.name if user.role else ("Super Administrador" if user.is_admin else "Usuario")
    user_out = UserOut.model_validate(user)
    user_out.role_name = role_name

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user_out
    }

@router.get("/me", response_model=UserOut)
def read_current_user_profile(
    current_user: User = Depends(get_current_user)
) -> Any:
    """Returns profile of currently authenticated user."""
    role_name = current_user.role.name if current_user.role else ("Super Administrador" if current_user.is_admin else "Usuario")
    user_out = UserOut.model_validate(current_user)
    user_out.role_name = role_name
    return user_out

@router.get("/roles")
def list_available_roles(
    db: Session = Depends(get_db)
) -> Any:
    """Lists available roles for administration management."""
    roles = db.query(Role).all()
    return [{"id": r.id, "name": r.name, "description": r.description} for r in roles]
