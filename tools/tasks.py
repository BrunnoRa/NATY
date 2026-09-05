from core.models import ToolResult
from database.repositories.tasks import TaskRepository


class TasksTool:
    def __init__(self, repo: TaskRepository): self.repo = repo

    def create(self, title: str, **kwargs) -> ToolResult:
        if not title.strip(): return ToolResult(False, "Qual é a tarefa?")
        task = self.repo.create(title, **kwargs)
        return ToolResult(True, f"Feito. Criei a tarefa '{task['title']}'.", task, "task", task["id"])

    def list_pending(self) -> ToolResult:
        tasks = self.repo.list("pending")
        if not tasks: return ToolResult(True, "Você não tem tarefas pendentes.", [])
        preview = "; ".join(t["title"] for t in tasks[:5])
        rest = f" e mais {len(tasks)-5}" if len(tasks) > 5 else ""
        return ToolResult(True, f"Você tem {len(tasks)} tarefa(s) pendente(s): {preview}{rest}.", tasks)

    def complete(self, task_id: int) -> ToolResult:
        task = self.repo.complete(task_id)
        return ToolResult(bool(task), f"Concluí '{task['title']}'." if task else "Não encontrei essa tarefa.", task, "task", task_id if task else None)

    def complete_named(self, query: str) -> ToolResult:
        needle = query.casefold().strip()
        matches = [task for task in self.repo.list("pending") if needle in task["title"].casefold()]
        if not matches:
            return ToolResult(False, f"Não encontrei uma tarefa pendente chamada '{query}'.", type="task_not_found", error="task_not_found")
        if len(matches) > 1:
            return ToolResult(False, "Encontrei mais de uma tarefa parecida. Qual delas você quer concluir?", matches,
                              type="clarification", error="ambiguous_task")
        result = self.complete(matches[0]["id"])
        result.type = "task_completed"
        return result

    def update(self, task_id: int, **changes) -> ToolResult:
        task = self.repo.update(task_id, **changes)
        return ToolResult(bool(task), "Feito. Atualizei a tarefa." if task else "Não encontrei essa tarefa.", task, "task", task_id if task else None)

    def postpone(self, task_id: int, due_at: str) -> ToolResult:
        task = self.repo.postpone(task_id, due_at)
        return ToolResult(bool(task), "Feito. Remarquei a tarefa." if task else "Não encontrei essa tarefa.", task, "task", task_id if task else None)
