from __future__ import annotations

from database.repositories.projects import ProjectRepository
from database.repositories.tasks import TaskRepository
from knowledge.context import ContextNote, ContextPack
from knowledge.obsidian_index import ObsidianIndex


class ObsidianContextRetriever:
    def __init__(self, index: ObsidianIndex | None, projects: ProjectRepository, tasks: TaskRepository,
                 max_notes: int = 6, max_chars: int = 8000):
        self.index, self.projects, self.tasks, self.max_notes, self.max_chars = index, projects, tasks, max_notes, max_chars

    def retrieve(self, query: str) -> ContextPack:
        notes = []
        if self.index:
            for row in self.index.search(query, self.max_notes):
                notes.append(ContextNote(row["title"], row["path"], row["body"][:1600], float(row.get("score") or 0)))
        structured = {}
        for project in self.projects.list():
            if project["name"].lower() in query.lower():
                structured["project"] = project; structured["tasks"] = self.projects.tasks(project["id"]); break
        return ContextPack(query=query, notes=notes, structured=structured, max_chars=self.max_chars)
