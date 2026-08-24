import os
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from app.config import get_settings


class CalendarService:
    @staticmethod
    def _get_access_token() -> Optional[str]:
        settings = get_settings()
        access_token = os.getenv("GOOGLE_ACCESS_TOKEN") or settings.google_access_token
        if access_token:
            return access_token

        refresh_token = os.getenv("GOOGLE_REFRESH_TOKEN") or settings.google_refresh_token
        client_id = os.getenv("GOOGLE_CLIENT_ID") or settings.google_client_id
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET") or settings.google_client_secret
        if refresh_token and client_id and client_secret:
            try:
                response = httpx.post(
                    "https://oauth2.googleapis.com/token",
                    data={
                        "client_id": client_id,
                        "client_secret": client_secret,
                        "refresh_token": refresh_token,
                        "grant_type": "refresh_token",
                    },
                    timeout=15,
                )
                response.raise_for_status()
                return response.json().get("access_token")
            except Exception:
                return None
        return None

    @staticmethod
    def create_event_for_appointment(doctor_name: str, patient_name: str, appointment_start: datetime, appointment_end: datetime) -> Dict[str, Any]:
        summary = f"Appointment: {patient_name} with {doctor_name}"
        payload = {
            "summary": summary,
            "description": "Healthcare appointment scheduled through the appointment manager.",
            "start": {"dateTime": appointment_start.isoformat()},
            "end": {"dateTime": appointment_end.isoformat()},
        }
        access_token = CalendarService._get_access_token()
        if not access_token:
            return {
                "status": "queued",
                "summary": summary,
                "start": appointment_start.isoformat(),
                "end": appointment_end.isoformat(),
                "provider": "google-calendar",
                "note": "Google Calendar integration requires GOOGLE_ACCESS_TOKEN or a valid refresh token.",
            }

        try:
            response = httpx.post(
                "https://www.googleapis.com/calendar/v3/calendars/primary/events",
                headers={"Authorization": f"Bearer {access_token}"},
                json=payload,
                timeout=15,
            )
            if response.status_code >= 400:
                return {
                    "status": "failed",
                    "provider": "google-calendar",
                    "error": response.text,
                    "summary": summary,
                }
            data = response.json()
            return {
                "status": "created",
                "provider": "google-calendar",
                "event_id": data.get("id"),
                "summary": summary,
                "start": appointment_start.isoformat(),
                "end": appointment_end.isoformat(),
            }
        except Exception as exc:  # pragma: no cover - external dependency not configured
            return {"status": "failed", "provider": "google-calendar", "error": str(exc), "summary": summary}

    @staticmethod
    def update_event(event_id: str, appointment_start: datetime, appointment_end: datetime) -> Dict[str, Any]:
        access_token = CalendarService._get_access_token()
        if not access_token:
            return {"status": "queued", "event_id": event_id, "start": appointment_start.isoformat(), "end": appointment_end.isoformat(), "provider": "google-calendar"}
        try:
            response = httpx.patch(
                f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                json={
                    "start": {"dateTime": appointment_start.isoformat()},
                    "end": {"dateTime": appointment_end.isoformat()},
                },
                timeout=15,
            )
            response.raise_for_status()
            return {"status": "updated", "event_id": event_id, "start": appointment_start.isoformat(), "end": appointment_end.isoformat(), "provider": "google-calendar"}
        except Exception as exc:  # pragma: no cover - external dependency not configured
            return {"status": "failed", "event_id": event_id, "error": str(exc), "provider": "google-calendar"}

    @staticmethod
    def delete_event(event_id: str) -> Dict[str, Any]:
        access_token = CalendarService._get_access_token()
        if not access_token:
            return {"status": "queued", "event_id": event_id, "provider": "google-calendar"}
        try:
            response = httpx.delete(
                f"https://www.googleapis.com/calendar/v3/calendars/primary/events/{event_id}",
                headers={"Authorization": f"Bearer {access_token}"},
                timeout=15,
            )
            if response.status_code in {200, 204}:
                return {"status": "cancelled", "event_id": event_id, "provider": "google-calendar"}
            return {"status": "failed", "event_id": event_id, "provider": "google-calendar", "error": response.text}
        except Exception as exc:  # pragma: no cover - external dependency not configured
            return {"status": "failed", "event_id": event_id, "provider": "google-calendar", "error": str(exc)}
