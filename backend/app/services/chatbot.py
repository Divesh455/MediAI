from __future__ import annotations

import json
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from fastapi import HTTPException

from ..core.config import (
    GEMINI_MAX_OUTPUT_TOKENS,
    GEMINI_MODEL,
    GEMINI_TEMPERATURE,
    get_gemini_api_key,
)
from ..schemas.chat import ChatRequest, ChatResponse


SYSTEM_PROMPT = (
    "You are MediAI Assistant, a careful and concise health information assistant. "
    "Answer general health, symptom, wellness, and medication-information questions "
    "in simple language. Do not diagnose the user, claim certainty, prescribe medicine, "
    "or suggest changing medication. Encourage urgent medical care for emergency symptoms "
    "such as chest pain, severe breathing trouble, fainting, stroke signs, heavy bleeding, "
    "severe allergic reaction, or suicidal thoughts. Recommend consulting a qualified "
    "healthcare professional for diagnosis, treatment, medication changes, or personalized advice.\n\n"
    "Output style:\n"
    "- Use this section format whenever relevant:\n"
    "  Health Summary\n"
    "  Key Information\n"
    "  Symptoms Mentioned\n"
    "  Recommended Precautions\n"
    "  Disclaimer\n"
    "- If the user asks about a disease, put the disease name under Health Summary.\n"
    "- Do not invent a confidence score for chatbot answers. Only include confidence if it is supplied by a prediction result.\n"
    "- Use short bullet points.\n"
    "- Include practical self-care only when safe and general."
)


def build_gemini_contents(payload: ChatRequest) -> list[dict]:
    contents = []

    for item in payload.history[-12:]:
        contents.append(
            {
                "role": "model" if item.role == "assistant" else "user",
                "parts": [{"text": item.content}],
            }
        )

    contents.append(
        {
            "role": "user",
            "parts": [
                {
                    "text": (
                        "User health question:\n"
                        f"{payload.message}\n\n"
                        "Give a helpful, cautious, easy-to-understand answer. "
                        "If this is a follow-up, use the previous conversation context."
                    )
                }
            ],
        }
    )
    return contents


def build_gemini_payload(payload: ChatRequest) -> dict:
    return {
        "system_instruction": {
            "parts": [{"text": SYSTEM_PROMPT}],
        },
        "contents": build_gemini_contents(payload),
        "generationConfig": {
            "temperature": GEMINI_TEMPERATURE,
            "maxOutputTokens": GEMINI_MAX_OUTPUT_TOKENS,
        },
    }


def extract_gemini_text(response_data: dict) -> str:
    candidates = response_data.get("candidates") or []
    if not candidates:
        raise HTTPException(status_code=502, detail="Gemini returned no response candidates.")

    parts = candidates[0].get("content", {}).get("parts") or []
    text_parts = [part.get("text", "") for part in parts if part.get("text")]
    if not text_parts:
        raise HTTPException(status_code=502, detail="Gemini returned an empty response.")

    return "\n".join(text_parts).strip()


def call_gemini(payload: ChatRequest) -> ChatResponse:
    api_key = get_gemini_api_key()
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="Gemini API key is not configured. Set GOOGLE_API_KEY or GEMINI_API_KEY.",
        )

    model = quote(GEMINI_MODEL, safe="")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    request = Request(
        url,
        data=json.dumps(build_gemini_payload(payload)).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        try:
            error_body = json.loads(exc.read().decode("utf-8"))
            detail = error_body.get("error", {}).get("message") or str(exc)
        except Exception:
            detail = str(exc)
        raise HTTPException(status_code=502, detail=f"Gemini request failed: {detail}") from exc
    except URLError as exc:
        raise HTTPException(status_code=502, detail=f"Gemini network error: {exc.reason}") from exc
    except TimeoutError as exc:
        raise HTTPException(status_code=504, detail="Gemini request timed out.") from exc

    return ChatResponse(answer=extract_gemini_text(response_data), model=GEMINI_MODEL)


def get_fallback_response(message: str, reason: str | None = None) -> ChatResponse:
    normalized_message = message.lower()

    if "cold" in normalized_message:
        answer = (
            "Health Summary\n"
            "Common Cold\n\n"
            "Symptoms Mentioned\n"
            "- Runny or blocked nose\n"
            "- Sneezing\n"
            "- Sore throat\n"
            "- Mild cough\n"
            "- Headache or tiredness\n"
            "- Sometimes low-grade fever\n\n"
            "Recommended Precautions\n"
            "- Rest and drink enough fluids\n"
            "- Try warm drinks or steam for comfort\n"
            "- Avoid smoke, dust, and close contact with others\n"
            "- Seek medical care for breathing difficulty, high fever, severe symptoms, or symptoms lasting longer than expected"
        )
    elif "hypertension" in normalized_message or "blood pressure" in normalized_message:
        answer = (
            "Health Summary\n"
            "Hypertension\n\n"
            "Key Information\n"
            "- Hypertension means blood pressure stays higher than normal over time\n"
            "- It often has no obvious symptoms\n"
            "- Regular blood pressure measurement is important\n\n"
            "Recommended Precautions\n"
            "- Reduce excess salt\n"
            "- Stay physically active\n"
            "- Limit alcohol and avoid tobacco\n"
            "- Manage stress\n"
            "- Follow a clinician's treatment plan"
        )
    elif "healthy" in normalized_message or "wellness" in normalized_message:
        answer = (
            "Health Summary\n"
            "General Wellness\n\n"
            "Recommended Precautions\n"
            "- Eat balanced meals\n"
            "- Drink enough water\n"
            "- Sleep well\n"
            "- Move your body regularly\n"
            "- Manage stress\n"
            "- Keep up with preventive checkups\n\n"
            "Key Information\n"
            "- Small consistent habits usually help more than sudden extreme changes"
        )
    else:
        answer = (
            "Health Summary\n"
            "I can help with general health, symptom, wellness, and medication-information questions.\n\n"
            "Key Information\n"
            "- Please describe your question or symptoms in a little more detail\n"
            "- Include how long it has been happening\n"
            "- Mention whether anything makes it better or worse"
        )

    if reason:
        answer += f"\n\nProvider Status\n- Gemini fallback is active because {reason}"

    answer += "\n\nDisclaimer\nThis is general information only and is not a substitute for professional medical advice."
    return ChatResponse(answer=answer, model="local-fallback")


def get_chat_response(payload: ChatRequest) -> ChatResponse:
    # Gemini connection fix: use the key loaded from backend/.env and call the
    # Gemini REST API directly, avoiding the previous LangChain dependency blocker.
    try:
        return call_gemini(payload)
    except HTTPException as exc:
        return get_fallback_response(payload.message, exc.detail)
    except Exception as exc:
        return get_fallback_response(payload.message, f"Unexpected Gemini error: {exc}")
