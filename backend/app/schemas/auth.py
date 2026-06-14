from __future__ import annotations

from pydantic import BaseModel, EmailStr, Field, validator


class RegisterRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=80, alias="firstName")
    last_name: str = Field(..., min_length=1, max_length=80, alias="lastName")
    email: EmailStr
    phone: str | None = Field(default="", max_length=40)
    password: str = Field(..., min_length=8, max_length=128)

    @validator("password")
    @classmethod
    def validate_password(cls, password: str) -> str:
        if not any(char.isupper() for char in password):
            raise ValueError("Password must include an uppercase letter.")
        if not any(char.islower() for char in password):
            raise ValueError("Password must include a lowercase letter.")
        if not any(char.isdigit() for char in password):
            raise ValueError("Password must include a number.")
        return password


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=1, max_length=128)


class UserResponse(BaseModel):
    id: int
    first_name: str
    last_name: str
    email: str
    phone: str | None = ""


class AuthResponse(BaseModel):
    user: UserResponse
