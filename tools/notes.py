from core.models import ToolResult
from database.connection import Database
from tools.obsidian import ObsidianTool


class NotesTool:
    def __init__(self, db: Database, obsidian: ObsidianTool | None = None): self.db, self.obsidian = db, obsidian

    def create(self, title: str, content: str, project_id: int | None = None) -> ToolResult:
        note_id = self.db.execute("INSERT INTO notes(title, content, project_id) VALUES (?, ?, ?)", (title, content, project_id))
        path = None
        if self.obsidian:
            try: path = self.obsidian.save_note("Notas", title, content)
            except Exception: pass
        return ToolResult(True, "Anotei.", {"id": note_id, "path": str(path) if path else None}, "note", note_id)
