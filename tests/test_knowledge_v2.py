from pathlib import Path

from database.repositories.projects import ProjectRepository
from database.repositories.tasks import TaskRepository
from knowledge.context import ContextNote, ContextPack
from knowledge.graph import KnowledgeGraph
from knowledge.markdown import parse_markdown
from knowledge.obsidian_bootstrap import ObsidianBootstrap
from knowledge.obsidian_index import ObsidianIndex
from knowledge.retriever import ObsidianContextRetriever
from tests.base import TempDatabaseTest


class KnowledgeV2Tests(TempDatabaseTest):
    def setUp(self):
        super().setUp()
        self.vault = self.root / "Vault"
        self.vault.mkdir()

    def test_bootstrap_is_non_destructive(self):
        custom = self.vault / "Naty" / "01 - Eu" / "Perfil.md"
        custom.parent.mkdir(parents=True)
        custom.write_text("# Meu perfil\nNão sobrescrever", encoding="utf-8")
        created = ObsidianBootstrap(self.vault).prepare()
        self.assertTrue((self.vault / "Naty" / "99 - Templates" / "Projeto.md").is_file())
        self.assertEqual(custom.read_text(encoding="utf-8"), "# Meu perfil\nNão sobrescrever")
        self.assertNotIn(custom, created)

    def test_markdown_wikilinks_frontmatter_and_tags(self):
        parsed = parse_markdown("---\ntype: project\n---\n# Casa\n[[Compras|lista]] [[Pessoa#Contato]] #ativo")
        self.assertEqual(parsed["title"], "Casa")
        self.assertEqual(parsed["frontmatter"]["type"], "project")
        self.assertEqual(parsed["wikilinks"], ["Compras", "Pessoa"])
        self.assertIn("ativo", parsed["tags"])

    def test_incremental_fts_and_delete(self):
        note = self.vault / "Projeto.md"
        note.write_text("# Projeto Atlas\nComprar cadeira ergonômica", encoding="utf-8")
        index = ObsidianIndex(self.db, self.vault)
        first = index.index()
        second = index.index()
        self.assertEqual(first["indexed"], 1)
        self.assertEqual(second["skipped"], 1)
        self.assertEqual(index.search("cadeira")[0]["title"], "Projeto Atlas")
        note.unlink()
        self.assertEqual(index.index()["deleted"], 1)
        self.assertEqual(index.search("cadeira"), [])

    def test_graph_builds_wikilink_edges(self):
        (self.vault / "A.md").write_text("# A\n[[B]]", encoding="utf-8")
        (self.vault / "B.md").write_text("# B", encoding="utf-8")
        ObsidianIndex(self.db, self.vault).index()
        nodes, edges = KnowledgeGraph(self.db).rebuild()
        self.assertIn("note:A.md", {node.id for node in nodes})
        self.assertIn(("note:A.md", "note:B.md", "wikilink"), {(edge.source, edge.target, edge.relation) for edge in edges})

    def test_context_budget_and_structured_retrieval(self):
        pack = ContextPack("atlas", [ContextNote("A", "A.md", "x" * 500)], max_chars=80)
        self.assertLessEqual(len(pack.as_prompt_data()), 80)
        projects, tasks = ProjectRepository(self.db), TaskRepository(self.db)
        project = projects.create("Atlas")
        tasks.create("Revisar mapa", project_id=project["id"])
        result = ObsidianContextRetriever(None, projects, tasks).retrieve("como está Atlas")
        self.assertEqual(result.structured["project"]["name"], "Atlas")
        self.assertEqual(len(result.structured["tasks"]), 1)

    def test_managed_scope_report_and_realistic_retrieval(self):
        managed = self.vault / "Naty"
        system = managed / "00 - Sistema"
        preferences = managed / "01 - Eu"
        skills = managed / "07 - Skills"
        projects = managed / "03 - Projetos"
        memories = managed / "05 - Memórias"
        for folder in (system, preferences, skills, projects, memories):
            folder.mkdir(parents=True, exist_ok=True)
        (self.vault / "Bem-vindo.md").write_text("# Fora do escopo", encoding="utf-8")
        (system / "NATY.md").write_text("# NATY\nAgente pessoal. [[Fluxo de Delegação]]", encoding="utf-8")
        (system / "Fluxo de Delegação.md").write_text("# Fluxo de Delegação\nDelegar tarefas pesadas.", encoding="utf-8")
        (preferences / "Preferências.md").write_text("# Preferências\nQuero baixo consumo na Naty.", encoding="utf-8")
        (skills / "Pesquisa.md").write_text("# Pesquisa", encoding="utf-8")
        (projects / "NATY Agent.md").write_text("# NATY Agent", encoding="utf-8")
        (memories / "Decisões.md").write_text("# Decisões", encoding="utf-8")

        index = ObsidianIndex(self.db, self.vault, managed)
        report = index.index(validate=True)

        self.assertEqual(report["files_found"], 6)
        self.assertEqual(report["notes_indexed"], 6)
        self.assertEqual(report["links_found"], 1)
        self.assertEqual((report["projects"], report["skills"], report["memories"]), (1, 1, 1))
        self.assertEqual(report["invalid_markdown"], 0)
        indexed_paths = {row["path"] for row in self.db.query("SELECT path FROM obsidian_documents")}
        self.assertNotIn("Bem-vindo.md", indexed_paths)
        self.assertEqual(index.search("Naty, o que você sabe sobre você mesma?")[0]["path"], "Naty/00 - Sistema/NATY.md")
        self.assertEqual(index.search("minhas preferências para a Naty")[0]["path"], "Naty/01 - Eu/Preferências.md")
        delegation = {row["path"] for row in index.search("tarefas pesadas")}
        self.assertIn("Naty/00 - Sistema/Fluxo de Delegação.md", delegation)
