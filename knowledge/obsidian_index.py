from __future__ import annotations

from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import unicodedata

from database.connection import Database
from knowledge.markdown import parse_markdown


class ObsidianIndex:
    _STOPWORDS = {
        "a", "as", "com", "como", "da", "das", "de", "do", "dos", "e", "ela", "em", "eu",
        "me", "mesma", "meu", "minhas", "o", "os", "para", "por", "que", "quais", "sao", "sobre",
        "uma", "voce",
    }

    def __init__(self, db: Database, vault: str | Path, scope: str | Path | None = None):
        self.db = db
        self.vault = Path(vault).expanduser().resolve()
        self.scope = Path(scope).expanduser().resolve() if scope else self.vault
        try:
            self.scope.relative_to(self.vault)
        except ValueError as exc:
            raise ValueError("O escopo de indexação deve ficar dentro do Vault.") from exc

    @staticmethod
    def _validation_issues(raw: str, relative: str) -> list[str]:
        issues: list[str] = []
        if not raw.strip():
            issues.append(f"{relative}: arquivo vazio")
        if raw.startswith("---") and not re.search(r"\A---\r?\n.*?\r?\n---(?:\r?\n|\Z)", raw, re.DOTALL):
            issues.append(f"{relative}: frontmatter sem delimitador de fechamento")
        if raw.strip() and not re.search(r"^#\s+\S", raw, re.MULTILINE):
            issues.append(f"{relative}: título H1 ausente")
        return issues

    @staticmethod
    def _category_counts(paths: list[Path], scope: Path) -> dict[str, int]:
        counts = {"projects": 0, "skills": 0, "memories": 0}
        for path in paths:
            relative = path.relative_to(scope).as_posix()
            if relative.startswith("03 - Projetos/"): counts["projects"] += 1
            elif relative.startswith("07 - Skills/"): counts["skills"] += 1
            elif relative.startswith("05 - Memórias/"): counts["memories"] += 1
        return counts

    def index(self, validate: bool = False) -> dict:
        empty = {"indexed": 0, "skipped": 0, "deleted": 0, "files_found": 0,
                 "notes_indexed": 0, "links_found": 0, "projects": 0, "skills": 0,
                 "memories": 0, "invalid_markdown": 0, "issues": []}
        if not self.scope.is_dir(): return empty
        paths = sorted(path for path in self.scope.rglob("*.md") if not path.is_symlink() and path.is_file())
        categories = self._category_counts(paths, self.scope)
        existing = {r["path"]: dict(r) for r in self.db.query("SELECT id,path,mtime,content_hash FROM obsidian_documents")}
        seen, indexed, skipped, invalid_files, issues = set(), 0, 0, 0, []
        for path in paths:
            relative = path.relative_to(self.vault).as_posix(); seen.add(relative); stat = path.stat()
            old = existing.get(relative)
            if old and abs(float(old["mtime"]) - stat.st_mtime) < 0.0001 and not validate:
                skipped += 1; continue
            try:
                raw = path.read_text(encoding="utf-8", errors="strict")[:2_000_000]
            except (OSError, UnicodeError) as exc:
                issues.append(f"{relative}: não foi possível ler como UTF-8 ({exc})")
                invalid_files += 1
                continue
            if validate:
                file_issues = self._validation_issues(raw, relative)
                issues.extend(file_issues)
                invalid_files += bool(file_issues)
            digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
            if old and old["content_hash"] == digest:
                self.db.execute("UPDATE obsidian_documents SET mtime=? WHERE id=?", (stat.st_mtime, old["id"])); skipped += 1; continue
            parsed = parse_markdown(raw); title = parsed["title"] or path.stem
            with self.db.transaction() as conn:
                conn.execute("""INSERT INTO obsidian_documents(path,title,tags,frontmatter,body,wikilinks,mtime,content_hash,indexed_at)
                    VALUES(?,?,?,?,?,?,?,?,?) ON CONFLICT(path) DO UPDATE SET title=excluded.title,tags=excluded.tags,
                    frontmatter=excluded.frontmatter,body=excluded.body,wikilinks=excluded.wikilinks,mtime=excluded.mtime,
                    content_hash=excluded.content_hash,indexed_at=excluded.indexed_at""",
                    (relative, title, " ".join(parsed["tags"]), json.dumps(parsed["frontmatter"], ensure_ascii=False), parsed["plain"],
                     json.dumps(parsed["wikilinks"], ensure_ascii=False), stat.st_mtime, digest, datetime.now().astimezone().isoformat()))
                row = conn.execute("SELECT id FROM obsidian_documents WHERE path=?", (relative,)).fetchone()
                conn.execute("DELETE FROM obsidian_fts WHERE rowid=?", (row[0],))
                conn.execute("INSERT INTO obsidian_fts(rowid,path,title,tags,body) VALUES(?,?,?,?,?)", (row[0], relative, title, " ".join(parsed["tags"]), parsed["plain"]))
            indexed += 1
        deleted = 0
        for relative, old in existing.items():
            if relative not in seen:
                with self.db.transaction() as conn:
                    conn.execute("DELETE FROM obsidian_fts WHERE rowid=?", (old["id"],)); conn.execute("DELETE FROM obsidian_documents WHERE id=?", (old["id"],))
                deleted += 1
        current = [dict(row) for row in self.db.query("SELECT path,wikilinks FROM obsidian_documents") if row["path"] in seen]
        links_found = sum(len(json.loads(row["wikilinks"] or "[]")) for row in current)
        return {
            "indexed": indexed, "skipped": skipped, "deleted": deleted,
            "files_found": len(paths), "notes_indexed": len(current), "links_found": links_found,
            **categories, "invalid_markdown": invalid_files, "issues": issues,
        }

    @staticmethod
    def _plain(value: str) -> str:
        normalized = unicodedata.normalize("NFD", value.casefold())
        return " ".join(re.findall(r"[a-z0-9]+", "".join(c for c in normalized if unicodedata.category(c) != "Mn")))

    def search(self, query: str, limit: int = 6) -> list[dict]:
        terms = [term for term in self._plain(query).split() if len(term) > 1 and term not in self._STOPWORDS][:8]
        expansions: list[str] = []
        if any(term.startswith("pesad") or term.startswith("complex") for term in terms):
            expansions.extend(("deleg", "context"))
        search_terms = list(dict.fromkeys(terms + expansions))
        if not search_terms: return []
        expression = " OR ".join(f'"{term}"*' for term in search_terms)
        try:
            rows = self.db.query("""SELECT d.*, bm25(obsidian_fts) score FROM obsidian_fts
                JOIN obsidian_documents d ON d.id=obsidian_fts.rowid WHERE obsidian_fts MATCH ? ORDER BY score LIMIT ?""", (expression, max(limit * 5, 20)))
        except Exception:
            like = f"%{search_terms[0]}%"; rows = self.db.query("SELECT *, 0 score FROM obsidian_documents WHERE title LIKE ? OR body LIKE ? LIMIT ?", (like, like, limit))
        ranked = []
        for row in rows:
            item = dict(row); title = self._plain(item["title"]); haystack = f"{title} {self._plain(item['body'])}"
            coverage = sum(term in haystack for term in terms)
            expansion_hits = sum(term in haystack for term in expansions)
            title_hits = sum(term in title for term in search_terms)
            exact_title_hits = sum(title == term for term in search_terms)
            pair_hits = sum(f"{left} {right}" in haystack for left, right in zip(terms, terms[1:]))
            item["relevance"] = coverage * 4 + title_hits * 8 + exact_title_hits * 20 + pair_hits * 2 + expansion_hits
            ranked.append(item)
        ranked.sort(key=lambda item: (-item["relevance"], float(item.get("score") or 0), item["path"]))
        rows = ranked[:limit]
        now = datetime.now().astimezone().isoformat(timespec="seconds")
        if rows:
            with self.db.transaction() as conn:
                conn.executemany("UPDATE obsidian_documents SET last_accessed=? WHERE id=?", [(now, row["id"]) for row in rows])
        return [dict(r) for r in rows]
