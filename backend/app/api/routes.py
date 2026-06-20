from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import Response as FastResponse

from ..db import db_session, utc_now
from ..schemas.auth import (
    AuthResponse,
    LoginRequest,
    ProfileMutationResponse,
    ProfilePhotoUploadResponse,
    ProfileResponse,
    ProfileUpdateRequest,
    RegisterRequest,
    UserResponse,
)
from ..schemas.chat import ChatRequest, ChatResponse
from ..schemas.disease import DiseasePredictionRequest, DiseasePredictionResponse
from ..schemas.report import ReportGenerateRequest, ReportGenerationResponse
from ..schemas.xray import XRayAnalysisResponse
from ..core.config import SESSION_COOKIE_NAME
from ..services.auth import (
    build_profile_payload,
    authenticate_user,
    create_session,
    create_auth_token,
    create_user,
    delete_session,
    require_current_user,
    split_profile_name,
    store_profile_image,
    update_user_profile,
)
from ..services.chatbot import get_chat_response
from ..services.dashboard import get_dashboard_stats, get_user_history
from ..services.disease_prediction import (
    get_symptom_names,
    get_symptom_suggestions,
    predict_from_symptoms,
)
from ..services.reports import (
    generate_report_payload,
    load_generated_report,
    log_user_activity,
    record_chat_history,
    record_disease_prediction,
    record_xray_analysis,
    render_docx_bytes,
    render_pdf_bytes,
)
from ..services.xray_analysis import analyze_xray_image


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
    return AuthResponse(token=create_auth_token(user["id"]), user=public_user(user))


@router.post("/auth/login", response_model=AuthResponse)
def login(payload: LoginRequest, response: Response) -> AuthResponse:
    user = authenticate_user(payload.email, payload.password)
    create_session(response, user["id"])
    return AuthResponse(token=create_auth_token(user["id"]), user=public_user(user))


@router.post("/auth/logout")
def logout(request: Request, response: Response) -> dict[str, bool]:
    delete_session(response, request.cookies.get(SESSION_COOKIE_NAME))
    return {"ok": True}


@router.get("/auth/me", response_model=AuthResponse)
def me(user: dict = Depends(require_current_user)) -> AuthResponse:
    return AuthResponse(user=public_user(user))


@router.get("/auth/profile", response_model=ProfileResponse)
def get_profile(user: dict = Depends(require_current_user)) -> ProfileResponse:
    return ProfileResponse(**build_profile_payload(user))


@router.put("/auth/profile", response_model=ProfileMutationResponse)
def update_profile(
    payload: ProfileUpdateRequest,
    user: dict = Depends(require_current_user),
) -> ProfileMutationResponse:
    first_name, last_name = split_profile_name(payload.name, payload.first_name, payload.last_name)
    if not first_name:
        raise HTTPException(status_code=400, detail="First name is required.")

    updated_user = update_user_profile(
        user["id"],
        first_name=first_name,
        last_name=last_name,
        email=payload.email,
        phone=payload.phone,
        gender=payload.gender,
        dob=payload.dob,
        address=payload.address,
    )
    return ProfileMutationResponse(
        message="Profile updated successfully",
        profile=ProfileResponse(**build_profile_payload(updated_user)),
    )


@router.post("/auth/profile/upload-photo", response_model=ProfilePhotoUploadResponse)
async def upload_profile_photo(
    file: UploadFile = File(...),
    user: dict = Depends(require_current_user),
) -> ProfilePhotoUploadResponse:
    try:
        image_bytes = await file.read()
        updated_user = store_profile_image(
            user["id"],
            file.filename or "profile-upload",
            file.content_type,
            image_bytes,
        )
    finally:
        await file.close()

    return ProfilePhotoUploadResponse(
        message="Profile photo uploaded successfully",
        profile_image=updated_user.get("profile_image") or "",
        profile=ProfileResponse(**build_profile_payload(updated_user)),
    )


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
        activity_id = log_user_activity(
            connection,
            user["id"],
            "prediction",
            "Disease Prediction",
            f"Analyzed symptoms: {', '.join(payload.symptoms)}. Top result: {top_prediction}",
            created_at=utc_now(),
        )
        record_disease_prediction(
            connection,
            user["id"],
            source_key=f"activity:{activity_id}",
            created_at=utc_now(),
            input_symptoms=payload.symptoms,
            predictions=result.get("predictions") or [],
        )
    return result


@router.post("/api/xray/analyze", response_model=XRayAnalysisResponse)
async def analyze_xray(file: UploadFile = File(...), user: dict = Depends(require_current_user)) -> dict:
    try:
        image_bytes = await file.read()
        result = analyze_xray_image(file.filename or "xray-upload", file.content_type, image_bytes)
    finally:
        await file.close()

    with db_session() as connection:
        activity_id = log_user_activity(
            connection,
            user["id"],
            "xray",
            "X-Ray Analysis",
            (
                f"Analyzed {file.filename or 'uploaded X-ray'}. "
                f"Type: {result['image_type']}. Severity: {result['severity']}."
            ),
            created_at=utc_now(),
        )
        record_xray_analysis(
            connection,
            user["id"],
            source_key=f"activity:{activity_id}",
            created_at=utc_now(),
            file_name=file.filename or "xray-upload",
            result=result,
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
        assistant_cursor = connection.execute(
            """
            INSERT INTO messages (conversation_id, user_id, role, content, created_at)
            VALUES (?, ?, 'assistant', ?, ?)
            """,
            (conversation_id, user["id"], response.answer, utc_now()),
        )
        assistant_message_id = assistant_cursor.lastrowid
        connection.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (utc_now(), conversation_id),
        )
        activity_id = log_user_activity(
            connection,
            user["id"],
            "chat",
            "Chatbot Conversation",
            f"Asked: {payload.message[:120]}",
            created_at=utc_now(),
        )
        record_chat_history(
            connection,
            user["id"],
            source_key=f"message:{assistant_message_id}",
            created_at=utc_now(),
            conversation_id=conversation_id,
            question=payload.message,
            answer=response.answer,
        )

    return response


@router.post("/reports/generate", response_model=ReportGenerationResponse)
def generate_report(
    payload: ReportGenerateRequest,
    user: dict = Depends(require_current_user),
) -> dict:
    if payload.user_id and payload.user_id != user["id"]:
        raise HTTPException(status_code=403, detail="You can only generate reports for your own account.")
    return generate_report_payload(user, payload.start_date, payload.end_date)


@router.get("/reports/{report_id}/pdf")
def download_report_pdf(report_id: str, user: dict = Depends(require_current_user)) -> FastResponse:
    payload = load_generated_report(report_id, user["id"])
    pdf_bytes = render_pdf_bytes(payload)
    return FastResponse(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{report_id}.pdf"'},
    )


@router.get("/reports/{report_id}/docx")
def download_report_docx(report_id: str, user: dict = Depends(require_current_user)) -> FastResponse:
    payload = load_generated_report(report_id, user["id"])
    docx_bytes = render_docx_bytes(payload)
    return FastResponse(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{report_id}.docx"'},
    )
