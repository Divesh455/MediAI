from __future__ import annotations

from datetime import date

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


class ProfileUpdateRequest(BaseModel):
    name: str | None = Field(default=None, max_length=160)
    first_name: str | None = Field(default=None, alias="firstName", max_length=80)
    last_name: str | None = Field(default=None, alias="lastName", max_length=80)
    email: EmailStr
    phone: str | None = Field(default="", max_length=40)
    gender: str | None = Field(default="", max_length=40)
    dob: date | None = None
    address: str | None = Field(default="", max_length=255)


class ProfileResponse(BaseModel):
    id: int
    name: str
    first_name: str
    last_name: str
    email: str
    phone: str | None = ""
    gender: str | None = ""
    dob: str | None = ""
    address: str | None = ""
    profile_image: str | None = ""


class ProfileMutationResponse(BaseModel):
    message: str
    profile: ProfileResponse


class ProfilePhotoUploadResponse(BaseModel):
    message: str
    profile_image: str
    profile: ProfileResponse


class AuthResponse(BaseModel):
    token: str | None = None
    user: UserResponse


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., alias="currentPassword")
    new_password: str = Field(..., min_length=8, max_length=128, alias="newPassword")

    @validator("new_password")
    @classmethod
    def validate_password(cls, password: str) -> str:
        if not any(char.isupper() for char in password):
            raise ValueError("Password must include an uppercase letter.")
        if not any(char.islower() for char in password):
            raise ValueError("Password must include a lowercase letter.")
        if not any(char.isdigit() for char in password):
            raise ValueError("Password must include a number.")
        return password
