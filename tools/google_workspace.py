from __future__ import annotations

from core.models import ToolResult


class GoogleWorkspaceTool:
    def __init__(self, settings, db, auth, gmail, calendar):
        self.settings, self.db, self.auth = settings, db, auth
        self.gmail, self.calendar = gmail, calendar
        self.last_draft_id: str | None = None

    def status(self) -> ToolResult:
        data = self.auth.status()
        return ToolResult(True, "Google conectado." if data["connected"] else "Google ainda não conectado.", data,
                          type="google_status", ui_hint={"mode": "context", "panel": "google", "title": "Integrações · Google"})

    def _not_ready(self) -> ToolResult | None:
        if not self.settings.google_enabled or not self.auth.available():
            return ToolResult(False, "Google ainda não conectado. Selecione o JSON OAuth nas configurações e use Conectar.",
                              self.auth.status(), type="connector_not_configured", error="not_configured")
        return None

    def connect(self) -> ToolResult:
        if not self.auth.available():
            return ToolResult(False, "Google ainda não conectado. Selecione um JSON OAuth de aplicativo para computador.",
                              self.auth.status(), type="connector_not_configured", error="not_configured")
        try:
            credentials = self.auth.credentials(interactive=True)
            label = getattr(credentials, "account", None) or "Conta Google"
            self.db.execute(
                "INSERT INTO connector_accounts(provider,account_label,scopes,connected_at) VALUES('google',?,?,CURRENT_TIMESTAMP) "
                "ON CONFLICT(provider) DO UPDATE SET account_label=excluded.account_label,scopes=excluded.scopes,connected_at=CURRENT_TIMESTAMP,updated_at=CURRENT_TIMESTAMP",
                (label, " ".join(self.auth.scopes)),
            )
            self.settings.google_enabled = True
            self.settings.save()
            return ToolResult(True, "Conta Google conectada. O token foi protegido para seu usuário do Windows.")
        except Exception as exc:
            return ToolResult(False, f"Não consegui conectar o Google: {exc}")

    def disconnect(self, confirmed: bool = False) -> ToolResult:
        if not confirmed:
            return ToolResult(False, "Confirmação explícita necessária para desconectar o Google.")
        try:
            removed = self.auth.disconnect()
            self.db.execute("DELETE FROM connector_accounts WHERE provider='google'")
            self.settings.google_enabled = False
            self.settings.save()
            message = "Conta Google desconectada deste computador."
            if not removed: message += " Não havia token local armazenado."
            return ToolResult(True, message)
        except Exception as exc:
            return ToolResult(False, f"Não consegui remover o token Google: {exc}")

    def search_mail(self, query: str) -> ToolResult:
        if unavailable := self._not_ready(): return unavailable
        try:
            messages = self.gmail.search(query)
            return ToolResult(True, self.gmail.summarize(messages), messages)
        except Exception as exc:
            return ToolResult(False, f"Não consegui consultar o Gmail: {exc}")

    def draft(self, to: str, subject: str, body: str) -> ToolResult:
        if unavailable := self._not_ready(): return unavailable
        if not to or "@" not in to:
            return ToolResult(False, "Informe um endereço de e-mail válido para o rascunho.")
        if not body:
            return ToolResult(False, "Qual mensagem deve entrar no rascunho?")
        try:
            draft = self.gmail.create_draft(to, subject, body)
            self.last_draft_id = draft.get("id")
            return ToolResult(True, f"Rascunho criado para {to}. Nada foi enviado.", draft, "gmail_draft", None)
        except Exception as exc:
            return ToolResult(False, f"Não consegui criar o rascunho: {exc}")

    def send_last_draft(self, confirmed: bool = False) -> ToolResult:
        if not self.last_draft_id:
            return ToolResult(False, "Não há rascunho recente para enviar.")
        try:
            result = self.gmail.send_draft(self.last_draft_id, confirmed=confirmed)
            self.last_draft_id = None
            return ToolResult(True, "Rascunho enviado após sua confirmação.", result)
        except Exception as exc:
            return ToolResult(False, f"Não consegui enviar o rascunho: {exc}")

    def upcoming(self) -> ToolResult:
        if unavailable := self._not_ready(): return unavailable
        try:
            events = self.calendar.upcoming()
            if not events:
                return ToolResult(True, "Nenhum evento encontrado nos próximos 7 dias.", [])
            lines = [f"- {event.get('summary', '(sem título)')} — {(event.get('start') or {}).get('dateTime') or (event.get('start') or {}).get('date', '')}" for event in events]
            return ToolResult(True, "Agenda Google:\n" + "\n".join(lines), events)
        except Exception as exc:
            return ToolResult(False, f"Não consegui consultar o Google Calendar: {exc}")

    def create_event(self, title: str, starts_at: str | None, ends_at: str | None = None) -> ToolResult:
        if unavailable := self._not_ready(): return unavailable
        if not starts_at: return ToolResult(False, "Informe a data e o horário do compromisso.")
        try:
            event = self.calendar.create(title, starts_at, ends_at)
            return ToolResult(True, f"Compromisso '{title}' criado no Google Calendar.", event, type="google_event_created")
        except Exception as exc: return ToolResult(False, f"Não consegui criar o compromisso no Google Calendar: {exc}")

    def is_free(self, starts_at: str | None) -> ToolResult:
        if unavailable := self._not_ready(): return unavailable
        if not starts_at: return ToolResult(False, "Informe a data e o horário que deseja consultar.")
        try:
            from datetime import datetime, timedelta
            start = datetime.fromisoformat(starts_at); end = start + timedelta(hours=1)
            busy = self.calendar.between(start.isoformat(), end.isoformat())
            return ToolResult(True, "Você está livre nesse horário." if not busy else f"Esse horário tem {len(busy)} compromisso(s).",
                              busy, type="google_availability")
        except Exception as exc: return ToolResult(False, f"Não consegui consultar a disponibilidade: {exc}")
