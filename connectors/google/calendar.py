from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta

from connectors.base import Connector, ConnectorInfo, require_confirmation


class GoogleCalendarConnector(Connector):
    info = ConnectorInfo("google_calendar", ("calendar.events",))

    def __init__(self, auth=None, service_factory: Callable | None = None, service=None):
        self.auth, self._service_factory, self._service = auth, service_factory, service

    def available(self) -> bool:
        return self._service is not None or bool(self.auth and self.auth.available())

    def _api(self):
        if self._service is not None:
            return self._service
        credentials = self.auth.credentials(interactive=False)
        if self._service_factory:
            self._service = self._service_factory(credentials)
        else:
            from googleapiclient.discovery import build
            self._service = build("calendar", "v3", credentials=credentials, cache_discovery=False)
        return self._service

    def upcoming(self, days: int = 7, max_results: int = 20) -> list[dict]:
        start = datetime.now().astimezone()
        end = start + timedelta(days=max(1, days))
        return self._api().events().list(
            calendarId="primary", timeMin=start.isoformat(), timeMax=end.isoformat(),
            singleEvents=True, orderBy="startTime", maxResults=max_results,
        ).execute().get("items", [])

    def between(self, starts_at: str, ends_at: str, max_results: int = 20) -> list[dict]:
        return self._api().events().list(calendarId="primary", timeMin=starts_at, timeMax=ends_at,
            singleEvents=True, orderBy="startTime", maxResults=max_results).execute().get("items", [])

    def create(self, title: str, starts_at: str, ends_at: str | None = None, description: str = "") -> dict:
        if not ends_at:
            ends_at = (datetime.fromisoformat(starts_at) + timedelta(hours=1)).isoformat()
        event = {"summary": title, "description": description, "start": {"dateTime": starts_at}, "end": {"dateTime": ends_at}}
        return self._api().events().insert(calendarId="primary", body=event).execute()

    def update(self, event_id: str, changes: dict) -> dict:
        event = self._api().events().get(calendarId="primary", eventId=event_id).execute()
        event.update(changes)
        return self._api().events().update(calendarId="primary", eventId=event_id, body=event).execute()

    def delete(self, event_id: str, confirmed: bool = False) -> None:
        require_confirmation(confirmed, "excluir o evento")
        self._api().events().delete(calendarId="primary", eventId=event_id).execute()
