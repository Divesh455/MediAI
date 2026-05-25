from __future__ import annotations

from fastapi import APIRouter

from backend.app.schemas.chat import ChatRequest, ChatResponse
from backend.app.schemas.disease import DiseasePredictionRequest, DiseasePredictionResponse
from backend.app.services.chatbot import get_chat_response
from backend.app.services.disease_prediction import (
    get_symptom_names,
    get_symptom_suggestions,
    predict_from_symptoms,
)


router = APIRouter()


@router.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok", "service": "MediVision AI API"}


@router.get("/symptoms")
def get_symptoms() -> dict:
    return {
        "symptoms": get_symptom_names(),
        "suggestions": get_symptom_suggestions(),
        "model_input_source": "Training.csv symptom columns",
        "disease_description_source": "symptom_Description.csv",
    }


@router.post("/predict", response_model=DiseasePredictionResponse)
def predict_disease(payload: DiseasePredictionRequest) -> dict:
    return predict_from_symptoms(payload.symptoms)


@router.post("/chat", response_model=ChatResponse)
def chat(payload: ChatRequest) -> ChatResponse:
    return get_chat_response(payload)
