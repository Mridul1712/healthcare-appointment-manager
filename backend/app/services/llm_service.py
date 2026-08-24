import json
import os
from typing import Any, Dict, List

import httpx
from pydantic import BaseModel, Field


class PreVisitSummaryModel(BaseModel):
    urgency_level: str = Field(...)
    chief_complaint: str
    suggested_questions: List[str] = Field(...)


class PostVisitSummaryModel(BaseModel):
    summary: str
    medication_schedule: List[Dict[str, str]]
    follow_up_steps: List[str]


def _get_llm_api_key() -> str:
    return os.getenv("LLM_API_KEY") or os.getenv("OPENAI_API_KEY") or ""


def _get_llm_base_url() -> str:
    return os.getenv("LLM_BASE_URL") or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"


def _fallback_pre_visit_summary() -> Dict[str, Any]:
    return {
        "urgency_level": "Low",
        "chief_complaint": "Administrative intake gathered",
        "suggested_questions": [
            "What symptoms started first?",
            "How long have they been present?",
            "Are there any factors that make them worse?",
        ],
        "status": "PENDING",
        "fallback": True,
    }


def _fallback_post_visit_summary(notes: str, medications: List[Dict[str, str]] | None = None) -> Dict[str, Any]:
    return {
        "summary": notes or "Follow-up instructions were documented by the clinician.",
        "medication_schedule": medications or [],
        "follow_up_steps": ["Keep taking prescribed medications as directed.", "Return if symptoms worsen."],
        "status": "PENDING",
        "fallback": True,
    }


def _call_llm(prompt: str, model: str, response_schema: type[BaseModel] | None = None) -> Dict[str, Any]:
    api_key = _get_llm_api_key()
    if not api_key:
        return {}

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
    }
    if response_schema is not None:
        payload["response_format"] = {"type": "json_object"}

    try:
        with httpx.Client(timeout=15.0) as client:
            response = client.post(
                f"{_get_llm_base_url()}/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        if response_schema is not None:
            validated = response_schema.model_validate(parsed)
            return {**validated.model_dump(), "status": "READY", "fallback": False}
        return {"content": content, "status": "READY", "fallback": False}
    except Exception:
        return {}


def generate_pre_visit_summary(symptom_text: str) -> Dict[str, Any]:
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    prompt = (
        "Analyse these symptoms and return a JSON object with: urgency_level, chief_complaint, and "
        "suggested_questions as a list of exactly three strings. Symptoms: " + symptom_text
    )
    result = _call_llm(prompt, model, PreVisitSummaryModel)
    if result:
        return result
    return _fallback_pre_visit_summary()


def generate_post_visit_summary(notes: str, medications: List[Dict[str, str]] | None = None) -> Dict[str, Any]:
    model = os.getenv("LLM_MODEL", "gpt-4o-mini")
    prompt = "Convert these clinical notes into a patient-friendly JSON object with summary, medication_schedule, and follow_up_steps. Notes: " + notes
    result = _call_llm(prompt, model, PostVisitSummaryModel)
    if result:
        return result
    return _fallback_post_visit_summary(notes, medications)
