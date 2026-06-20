from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from fastapi import HTTPException

from ..core.config import (
    X_RAY_GEMINI_MAX_OUTPUT_TOKENS,
    X_RAY_GEMINI_MODEL,
    X_RAY_GEMINI_TEMPERATURE,
    X_RAY_MAX_FILE_SIZE_BYTES,
    X_RAY_REQUEST_TIMEOUT_SECONDS,
    get_gemini_api_key,
)


ALLOWED_FILE_EXTENSIONS = {".jpg", ".jpeg", ".png"}
ALLOWED_MIME_TYPES = {
    "image/jpeg": "image/jpeg",
    "image/jpg": "image/jpeg",
    "image/png": "image/png",
}

XRAY_PROMPT = (
    "Analyze this medical X-ray image and provide:\n"
    "1. Image type (Chest, Hand, Leg, Spine, Dental, etc.)\n"
    "2. Visible findings\n"
    "3. Potential abnormalities\n"
    "4. Severity assessment (Low, Medium, High)\n"
    "5. Recommendations\n"
    "6. Medical-style summary report\n"
    "7. Confidence level for observations\n\n"
    "Important:\n"
    "- Clearly state this is AI-generated analysis and not a medical diagnosis.\n"
    "- Return results in structured JSON format.\n\n"
    "Keep the response concise:\n"
    "- Use short clinical phrases, not long paragraphs.\n"
    "- Limit findings to a maximum of 5 short bullet-style items.\n"
    "- Limit abnormalities to a maximum of 5 short bullet-style items.\n"
    "- Limit recommendations to a maximum of 5 short bullet-style items.\n"
    "- Keep each item under 16 words when possible.\n\n"
    "Return JSON that matches this shape exactly:\n"
    "{\n"
    '  "image_type": "Chest",\n'
    '  "findings": ["Finding 1"],\n'
    '  "abnormalities": ["Abnormality 1"],\n'
    '  "severity": "Low",\n'
    '  "confidence": "84%",\n'
    '  "summary": "AI-generated medical-style summary report. This is not a medical diagnosis.",\n'
    '  "recommendations": ["Recommendation 1"]\n'
    "}\n\n"
    "If image quality is limited or the anatomy is unclear, say that clearly, lower the "
    "confidence, and keep the response medically cautious."
)

def resolve_mime_type(filename: str, content_type: str | None) -> str:
    extension = Path(filename or "").suffix.lower()
    normalized_content_type = (content_type or "").strip().lower()

    if extension not in ALLOWED_FILE_EXTENSIONS and normalized_content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Please upload a JPG, JPEG, or PNG X-ray image.",
        )

    if normalized_content_type in ALLOWED_MIME_TYPES:
        return ALLOWED_MIME_TYPES[normalized_content_type]

    if extension in {".jpg", ".jpeg"}:
        return "image/jpeg"
    return "image/png"


def validate_image_bytes(image_bytes: bytes) -> None:
    if not image_bytes:
        raise HTTPException(status_code=400, detail="The uploaded image is empty.")

    if len(image_bytes) > X_RAY_MAX_FILE_SIZE_BYTES:
        max_megabytes = X_RAY_MAX_FILE_SIZE_BYTES // (1024 * 1024)
        raise HTTPException(
            status_code=413,
            detail=f"File size exceeds the {max_megabytes}MB limit for X-ray uploads.",
        )


def build_xray_payload(image_bytes: bytes, mime_type: str) -> dict:
    encoded_image = base64.b64encode(image_bytes).decode("utf-8")
    return {
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "inline_data": {
                            "mime_type": mime_type,
                            "data": encoded_image,
                        }
                    },
                    {"text": XRAY_PROMPT},
                ],
            }
        ],
        "generationConfig": {
            "temperature": X_RAY_GEMINI_TEMPERATURE,
            "maxOutputTokens": X_RAY_GEMINI_MAX_OUTPUT_TOKENS,
        },
    }


def extract_gemini_text(response_data: dict) -> str:
    candidates = response_data.get("candidates") or []
    if not candidates:
        prompt_feedback = response_data.get("promptFeedback") or {}
        block_reason = prompt_feedback.get("blockReason")
        if block_reason:
            raise HTTPException(status_code=502, detail=f"Gemini blocked the X-ray analysis: {block_reason}.")
        raise HTTPException(status_code=502, detail="Gemini returned no response candidates.")

    parts = candidates[0].get("content", {}).get("parts") or []
    text_parts = [part.get("text", "") for part in parts if part.get("text")]
    if not text_parts:
        raise HTTPException(status_code=502, detail="Gemini returned an empty response.")

    return "\n".join(text_parts).strip()


def parse_json_text(payload_text: str) -> dict:
    try:
        data = json.loads(payload_text)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass

    fenced_match = re.search(r"```json\s*(\{.*\})\s*```", payload_text, flags=re.DOTALL | re.IGNORECASE)
    if fenced_match:
        return json.loads(fenced_match.group(1))

    first_brace = payload_text.find("{")
    last_brace = payload_text.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        return json.loads(payload_text[first_brace:last_brace + 1])

    raise HTTPException(status_code=502, detail="Gemini did not return valid JSON for the X-ray analysis.")


def normalize_string_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        cleaned = value.strip()
        return [cleaned] if cleaned else []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    return []


def shorten_text(value: str, max_length: int = 120) -> str:
    cleaned = re.sub(r"\s+", " ", value).strip().rstrip(".")
    if not cleaned:
        return ""

    if len(cleaned) <= max_length:
        return cleaned

    shortened = cleaned[: max_length - 3].rsplit(" ", 1)[0].strip()
    return (shortened or cleaned[: max_length - 3]).rstrip(",;:-") + "..."


def compact_list(value: object, max_items: int = 5, max_length: int = 120) -> list[str]:
    items = normalize_string_list(value)
    compacted = [shorten_text(item, max_length=max_length) for item in items]
    return [item for item in compacted if item][:max_items]


def normalize_severity(value: object) -> str:
    normalized = str(value or "").strip().lower()
    if normalized == "low":
        return "Low"
    if normalized == "high":
        return "High"
    if normalized == "medium":
        return "Medium"
    return "Medium"


def normalize_confidence(value: object) -> str:
    if value is None:
        return "Unavailable"

    if isinstance(value, (int, float)):
        score = round(float(value), 2)
        if score <= 1:
            score *= 100
        score = min(max(score, 0), 100)
        return f"{score:.0f}%"

    cleaned = str(value).strip()
    return cleaned or "Unavailable"


def normalize_summary(value: object, image_type: str, severity: str) -> str:
    summary = str(value or "").strip()
    if summary:
        return summary

    return (
        f"AI-generated X-ray analysis for a possible {image_type or 'medical'} image. "
        f"Estimated severity: {severity}. This is not a medical diagnosis."
    )


def sanitize_xray_result(data: dict) -> dict:
    image_type = str(data.get("image_type") or "Unknown").strip() or "Unknown"
    findings = compact_list(data.get("findings"), max_items=5, max_length=90)
    abnormalities = compact_list(data.get("abnormalities"), max_items=5, max_length=90)
    severity = normalize_severity(data.get("severity"))
    confidence = normalize_confidence(data.get("confidence"))
    recommendations = compact_list(data.get("recommendations"), max_items=5, max_length=90)
    summary = shorten_text(normalize_summary(data.get("summary"), image_type, severity), max_length=260)

    if not findings and not abnormalities and not summary:
        raise HTTPException(status_code=502, detail="Gemini returned an empty X-ray analysis.")

    if not findings:
        findings = ["No clear findings were extracted from the AI response."]

    if not recommendations:
        recommendations = [
            "Consult a qualified healthcare professional or radiologist for formal interpretation."
        ]

    return {
        "image_type": image_type,
        "findings": findings,
        "abnormalities": abnormalities,
        "severity": severity,
        "confidence": confidence,
        "summary": summary,
        "recommendations": recommendations,
    }


def request_gemini_xray_analysis(image_bytes: bytes, mime_type: str) -> dict:
    api_key = get_gemini_api_key()
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="Gemini API key is not configured. Set GOOGLE_API_KEY or GEMINI_API_KEY.",
        )

    model = quote(X_RAY_GEMINI_MODEL, safe="")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    request = Request(
        url,
        data=json.dumps(build_xray_payload(image_bytes, mime_type)).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=X_RAY_REQUEST_TIMEOUT_SECONDS) as response:
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
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=502, detail="Gemini returned malformed JSON.") from exc

    return sanitize_xray_result(parse_json_text(extract_gemini_text(response_data)))


def analyze_xray_image(filename: str, content_type: str | None, image_bytes: bytes) -> dict:
    mime_type = resolve_mime_type(filename, content_type)
    validate_image_bytes(image_bytes)
    return request_gemini_xray_analysis(image_bytes, mime_type)
