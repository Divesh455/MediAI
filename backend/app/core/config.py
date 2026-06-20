from __future__ import annotations

import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:
    def load_dotenv(path: Path) -> None:
        if not path.exists():
            return

        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue

            name, value = stripped.split("=", 1)
            os.environ.setdefault(name.strip(), value.strip().strip('"').strip("'"))


BASE_DIR = Path(__file__).resolve().parents[3]
BACKEND_DIR = BASE_DIR / "backend"

load_dotenv(BACKEND_DIR / ".env")


def get_env_path(name: str, default: Path) -> Path:
    value = os.getenv(name)
    if not value:
        return default

    path = Path(value)
    return path if path.is_absolute() else BASE_DIR / path


def get_env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return float(value)
    except ValueError:
        return default


def get_env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


APP_TITLE = os.getenv("APP_TITLE", "MediVision AI API")
FRONTEND_DIR = get_env_path("FRONTEND_DIR", BACKEND_DIR / "static")
UPLOADS_DIR = get_env_path("UPLOADS_DIR", FRONTEND_DIR / "uploads")
PROFILE_IMAGES_DIR = get_env_path("PROFILE_IMAGES_DIR", UPLOADS_DIR / "profile-images")

MODEL_DIR = get_env_path("MODEL_DIR", BASE_DIR / "Model")
DATABASE_PATH = get_env_path("DATABASE_PATH", BACKEND_DIR / "mediai.db")
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "mediai_session")
SESSION_MAX_AGE_SECONDS = get_env_int("SESSION_MAX_AGE_SECONDS", 60 * 60 * 24 * 7)
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", os.getenv("AUTH_TOKEN_SECRET", "mediAI-dev-jwt-secret"))
JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
JWT_EXPIRY_SECONDS = get_env_int("JWT_EXPIRY_SECONDS", SESSION_MAX_AGE_SECONDS)
PROFILE_IMAGE_MAX_FILE_SIZE_BYTES = get_env_int("PROFILE_IMAGE_MAX_FILE_SIZE_BYTES", 5 * 1024 * 1024)

MODEL_PATH = get_env_path("DISEASE_MODEL_PATH", MODEL_DIR / "disease_prediction_pipeline.pkl")
ENCODER_PATH = get_env_path("LABEL_ENCODER_PATH", MODEL_DIR / "label_encoder.pkl")
DESCRIPTION_PATH = get_env_path("SYMPTOM_DESCRIPTION_PATH", MODEL_DIR / "symptom_Description.csv")
PRECAUTION_PATH = get_env_path("SYMPTOM_PRECAUTION_PATH", MODEL_DIR / "symptom_precaution.csv")
TRAINING_PATH = get_env_path("TRAINING_DATA_PATH", MODEL_DIR / "Training.csv")

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
GEMINI_TEMPERATURE = get_env_float("GEMINI_TEMPERATURE", 0.3)
GEMINI_MAX_OUTPUT_TOKENS = get_env_int("GEMINI_MAX_OUTPUT_TOKENS", 1024)
X_RAY_GEMINI_MODEL = os.getenv("X_RAY_GEMINI_MODEL", "gemini-2.5-flash")
X_RAY_GEMINI_TEMPERATURE = get_env_float("X_RAY_GEMINI_TEMPERATURE", 0.2)
X_RAY_GEMINI_MAX_OUTPUT_TOKENS = get_env_int("X_RAY_GEMINI_MAX_OUTPUT_TOKENS", 2048)
X_RAY_MAX_FILE_SIZE_BYTES = get_env_int("X_RAY_MAX_FILE_SIZE_BYTES", 10 * 1024 * 1024)
X_RAY_REQUEST_TIMEOUT_SECONDS = get_env_int("X_RAY_REQUEST_TIMEOUT_SECONDS", 45)


def get_gemini_api_key() -> str | None:
    return os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY")
