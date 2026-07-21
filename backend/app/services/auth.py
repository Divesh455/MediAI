from __future__ import annotations

import binascii
import base64
import hashlib
import hmac
import json
import secrets
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from fastapi import Depends, HTTPException, Request, Response, UploadFile, status
from passlib.context import CryptContext

from ..core.config import (
    JWT_ALGORITHM,
    JWT_EXPIRY_SECONDS,
    JWT_SECRET_KEY,
    PROFILE_IMAGE_MAX_FILE_SIZE_BYTES,
    PROFILE_IMAGES_DIR,
    SESSION_COOKIE_NAME,
    SESSION_MAX_AGE_SECONDS,
)
from ..db import db_session, utc_now
from .reports import log_user_activity


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_context.verify(password, password_hash)


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _base64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(f"{data}{padding}".encode("ascii"))


def _json_b64url(payload: dict) -> str:
    return _base64url_encode(json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8"))


def create_auth_token(user_id: int) -> str:
    issued_at = int(datetime.now(timezone.utc).timestamp())
    header = {"alg": JWT_ALGORITHM, "typ": "JWT"}
    payload = {
        "sub": str(user_id),
        "iat": issued_at,
        "exp": issued_at + JWT_EXPIRY_SECONDS,
    }
    signing_input = f"{_json_b64url(header)}.{_json_b64url(payload)}".encode("ascii")
    signature = hmac.new(JWT_SECRET_KEY.encode("utf-8"), signing_input, hashlib.sha256).digest()
    return f"{signing_input.decode('ascii')}.{_base64url_encode(signature)}"


def verify_auth_token(token: str) -> dict | None:
    try:
        header_part, payload_part, signature_part = token.split(".", 2)
        header = json.loads(_base64url_decode(header_part))
        if header.get("alg") != JWT_ALGORITHM:
            return None

        signing_input = f"{header_part}.{payload_part}".encode("ascii")
        expected_signature = hmac.new(
            JWT_SECRET_KEY.encode("utf-8"),
            signing_input,
            hashlib.sha256,
        ).digest()
        provided_signature = _base64url_decode(signature_part)
        if not hmac.compare_digest(expected_signature, provided_signature):
            return None

        payload = json.loads(_base64url_decode(payload_part))
        expires_at = int(payload.get("exp") or 0)
        if expires_at <= int(datetime.now(timezone.utc).timestamp()):
            return None
        return payload
    except (ValueError, json.JSONDecodeError, TypeError, binascii.Error):
        return None


def normalize_email(email: str) -> str:
    return email.strip().lower()


def get_user_by_email(email: str) -> dict | None:
    with db_session() as connection:
        return connection.execute(
            "SELECT * FROM users WHERE email = ?",
            (normalize_email(email),),
        ).fetchone()


def get_user_by_id(user_id: int) -> dict | None:
    with db_session() as connection:
        return connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def create_user(first_name: str, last_name: str, email: str, phone: str | None, password: str) -> dict:
    email = normalize_email(email)
    if get_user_by_email(email):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    with db_session() as connection:
        cursor = connection.execute(
            """
            INSERT INTO users (
                first_name, last_name, email, phone, password_hash, created_at, dob, gender, address, profile_image
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                first_name.strip(),
                last_name.strip(),
                email,
                phone.strip() if phone else "",
                hash_password(password),
                utc_now(),
                "",
                "",
                "",
                "",
            ),
        )
        user_id = cursor.lastrowid
        log_user_activity(
            connection,
            user_id,
            "auth",
            "Account Created",
            "Welcome to MediAI",
            created_at=utc_now(),
        )
        return connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def authenticate_user(email: str, password: str) -> dict:
    user = get_user_by_email(email)
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return user


def get_user_from_auth_header(request: Request) -> dict | None:
    authorization = request.headers.get("Authorization", "")
    if not authorization.startswith("Bearer "):
        return None

    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        return None

    payload = verify_auth_token(token)
    if not payload:
        return None

    try:
        user_id = int(payload.get("sub"))
    except (TypeError, ValueError):
        return None

    user = get_user_by_id(user_id)
    if not user:
        return None
    user.pop("password_hash", None)
    return user


def normalize_profile_text(value: str | None) -> str:
    return value.strip() if value else ""


def build_profile_payload(user: dict) -> dict:
    first_name = normalize_profile_text(user.get("first_name"))
    last_name = normalize_profile_text(user.get("last_name"))
    name = " ".join(part for part in [first_name, last_name] if part).strip()

    return {
        "id": user["id"],
        "name": name,
        "first_name": first_name,
        "last_name": last_name,
        "email": user.get("email", ""),
        "phone": normalize_profile_text(user.get("phone")),
        "gender": normalize_profile_text(user.get("gender")),
        "dob": normalize_profile_text(user.get("dob")),
        "address": normalize_profile_text(user.get("address")),
        "profile_image": normalize_profile_text(user.get("profile_image")),
    }


def split_profile_name(name: str | None, first_name: str | None, last_name: str | None) -> tuple[str, str]:
    resolved_first = normalize_profile_text(first_name)
    resolved_last = normalize_profile_text(last_name)
    if resolved_first and resolved_last:
        return resolved_first, resolved_last

    source_name = normalize_profile_text(name)
    if not source_name:
        return resolved_first, resolved_last

    parts = [part for part in source_name.split() if part]
    if not resolved_first and parts:
        resolved_first = parts[0]
    if not resolved_last and len(parts) > 1:
        resolved_last = " ".join(parts[1:])
    return resolved_first, resolved_last


def update_user_profile(
    user_id: int,
    *,
    first_name: str,
    last_name: str,
    email: str,
    phone: str | None,
    gender: str | None,
    dob: date | None,
    address: str | None,
) -> dict:
    normalized_email = normalize_email(email)
    existing_user = get_user_by_email(normalized_email)
    if existing_user and existing_user["id"] != user_id:
        raise HTTPException(status_code=409, detail="An account with this email already exists.")

    with db_session() as connection:
        connection.execute(
            """
            UPDATE users
            SET first_name = ?, last_name = ?, email = ?, phone = ?, gender = ?, dob = ?, address = ?
            WHERE id = ?
            """,
            (
                normalize_profile_text(first_name),
                normalize_profile_text(last_name),
                normalized_email,
                normalize_profile_text(phone),
                normalize_profile_text(gender),
                dob.isoformat() if dob else "",
                normalize_profile_text(address),
                user_id,
            ),
        )

    updated_user = get_user_by_id(user_id)
    if not updated_user:
        raise HTTPException(status_code=404, detail="Profile not found.")
    updated_user.pop("password_hash", None)
    return updated_user


def store_profile_image(user_id: int, filename: str, content_type: str | None, image_bytes: bytes) -> dict:
    if len(image_bytes) > PROFILE_IMAGE_MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail="Profile image exceeds the maximum file size.")

    file_suffix = Path(filename or "").suffix.lower()
    allowed_suffixes = {".jpg", ".jpeg", ".png"}
    allowed_content_types = {"image/jpeg", "image/png"}
    if file_suffix not in allowed_suffixes or (content_type or "").lower() not in allowed_content_types:
        raise HTTPException(status_code=400, detail="Only JPG, JPEG, and PNG images are allowed.")

    PROFILE_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
    safe_suffix = ".jpg" if file_suffix not in allowed_suffixes else file_suffix
    image_name = f"profile-{user_id}-{secrets.token_hex(12)}{safe_suffix}"
    image_path = PROFILE_IMAGES_DIR / image_name
    image_path.write_bytes(image_bytes)

    profile_image_url = f"/uploads/profile-images/{image_name}"
    with db_session() as connection:
        connection.execute(
            "UPDATE users SET profile_image = ? WHERE id = ?",
            (profile_image_url, user_id),
        )

    updated_user = get_user_by_id(user_id)
    if not updated_user:
        raise HTTPException(status_code=404, detail="Profile not found.")
    updated_user.pop("password_hash", None)
    return updated_user


def create_session(response: Response, user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=SESSION_MAX_AGE_SECONDS)
    with db_session() as connection:
        connection.execute(
            "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, user_id, utc_now(), expires_at.isoformat()),
        )

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        max_age=SESSION_MAX_AGE_SECONDS,
        path="/",
    )
    return token


def delete_session(response: Response, token: str | None) -> None:
    if token:
        with db_session() as connection:
            connection.execute("DELETE FROM sessions WHERE token = ?", (token,))
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")


def get_current_user_optional(request: Request) -> dict | None:
    user = get_user_from_auth_header(request)
    if user:
        return user

    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None

    with db_session() as connection:
        session = connection.execute(
            """
            SELECT
                sessions.*,
                users.id,
                users.first_name,
                users.last_name,
                users.email,
                users.phone,
                users.dob,
                users.gender,
                users.address,
                users.profile_image,
                users.created_at AS user_created_at
            FROM sessions
            JOIN users ON users.id = sessions.user_id
            WHERE sessions.token = ?
            """,
            (token,),
        ).fetchone()

        if not session:
            return None

        expires_at = datetime.fromisoformat(session["expires_at"])
        if expires_at <= datetime.now(timezone.utc):
            connection.execute("DELETE FROM sessions WHERE token = ?", (token,))
            return None

        return {
            "id": session["user_id"],
            "first_name": session["first_name"],
            "last_name": session["last_name"],
            "email": session["email"],
            "phone": session["phone"],
            "dob": session["dob"],
            "gender": session["gender"],
            "address": session["address"],
            "profile_image": session["profile_image"],
            "created_at": session["user_created_at"],
        }


def require_current_user(request: Request) -> dict:
    user = get_current_user_optional(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return user


CurrentUser = Depends(require_current_user)


def change_user_password(user_id: int, new_password: str) -> None:
    hashed = hash_password(new_password)
    with db_session() as connection:
        connection.execute(
            "UPDATE users SET password_hash = ? WHERE id = ?",
            (hashed, user_id),
        )


def delete_user_account(user_id: int) -> None:
    with db_session() as connection:
        connection.execute(
            "DELETE FROM users WHERE id = ?",
            (user_id,),
        )
