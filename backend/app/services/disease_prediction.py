from __future__ import annotations

from typing import Any

import joblib
import pandas as pd
from fastapi import HTTPException

from ..core.config import (
    DESCRIPTION_PATH,
    ENCODER_PATH,
    MODEL_PATH,
    PRECAUTION_PATH,
    TRAINING_PATH,
)


def normalize_symptom(value: str) -> str:
    return value.strip().lower().replace(" ", "_")


def format_symptom_label(value: str) -> str:
    return value.replace("_", " ").replace("  ", " ").strip().title()


model = joblib.load(MODEL_PATH)
label_encoder = joblib.load(ENCODER_PATH)

training_columns = list(pd.read_csv(TRAINING_PATH, nrows=0).columns)
feature_names = [column for column in training_columns if column != "prognosis"]
normalized_feature_map = {normalize_symptom(name): name for name in feature_names}

descriptions = pd.read_csv(DESCRIPTION_PATH).set_index("Disease")["Description"].to_dict()

precautions_df = pd.read_csv(PRECAUTION_PATH).fillna("")
precautions = {
    row["Disease"]: [
        row[column]
        for column in ["Precaution_1", "Precaution_2", "Precaution_3", "Precaution_4"]
        if row[column]
    ]
    for _, row in precautions_df.iterrows()
}


def is_valid_symptom(symptom: str) -> bool:
    return normalize_symptom(symptom) in normalized_feature_map


def get_symptom_names() -> list[str]:
    return list(dict.fromkeys(feature_names))


def get_symptom_suggestions() -> list[dict[str, str]]:
    return [
        {
            "value": symptom,
            "label": format_symptom_label(symptom),
        }
        for symptom in get_symptom_names()
    ]


def predict_from_symptoms(symptoms: list[str]) -> dict[str, Any]:
    selected_symptoms = {
        normalized_feature_map[normalize_symptom(symptom)]
        for symptom in symptoms
    }
    row = [1 if symptom in selected_symptoms else 0 for symptom in feature_names]
    input_frame = pd.DataFrame([row], columns=feature_names)

    if not hasattr(model, "predict_proba"):
        predicted_label = model.predict(input_frame)[0]
        disease = label_encoder.inverse_transform([predicted_label])[0]
        return {
            "input_symptoms": symptoms,
            "predictions": [
                {
                    "disease": disease,
                    "confidence": 1.0,
                    "description": descriptions.get(disease),
                    "precautions": precautions.get(disease, []),
                }
            ],
        }

    probabilities = model.predict_proba(input_frame)[0]
    top_indexes = probabilities.argsort()[-3:][::-1]
    predictions = []

    for index in top_indexes:
        encoded_label = model.classes_[index]
        disease = label_encoder.inverse_transform([encoded_label])[0]
        predictions.append(
            {
                "disease": disease,
                "confidence": round(float(probabilities[index]), 4),
                "description": descriptions.get(disease),
                "precautions": precautions.get(disease, []),
            }
        )

    if not predictions:
        raise HTTPException(status_code=500, detail="Model did not return a prediction.")

    return {"input_symptoms": symptoms, "predictions": predictions}
