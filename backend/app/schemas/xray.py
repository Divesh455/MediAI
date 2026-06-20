from __future__ import annotations

from pydantic import BaseModel, Field, validator


class XRayAnalysisResponse(BaseModel):
    image_type: str = Field(default="Unknown")
    findings: list[str] = Field(default_factory=list)
    abnormalities: list[str] = Field(default_factory=list)
    severity: str = Field(default="Medium")
    confidence: str = Field(default="Unavailable")
    summary: str = Field(default="")
    recommendations: list[str] = Field(default_factory=list)

    @validator("image_type", "severity", "confidence", "summary", pre=True)
    @classmethod
    def clean_text_fields(cls, value: object) -> str:
        if value is None:
            return ""
        return str(value).strip()

    @validator("findings", "abnormalities", "recommendations", pre=True)
    @classmethod
    def clean_string_lists(cls, value: object) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            cleaned = value.strip()
            return [cleaned] if cleaned else []
        if not isinstance(value, list):
            return []

        return [str(item).strip() for item in value if str(item).strip()]
