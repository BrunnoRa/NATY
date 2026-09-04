from __future__ import annotations

import base64
from collections.abc import Callable
from email.message import EmailMessage

from connectors.base import Connector, ConnectorInfo, require_confirmation


class GmailConnector(Connector):
    info = ConnectorInfo("gmail", ("gmail.readonly", "gmail.compose", "gmail.modify"))

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
            self._service = build("gmail", "v1", credentials=credentials, cache_discovery=False)
        return self._service

    def search(self, query: str = "is:unread", max_results: int = 10) -> list[dict]:
        api = self._api()
        rows = api.users().messages().list(userId="me", q=query, maxResults=max_results).execute().get("messages", [])
        return [self.get(row["id"]) for row in rows]

    def get(self, message_id: str) -> dict:
        data = self._api().users().messages().get(userId="me", id=message_id, format="metadata", metadataHeaders=["From", "Subject", "Date"]).execute()
        headers = {row.get("name", "").casefold(): row.get("value", "") for row in data.get("payload", {}).get("headers", [])}
        return {"id": data.get("id"), "thread_id": data.get("threadId"), "from": headers.get("from", ""), "subject": headers.get("subject", "(sem assunto)"), "date": headers.get("date", ""), "snippet": data.get("snippet", "")}

    @staticmethod
    def summarize(messages: list[dict]) -> str:
        if not messages:
            return "Nenhum e-mail encontrado."
        lines = [f"- {m.get('subject', '(sem assunto)')} — {m.get('from', '')}: {m.get('snippet', '')[:180]}" for m in messages]
        return f"{len(messages)} e-mail(s):\n" + "\n".join(lines)

    def create_draft(self, to: str, subject: str, body: str) -> dict:
        message = EmailMessage()
        message["To"], message["Subject"] = to, subject
        message.set_content(body)
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode("ascii")
        return self._api().users().drafts().create(userId="me", body={"message": {"raw": raw}}).execute()

    def send_draft(self, draft_id: str, confirmed: bool = False) -> dict:
        require_confirmation(confirmed, "enviar o rascunho")
        return self._api().users().drafts().send(userId="me", body={"id": draft_id}).execute()

    def delete(self, message_id: str, confirmed: bool = False) -> None:
        require_confirmation(confirmed, "excluir o e-mail")
        self._api().users().messages().trash(userId="me", id=message_id).execute()
