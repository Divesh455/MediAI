from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from backend.app.db import db_session, utc_now
from backend.app.schemas.auth import AuthResponse, LoginRequest, RegisterRequest, UserResponse
from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.schemas.disease import DiseasePredictionRequest, DiseasePredictionResponse
from backend.app.core.config import SESSION_COOKIE_NAME
from backend.app.services.auth import (
    authenticate_user,
    create_session,
    create_user,
    delete_session,
    require_current_user,
)
from backend.app.services.chatbot import get_chat_response
from backend.app.services.dashboard import get_dashboard_stats, get_user_history
from backend.app.services.disease_prediction import (
    get_symptom_names,
    get_symptom_suggestions,
    predict_from_symptoms,
)


router = APIRouter()


def public_user(user: dict) -> UserResponse:
    return UserResponse(
        id=user["id"],
        first_name=user["first_name"],
        last_name=user["last_name"],
        email=user["email"],
        phone=user.get("phone") or "",
    )


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "MediVision AI API"}


@router.post("/auth/register", response_model=AuthResponse)
def register(payload: RegisterRequest, response: Response) -> AuthResponse:
    user = create_user(
        payload.first_name,
        payload.last_name,
        payload.email,
        payload.phone,
        payload.password,
    )
    create_session(response, user["id"])
    return AuthResponse(user=public_user(user))


@router.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response) -> AuthResponse:
    user = authenticate_user(payload.email, payload.password)
    create_session(response, user["id"])
    return AuthResponse(user=public_user(user))


@router.post("/auth/logout")
def logout(request: Request, response: Response) -> dict[str, bool]:
    delete_session(response, request.cookies.get(SESSION_COOKIE_NAME))
    return {"ok": True}


@router.get("/auth/me", response_model=AuthResponse)
def me(user: dict = Depends(require_current_user)) -> AuthResponse:
    return AuthResponse(user=public_user(user))


@router.get("/dashboard/stats")
def dashboard_stats(user: dict = Depends(require_current_user)) -> dict:
    return get_dashboard_stats(user)


@router.get("/activity/history")
def activity_history(
    date: str | None = None,
    user: dict = Depends(require_current_user),
) -> dict:
    if date:
        try:
            datetime.strptime(date, "%Y-%m-%d")
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")
    return get_user_history(user, date)


@router.get("/chat/history")
def chat_history(user: dict = Depends(require_current_user)) -> dict:
    with db_session() as connection:
        conversation = connection.execute(
            """
            SELECT id, title
            FROM conversations
            WHERE user_id = ?
            ORDER BY updated_at DESC
            LIMIT 1
            """,
            (user["id"],),
        ).fetchone()
        if not conversation:
            return {"conversation_id": None, "messages": []}

        messages = connection.execute(
            """
            SELECT role, content, created_at
            FROM messages
            WHERE conversation_id = ? AND user_id = ?
            ORDER BY created_at ASC
            LIMIT 50
            """,
            (conversation["id"], user["id"]),
        ).fetchall()

    return {
        "conversation_id": conversation["id"],
        "messages": messages,
    }


@router.get("/symptoms")
def get_symptoms(user: dict = Depends(require_current_user)) -> dict:
    return {
        "symptoms": get_symptom_names(),
        "suggestions": get_symptom_suggestions(),
        "model_input_source": "Training.csv symptom columns",
        "disease_description_source": "symptom_Description.csv",
    }


@router.post("/predict", response_model=DiseasePredictionResponse)
def predict_disease(payload: DiseasePredictionRequest, user: dict = Depends(require_current_user)) -> dict:
    result = predict_from_symptoms(payload.symptoms)
    top_prediction = result["predictions"][0]["disease"] if result.get("predictions") else "Unknown"
    with db_session() as connection:
        connection.execute(
            """
            INSERT INTO activities (user_id, activity_type, title, description, created_at)
            VALUES (?, 'prediction', 'Disease Prediction', ?, ?)
            """,
            (user["id"], f"Analyzed symptoms: {', '.join(payload.symptoms)}. Top result: {top_prediction}", utc_now()),
        )
    return result


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, user: dict = Depends(require_current_user)) -> ChatResponse:
    title = payload.message[:60] or "New conversation"
    with db_session() as connection:
        conversation_id = payload.conversation_id
        conversation = None
        if conversation_id:
            conversation = connection.execute(
                "SELECT id FROM conversations WHERE id = ? AND user_id = ?",
                (conversation_id, user["id"]),
            ).fetchone()

        if not conversation:
            cursor = connection.execute(
                """
                INSERT INTO conversations (user_id, title, created_at, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (user["id"], title, utc_now(), utc_now()),
            )
            conversation_id = cursor.lastrowid

        connection.execute(
            """
            INSERT INTO messages (conversation_id, user_id, role, content, created_at)
            VALUES (?, ?, 'user', ?, ?)
            """,
            (conversation_id, user["id"], payload.message, utc_now()),
        )

    response = get_chat_response(payload)
    response.conversation_id = conversation_id

    with db_session() as connection:
        connection.execute(
            """
            INSERT INTO messages (conversation_id, user_id, role, content, created_at)
            VALUES (?, ?, 'assistant', ?, ?)
            """,
            (conversation_id, user["id"], response.answer, utc_now()),
        )
        connection.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (utc_now(), conversation_id),
        )
        connection.execute(
            """
            INSERT INTO activities (user_id, activity_type, title, description, created_at)
            VALUES (?, 'chat', 'Chatbot Conversation', ?, ?)
            """,
            (user["id"], f"Asked: {payload.message[:120]}", utc_now()),
        )

    return response
