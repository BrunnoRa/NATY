from __future__ import annotations

from pathlib import Path
import json
import os
import re
import tempfile

from database.repositories.lists import ListRepository


BEGIN = "<!-- NATY:BEGIN -->"
END = "<!-- NATY:END -->"


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    except Exception:
        try: os.unlink(temp_name)
        except OSError: pass
        raise


def replace_managed_block(existing: str, block: str) -> str:
    managed = f"{BEGIN}\n{block.rstrip()}\n{END}"
    pattern = re.compile(re.escape(BEGIN) + r".*?" + re.escape(END), re.DOTALL)
    if pattern.search(existing):
        return pattern.sub(lambda _: managed, existing, count=1)
    separator = "\n\n" if existing.strip() else ""
    return existing.rstrip() + separator + managed + "\n"


class ObsidianTool:
    def __init__(self, enabled: bool, vault_path: str, lists: ListRepository, naty_path: str = ""):
        self.enabled = enabled
        self.vault = Path(vault_path).expanduser().resolve() if vault_path else None
        self.base = Path(naty_path).expanduser().resolve() if naty_path else (self.vault / "Naty" if self.vault else None)
        if self.vault and self.base and self.base != (self.vault / "Naty").resolve():
            self.base = None
        self.lists = lists

    @property
    def available(self) -> bool:
        return bool(self.enabled and self.vault and self.base and self.vault.is_dir())

    def _managed_path(self, *parts: str) -> Path:
        if self.base is None:
            raise ValueError("A pasta gerenciada da Naty não está configurada.")
        path = self.base.joinpath(*parts).resolve()
        try:
            path.relative_to(self.base)
        except ValueError as exc:
            raise ValueError("A Naty só pode escrever dentro da pasta gerenciada Naty.") from exc
        return path

    def initialize(self) -> bool:
        if not self.available: return False
        from knowledge.obsidian_bootstrap import ObsidianBootstrap
        ObsidianBootstrap(self.vault, self.base).prepare()
        return True

    def prepare_vault(self) -> list[Path]:
        if not self.available: return []
        from knowledge.obsidian_bootstrap import ObsidianBootstrap
        return ObsidianBootstrap(self.vault, self.base).prepare()

    def list_path(self, list_record: dict) -> Path:
        assert self.vault is not None
        if list_record["slug"] in {"compras", "lista-de-compras"} or list_record["name"].lower() in {"compras", "lista de compras"}:
            return self._managed_path("04 - Listas", "Lista de Compras.md")
        return self._managed_path("04 - Listas", f"{list_record['name']}.md")

    def sync_list(self, list_id: int) -> Path | None:
        if not self.available: return None
        self.initialize()
        record = self.lists.get(list_id)
        if not record: return None
        items = self.lists.items(list_id)
        lines = [f"# {record['name']}", ""]
        lines.extend(f"- [{'x' if item['checked'] else ' '}] {item['text']}" for item in items)
        path = self.list_path(record)
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        atomic_write(path, replace_managed_block(existing, "\n".join(lines)))
        self.lists.db.execute("UPDATE lists SET obsidian_file = ? WHERE id = ?", (str(path.relative_to(self.vault)), list_id))
        return path

    def save_note(self, folder: str, title: str, body: str) -> Path | None:
        if not self.available: return None
        self.initialize()
        safe = re.sub(r'[<>:"/\\|?*]+', "-", title).strip(" .") or "Nota"
        assert self.vault is not None
        mapped = {"Notas": "08 - Notas", "Pesquisas": "06 - Pesquisas", "Projetos": "03 - Projetos", "Listas": "04 - Listas"}.get(folder, folder)
        path = self._managed_path(mapped, f"{safe}.md")
        existing = path.read_text(encoding="utf-8") if path.exists() else ""
        from datetime import date
        from knowledge.markdown import yaml_frontmatter
        prefix = yaml_frontmatter("research" if mapped == "06 - Pesquisas" else "note", date.today().isoformat()) if not existing else existing
        atomic_write(path, replace_managed_block(prefix, f"# {title}\n\n{body}"))
        return path

    def append_evolution(self, entry: dict) -> Path | None:
        if not self.available: return None
        self.initialize()
        path = self._managed_path("05 - Memórias", "Evolução da NATY.md")
        existing = path.read_text(encoding="utf-8") if path.exists() else "# Evolução da NATY\n"
        match = re.search(re.escape(BEGIN) + r"\n?(.*?)\n?" + re.escape(END), existing, re.DOTALL)
        previous = match.group(1).rstrip() if match else ""
        block = previous + ("\n\n" if previous else "") + "\n".join(
            f"- {key}: {json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value}"
            for key, value in entry.items())
        atomic_write(path, replace_managed_block(existing, block))
        return path

    def sync_skill_gaps(self, gaps: list[dict]) -> Path | None:
        if not self.available: return None
        self.initialize()
        path = self._managed_path("00 - Sistema", "Skills Sugeridas.md")
        existing = path.read_text(encoding="utf-8") if path.exists() else "# Skills Sugeridas\n"
        block = "## Confirmadas pelo usuário\n\n" + ("\n".join(f"- [ ] {item['request_text']}" for item in gaps) if gaps else "Nenhuma.")
        atomic_write(path, replace_managed_block(existing, block))
        return path
