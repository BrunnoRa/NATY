from __future__ import annotations

import json
from pathlib import Path

from connectors.google.credential_store import DpapiCredentialStore


DEFAULT_SCOPES = (
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.compose",
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar.events",
)


class GoogleAuth:
    """Installed-app OAuth whose refresh token is never written in plain text."""

    def __init__(self, credentials_path: str, token_store, scopes=DEFAULT_SCOPES):
        self.credentials_path = Path(credentials_path).expanduser() if credentials_path else None
        self.token_store = token_store
        self.scopes = tuple(scopes)

    @classmethod
    def for_settings(cls, settings):
        token_path = settings.resolve_path(settings.data_dir) / "secrets" / "google.token"
        return cls(settings.google_credentials_path, DpapiCredentialStore(token_path))

    def available(self) -> bool:
        if not self.credentials_path or not self.credentials_path.is_file():
            return False
        try:
            import google.oauth2.credentials  # noqa: F401
            import google_auth_oauthlib.flow  # noqa: F401
        except ImportError:
            return False
        return True

    def credentials(self, interactive: bool = False):
        if not self.available():
            raise RuntimeError("Instale requirements-google.txt e configure o JSON OAuth de aplicativo para computador.")
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        token = self.token_store.load()
        creds = Credentials.from_authorized_user_info(json.loads(token), self.scopes) if token else None
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            self.token_store.save(creds.to_json())
        if creds and creds.valid:
            return creds
        if not interactive:
            raise RuntimeError("Conta Google ainda não conectada.")
        from google_auth_oauthlib.flow import InstalledAppFlow
        flow = InstalledAppFlow.from_client_secrets_file(str(self.credentials_path), self.scopes)
        creds = flow.run_local_server(port=0, open_browser=True, authorization_prompt_message="Abra este endereço para autorizar a Naty: {url}")
        self.token_store.save(creds.to_json())
        return creds

    def disconnect(self) -> bool:
        return self.token_store.clear()
