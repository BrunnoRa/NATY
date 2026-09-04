from __future__ import annotations

from pathlib import Path
import sys
from time import perf_counter

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import Settings
from database.connection import Database
from database.migrations import migrate
from knowledge.graph import KnowledgeGraph
from knowledge.obsidian_index import ObsidianIndex


CASES = (
    ("Naty, o que você sabe sobre você mesma?", {"Naty/00 - Sistema/NATY.md"}),
    ("Quais são minhas preferências para a Naty?", {"Naty/01 - Eu/Preferências.md"}),
    (
        "Como decidimos lidar com tarefas pesadas?",
        {
            "Naty/00 - Sistema/Fluxo de Delegação.md",
            "Naty/00 - Sistema/Modos de Uso.md",
            "Naty/05 - Memórias/Decisões do Projeto.md",
            "Naty/00 - Sistema/NATY.md",
        },
    ),
)


def main() -> int:
    settings = Settings.load()
    managed = settings.managed_obsidian_path
    if not settings.obsidian_enabled or managed is None or not managed.is_dir():
        print("FAIL: Vault real da Naty não está configurado ou não existe.")
        return 1

    database = Database(settings.database_path)
    migrate(database)
    index = ObsidianIndex(database, settings.obsidian_vault_path, managed)
    started = perf_counter()
    report = index.index(validate=True)
    index_ms = (perf_counter() - started) * 1000
    started = perf_counter()
    nodes, edges = KnowledgeGraph(database).rebuild()
    graph_ms = (perf_counter() - started) * 1000

    print(f"Vault: {settings.obsidian_vault_path}")
    print(f"Pasta gerenciada: {managed}")
    print(f"Arquivos encontrados: {report['files_found']}")
    print(f"Notas indexadas: {report['notes_indexed']}")
    print(f"Links encontrados: {report['links_found']}")
    print(f"Projetos: {report['projects']}")
    print(f"Skills: {report['skills']}")
    print(f"Memórias: {report['memories']}")
    print(f"Markdown inválido: {report['invalid_markdown']}")
    print(f"Grafo: {len(nodes)} nós / {len(edges)} relações")
    print(f"Benchmark: índice {index_ms:.2f} ms / grafo {graph_ms:.2f} ms")
    if report["issues"]:
        for issue in report["issues"]:
            print(f"- {issue}")
        return 1

    failed = False
    for query, expected in CASES:
        started = perf_counter()
        results = index.search(query, limit=6)
        retrieval_ms = (perf_counter() - started) * 1000
        paths = [row["path"] for row in results]
        matched = expected.intersection(paths)
        status = "OK" if matched else "FAIL"
        print(f"{status}: {query}")
        print(f"  Encontrado: {paths[0] if paths else 'nenhum resultado'} ({retrieval_ms:.2f} ms)")
        failed = failed or not matched

    fts_count = database.one("SELECT count(*) AS total FROM obsidian_fts")["total"]
    if fts_count != report["notes_indexed"]:
        print(f"FAIL: FTS5 contém {fts_count} registros para {report['notes_indexed']} notas.")
        failed = True
    integrity = database.one("PRAGMA integrity_check")[0]
    outside_scope = database.one("SELECT count(*) FROM obsidian_documents WHERE path NOT LIKE 'Naty/%'")[0]
    print(f"SQLite: {integrity}; FTS5: {fts_count}; fora do escopo: {outside_scope}")
    if integrity != "ok" or outside_scope:
        failed = True
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
