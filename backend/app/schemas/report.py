from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, Field, validator

from .auth import UserResponse


class ReportGenerateRequest(BaseModel):
    user_id: int | None = None
    start_date: date
    end_date: date

    @validator("end_date")
    @classmethod
    def validate_range(cls, end_date: date, values: dict[str, Any]) -> date:
        start_date = values.get("start_date")
        if start_date and end_date < start_date:
            raise ValueError("End date must be the same as or after the start date.")
        return end_date


class ReportSummary(BaseModel):
    executive_summary: str
    key_concerns: list[str] = Field(default_factory=list)
    recommended_next_actions: list[str] = Field(default_factory=list)


class DiseasePredictionReportItem(BaseModel):
    prediction_date: str
    input_symptoms: list[str] = Field(default_factory=list)
    predicted_disease: str
    confidence_score: str
    risk_level: str
    recommendations: list[str] = Field(default_factory=list)


class XRayAnalysisReportItem(BaseModel):
    upload_date: str
    body_part: str
    findings: list[str] = Field(default_factory=list)
    severity: str
    ai_explanation: str
    suggested_action: list[str] = Field(default_factory=list)


class ChatHistoryReportItem(BaseModel):
    created_at: str
    question: str
    answer: str
    topics_discussed: list[str] = Field(default_factory=list)
    follow_up_recommendations: list[str] = Field(default_factory=list)


class ReportStatistics(BaseModel):
    total_predictions: int
    total_xrays: int
    total_chats: int
    most_common_health_concern: str
    last_activity_date: str | None = None


class ReportGenerationResponse(BaseModel):
    report_id: str
    generated_at: str
    start_date: date
    end_date: date
    user: UserResponse
    summary: ReportSummary
    disease_predictions: list[DiseasePredictionReportItem] = Field(default_factory=list)
    xray_analyses: list[XRayAnalysisReportItem] = Field(default_factory=list)
    chat_history: list[ChatHistoryReportItem] = Field(default_factory=list)
    statistics: ReportStatistics
    recommendations: list[str] = Field(default_factory=list)
