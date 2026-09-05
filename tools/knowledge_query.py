from core.models import ToolResult


class KnowledgeQueryTool:
    def __init__(self, retriever):
        self.retriever = retriever

    def query(self, query: str) -> ToolResult:
        pack = self.retriever.retrieve(query) if self.retriever else None
        if not pack or (not pack.notes and not pack.structured):
            return ToolResult(True, "Não encontrei isso na minha memória.", {"query": query, "notes": []}, type="memory_not_found")
        notes = [{"title": note.title, "path": note.path, "excerpt": note.excerpt} for note in pack.notes]
        project = pack.structured.get("project")
        tasks = pack.structured.get("tasks", [])
        parts = []
        if project:
            parts.append(f"O projeto '{project['name']}' está {project['status']} e tem {len(tasks)} tarefa(s).")
        if notes:
            names = ", ".join(note["title"] for note in notes[:3])
            excerpt = notes[0]["excerpt"].strip()[:360]
            parts.append(f"Encontrei {len(notes)} nota(s) relacionada(s): {names}. {excerpt}")
        return ToolResult(True, " ".join(parts), {"query": query, "project": project, "tasks": tasks, "notes": notes}, type="obsidian_result")
