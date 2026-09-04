from __future__ import annotations

from core.models import ToolResult
from database.repositories.tasks import TaskRepository
from planner.scoring import task_score


class Planner:
    def __init__(self, tasks: TaskRepository): self.tasks = tasks

    def suggest(self, available_minutes: int | None = None, limit: int = 3) -> ToolResult:
        candidates = self.tasks.list("pending")
        if available_minutes is not None:
            candidates = [t for t in candidates if int(t.get("estimated_minutes") or 30) <= available_minutes]
        ranked = sorted(candidates, key=task_score, reverse=True)[:limit]
        for task in ranked: task["planner_score"] = task_score(task)
        if not ranked:
            suffix = f" que caiba em {available_minutes} minutos" if available_minutes else ""
            return ToolResult(True, f"Não encontrei tarefa pendente{suffix}.", [])
        names = "; ".join(f"{t['title']} ({t.get('estimated_minutes') or 30} min)" for t in ranked)
        return ToolResult(True, f"Sugestão: {names}.", ranked, "task", ranked[0]["id"])
