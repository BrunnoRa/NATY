from __future__ import annotations

from core.models import ToolResult


class NotificationTool:
    def __init__(self, repository): self.repository = repository

    def show(self, important_only: bool = False) -> ToolResult:
        priorities = ("IMPORTANT", "URGENT") if important_only else ()
        items = self.repository.list(unread_only=True, priorities=priorities)
        if not items:
            message = "Você não tem notificações importantes não lidas." if important_only else "Você não perdeu nenhuma notificação da NATY."
        else:
            message = f"Você tem {len(items)} notificação(ões) não lida(s). " + " ".join(
                f"{item['title']}: {item['message']}" for item in reversed(items[-3:]))
        return ToolResult(True, message, {"notifications": items}, type="notification_list",
                          ui_hint={"mode": "context", "panel": "notifications", "title": "Notificações"})
