from core.models import ToolResult
from database.repositories.projects import ProjectRepository


class ProjectsTool:
    def __init__(self, repo: ProjectRepository): self.repo = repo

    def create(self, name: str, description: str = "") -> ToolResult:
        try: project = self.repo.create(name, description)
        except Exception:
            project = self.repo.find(name)
        return ToolResult(True, f"Projeto '{project['name']}' pronto.", project, "project", project["id"])

    def overdue(self, name: str) -> ToolResult:
        from datetime import datetime
        project = self.repo.find(name)
        if not project: return ToolResult(False, f"Não encontrei o projeto '{name}'.")
        tasks = self.repo.tasks(project["id"])
        now = datetime.now().astimezone()
        overdue = []
        for task in tasks:
            if not task["due_at"]: continue
            try:
                due = datetime.fromisoformat(task["due_at"])
                if due.tzinfo is None: due = due.replace(tzinfo=now.tzinfo)
                if due < now: overdue.append(task)
            except ValueError: continue
        return ToolResult(True, f"O projeto '{name}' tem {len(overdue)} tarefa(s) atrasada(s).", overdue, "project", project["id"])
