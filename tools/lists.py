from core.models import ToolResult
from database.repositories.lists import ListRepository
from tools.obsidian import ObsidianTool


class ListsTool:
    def __init__(self, repo: ListRepository, obsidian: ObsidianTool | None = None):
        self.repo, self.obsidian = repo, obsidian

    def _sync(self, list_id: int) -> None:
        if self.obsidian:
            try: self.obsidian.sync_list(list_id)
            except Exception: pass

    def create(self, name: str) -> ToolResult:
        record = self.repo.create(name)
        self._sync(record["id"])
        return ToolResult(True, f"Feito. A lista '{record['name']}' está pronta.", record, "list", record["id"])

    def add(self, name: str | None, items: list[str], fallback_id: int | None = None) -> ToolResult:
        record = self.repo.find(name) if name else (self.repo.get(fallback_id) if fallback_id else None)
        if not record:
            if not name: return ToolResult(False, "Em qual lista devo adicionar?")
            record = self.repo.create(name)
        clean = [item.strip(" .") for item in items if item.strip(" .")]
        added = [self.repo.add_item(record["id"], item) for item in clean]
        self._sync(record["id"])
        names = ", ".join(item["text"] for item in added)
        return ToolResult(True, f"Feito. Adicionei {names} à lista '{record['name']}'.", added, "list", record["id"])

    def show(self, name: str | None, fallback_id: int | None = None, unchecked_only: bool = False) -> ToolResult:
        record = self.repo.find(name) if name else (self.repo.get(fallback_id) if fallback_id else None)
        if not record: return ToolResult(False, "Qual lista você quer abrir?")
        items = self.repo.items(record["id"], False if unchecked_only else None)
        if not items: message = f"A lista '{record['name']}' está vazia."
        else: message = f"{record['name']}: " + "; ".join(("✓ " if i["checked"] else "") + i["text"] for i in items) + "."
        return ToolResult(True, message, items, "list", record["id"])

    def check(self, name: str | None, item: str, fallback_id: int | None = None) -> ToolResult:
        record = self.repo.find(name) if name else (self.repo.get(fallback_id) if fallback_id else None)
        if not record: return ToolResult(False, "Em qual lista está esse item?")
        updated = self.repo.check(record["id"], item)
        if not updated: return ToolResult(False, f"Não encontrei '{item}' na lista '{record['name']}'.")
        self._sync(record["id"])
        return ToolResult(True, f"Marquei '{updated['text']}' como concluído.", updated, "list", record["id"])

    def remove(self, name: str | None, item: str, fallback_id: int | None = None) -> ToolResult:
        record = self.repo.find(name) if name else (self.repo.get(fallback_id) if fallback_id else None)
        if not record: return ToolResult(False, "Em qual lista está esse item?")
        ok = self.repo.remove(record["id"], item)
        self._sync(record["id"])
        return ToolResult(ok, f"Removi '{item}'." if ok else f"Não encontrei '{item}'.", entity_type="list", entity_id=record["id"])

    def clear_checked(self, name: str | None, fallback_id: int | None = None) -> ToolResult:
        record = self.repo.find(name) if name else (self.repo.get(fallback_id) if fallback_id else None)
        if not record: return ToolResult(False, "Qual lista devo limpar?")
        count = self.repo.clear_checked(record["id"])
        self._sync(record["id"])
        return ToolResult(True, f"Removi {count} item(ns) concluído(s).", entity_type="list", entity_id=record["id"])
