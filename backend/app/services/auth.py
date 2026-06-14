from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, Request, Response, status
from passlib.context import CryptContext

from backend.app.core.config import SESSION_COOKIE_NAME, SESSION_MAX_AGE_SECONDS
from backend.app.db import db_session, utc_now


password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return password_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_context.verify(password, password_hash)


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
            INSERT INTO users (first_name, last_name, email, phone, password_hash, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (first_name.strip(), last_name.strip(), email, phone.strip() if phone else "", hash_password(password), utc_now()),
        )
        user_id = cursor.lastrowid
        connection.execute(
            """
            INSERT INTO activities (user_id, activity_type, title, description, created_at)
            VALUES (?, 'auth', 'Account Created', 'Welcome to MediAI', ?)
            """,
            (user_id, utc_now()),
        )
        return connection.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()


def authenticate_user(email: str, password: str) -> dict:
    user = get_user_by_email(email)
    if not user or not verify_password(password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return user


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
    token = request.cookies.get(SESSION_COOKIE_NAME)
    if not token:
        return None

    with db_session() as connection:
        session = connection.execute(
            """
            SELECT sessions.*, users.id, users.first_name, users.last_name, users.email, users.phone, users.created_at AS user_created_at
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
            "created_at": session["user_created_at"],
        }


def require_current_user(request: Request) -> dict:
    user = get_current_user_optional(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return user


CurrentUser = Depends(require_current_user)
