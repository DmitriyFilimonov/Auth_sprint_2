import re
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator, constr, Field
from src.models.entity import UserRole


class PasswordValidator:
    def validate_password(cls, v):
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one digit")
        return v


class LoginValidator:
    def validate_login(cls, v):
        if len(v) < 3:
            raise ValueError("Login must be at least 3 characters long")
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError("Login can only contain letters, numbers and underscores")
        return v


class UserBase(BaseModel):
    login: str
    email: EmailStr
    first_name: str
    last_name: str


class UserCreate(UserBase):
    password: str = Field(..., min_length=10, max_length=72)

    @field_validator("password")
    def validate_password(cls, v):
        return PasswordValidator().validate_password(v)

    @field_validator("login")
    def validate_login(cls, v):
        return LoginValidator().validate_login(v)


class UserInDB(UserBase):
    id: UUID

    model_config = ConfigDict(from_attributes=True)


class UserChangePassword(BaseModel):
    current_password: str
    new_password: constr(min_length=10)

    @field_validator("new_password")
    def validate_new_password(cls, v):
        return PasswordValidator().validate_password(v)


class UserChangeLogin(BaseModel):
    new_login: str

    @field_validator("new_login")
    def validate_new_login(cls, v):
        return LoginValidator().validate_login(v)


class LoginSchema(BaseModel):
    login: str
    password: str


class RoleCreate(BaseModel):
    user_id: UUID
    role: UserRole


class RoleInDB(BaseModel):
    id: UUID
    user_id: UUID
    role: UserRole

    model_config = ConfigDict(from_attributes=True)


class RoleUpdate(BaseModel):
    role: UserRole
