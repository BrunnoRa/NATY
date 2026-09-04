from core.models import ToolResult
from database.repositories.reminders import ReminderRepository


class RemindersTool:
    def __init__(self, repo: ReminderRepository): self.repo = repo

    def create(self, text: str, remind_at: str | None) -> ToolResult:
        if not remind_at: return ToolResult(False, "Para quando devo criar o lembrete?")
        reminder = self.repo.create(text or "Lembrete", remind_at)
        return ToolResult(True, f"Feito. Vou lembrar você em {remind_at.replace('T', ' ')}.", reminder, "reminder", reminder["id"])

    def list_pending(self) -> ToolResult:
        items = self.repo.pending()
        return ToolResult(True, f"Você tem {len(items)} lembrete(s) pendente(s).", items)
