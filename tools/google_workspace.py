from __future__ import annotations

from core.models import ToolResult


class GoogleWorkspaceTool:
    def __init__(self, settings, db, auth, gmail, calendar):
        self.settings, self.db, self.auth = settings, db, auth
        self.gmail, self.calendar = gmail, calendar
        self.last_draft_id: str | None = None

    def connect(self) -> ToolResult:
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
        if not self.settings.google_enabled:
            return ToolResult(False, "O Google está desativado. Diga 'conectar Google' quando quiser autorizar.")
        try:
            messages = self.gmail.search(query)
            return ToolResult(True, self.gmail.summarize(messages), messages)
        except Exception as exc:
            return ToolResult(False, f"Não consegui consultar o Gmail: {exc}")

    def draft(self, to: str, subject: str, body: str) -> ToolResult:
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
        try:
            events = self.calendar.upcoming()
            if not events:
                return ToolResult(True, "Nenhum evento encontrado nos próximos 7 dias.", [])
            lines = [f"- {event.get('summary', '(sem título)')} — {(event.get('start') or {}).get('dateTime') or (event.get('start') or {}).get('date', '')}" for event in events]
            return ToolResult(True, "Agenda Google:\n" + "\n".join(lines), events)
        except Exception as exc:
            return ToolResult(False, f"Não consegui consultar o Google Calendar: {exc}")
