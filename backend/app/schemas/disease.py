from __future__ import annotations

from pydantic import BaseModel, Field, validator

from ..services.disease_prediction import is_valid_symptom, normalize_symptom


class DiseasePredictionRequest(BaseModel):
    symptoms: list[str] = Field(..., min_length=1, max_length=5)

    @validator("symptoms")
    @classmethod
    def validate_symptoms(cls, symptoms: list[str]) -> list[str]:
        cleaned = [symptom.strip() for symptom in symptoms if symptom.strip()]
        if not cleaned:
            raise ValueError("Please provide at least one symptom.")
        if len(cleaned) > 5:
            raise ValueError("Please provide up to 5 symptoms.")
        if len({normalize_symptom(symptom) for symptom in cleaned}) != len(cleaned):
            raise ValueError("Please provide different symptoms.")

        unknown = [symptom for symptom in cleaned if not is_valid_symptom(symptom)]
        if unknown:
            raise ValueError(f"Unknown symptom(s): {', '.join(unknown)}.")

        return cleaned


class DiseasePrediction(BaseModel):
    disease: str
    confidence: float
    description: str | None = None
    precautions: list[str] = Field(default_factory=list)


class DiseasePredictionResponse(BaseModel):
    input_symptoms: list[str]
    predictions: list[DiseasePrediction]
