from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from core.models import ToolResult


class WorkspaceExecutor:
    ALLOWED_ACTIONS = {"OPEN_APP", "OPEN_URL", "OPEN_FILE", "OPEN_FOLDER", "START_TIMER", "SAFE_SKILL"}
    SAFE_FILE_SUFFIXES = {".md", ".txt", ".pdf", ".docx", ".xlsx", ".pptx", ".py", ".cs", ".xaml", ".json", ".toml"}

    def __init__(self, windows): self.windows = windows

    def validate(self, action: dict) -> dict:
        action_type = str(action.get("type", "")).upper()
        if action_type not in self.ALLOWED_ACTIONS:
            raise ValueError(f"Ação não permitida: {action_type or 'vazia'}")
        value = str(action.get("value", "")).strip()
        if action_type == "OPEN_APP" and value.casefold() not in self.windows.APPS:
            raise ValueError("Aplicativo fora da allowlist.")
        if action_type == "OPEN_URL" and urlparse(value).scheme not in {"http", "https"}:
            raise ValueError("URL fora da allowlist.")
        if action_type == "OPEN_FILE":
            path = Path(value)
            if path.suffix.casefold() not in self.SAFE_FILE_SUFFIXES:
                raise ValueError("Tipo de arquivo fora da allowlist.")
        if action_type == "OPEN_FOLDER" and Path(value).suffix:
            raise ValueError("OPEN_FOLDER exige uma pasta.")
        if action_type == "START_TIMER":
            minutes = int(action.get("minutes") or value or 0)
            if not 1 <= minutes <= 240:
                raise ValueError("Timer deve ter entre 1 e 240 minutos.")
            return {"type": action_type, "minutes": minutes}
        if action_type == "SAFE_SKILL" and value not in {"daily_briefing", "show_day"}:
            raise ValueError("Skill fora da allowlist do workspace.")
        return {"type": action_type, "value": value}

    def run(self, action: dict) -> str:
        safe = self.validate(action)
        kind = safe["type"]
        if kind == "OPEN_APP":
            result = self.windows.open_app(safe["value"])
            if not result.ok: raise OSError(result.message)
            return result.message
        if kind == "OPEN_URL":
            self.windows.opener(safe["value"])
            return "URL aberta"
        if kind in {"OPEN_FILE", "OPEN_FOLDER"}:
            path = Path(safe["value"])
            if not path.exists(): raise FileNotFoundError(path)
            self.windows.opener(str(path))
            return f"{path.name or path} aberto"
        if kind == "START_TIMER":
            return f"Timer de {safe['minutes']} minutos iniciado"
        return f"Skill segura preparada: {safe['value']}"


class WorkspaceTool:
    def __init__(self, repository, executor): self.repository, self.executor = repository, executor

    def save(self, name: str, **values) -> ToolResult:
        try:
            actions = [self.executor.validate(action) for action in values.get("actions", [])]
            workspace = self.repository.save(name, workspace_id=values.get("workspace_id"), aliases=values.get("aliases"),
                                             actions=actions, project_id=values.get("project_id"),
                                             focus_minutes=values.get("focus_minutes"), enabled=values.get("enabled", True))
            return ToolResult(True, f"Modo {workspace['name']} salvo com segurança.", workspace,
                              "workspace", workspace["id"], type="workspace_saved",
                              ui_hint={"mode": "context", "panel": "workspace", "title": "Modos"})
        except (ValueError, TypeError) as exc:
            return ToolResult(False, str(exc), type="workspace_error", error="invalid_workspace")

    def create(self, name: str) -> ToolResult:
        return self.save(name, aliases=[name])

    def configure_apps(self, name: str, apps: list[str]) -> ToolResult:
        existing = self.repository.find(name)
        actions = list(existing["actions"] if existing else [])
        actions.extend({"type": "OPEN_APP", "value": app.casefold()} for app in apps)
        return self.save(existing["name"] if existing else name, workspace_id=existing["id"] if existing else None,
                         aliases=existing["aliases"] if existing else [name], actions=actions)

    def activate(self, name: str) -> ToolResult:
        workspace = self.repository.find(name)
        if not workspace or not workspace["enabled"]:
            return ToolResult(False, f"Não encontrei um modo ativo chamado {name}.", type="workspace_not_found", error="not_found")
        completed, errors = [], []
        for action in workspace["actions"]:
            try: completed.append(self.executor.run(action))
            except (OSError, ValueError) as exc: errors.append(f"{action.get('type')}: {exc}")
        self.repository.set_active(workspace["id"])
        message = f"Modo {workspace['name']} ativado."
        if not workspace["actions"]: message += " Ele ainda não possui ações configuradas."
        elif errors: message += f" {len(errors)} ação(ões) não puderam ser executadas."
        return ToolResult(True, message, {**workspace, "completed": completed, "errors": errors},
                          "workspace", workspace["id"], type="workspace_activated",
                          ui_hint={"mode": "context", "panel": "workspace", "title": f"Modo {workspace['name']}"})

    def end(self, name: str = "") -> ToolResult:
        active = next((item for item in self.repository.list(False) if item["active"]), None)
        if not active:
            return ToolResult(True, "Nenhum modo está ativo.", type="workspace_ended")
        if name and self.repository.find(name) and self.repository.find(name)["id"] != active["id"]:
            return ToolResult(False, f"O modo ativo é {active['name']}.", type="workspace_error")
        self.repository.set_active(None)
        return ToolResult(True, f"Modo {active['name']} encerrado.", active, type="workspace_ended")

    def list(self) -> ToolResult:
        items = self.repository.list()
        message = ("Você ainda não tem modos configurados." if not items else
                   "Seus modos: " + ", ".join(item["name"] for item in items) + ".")
        return ToolResult(True, message, {"workspaces": items}, type="workspace_list",
                          ui_hint={"mode": "context", "panel": "workspace", "title": "Modos"})
