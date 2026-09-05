from __future__ import annotations

import argparse
from pathlib import Path

from skills.registry import build_registry
from tools.obsidian import atomic_write, replace_managed_block


class _NoopRouter:
    def execute(self, intent):  # pragma: no cover - documentation registry only
        raise RuntimeError("Catálogo não executa Skills.")


SKILL_FILES = {
    "system_status": "Sistema.md", "briefing": "Briefing.md", "workspaces": "Workspace.md",
    "automations": "Automação.md", "windows": "Mídia e Launcher.md", "active_context": "Contexto.md",
    "clipboard": "Clipboard.md", "safe_files": "Arquivos.md", "temporal_memory": "Memória Temporal.md",
    "notifications": "Notificações.md",
}


def _frontmatter(type_: str) -> str:
    return f"---\ntype: {type_}\nstatus: active\nnaty_managed: true\n---\n"


def _skill_note(skill: dict) -> str:
    examples = "\n".join(f"- {value}" for value in skill["examples"])
    limitations = []
    if skill["requires_credentials"]: limitations.append("Requer credenciais configuradas.")
    if skill["requires_network"]: limitations.append("Depende de conexão com a internet.")
    if skill["requires_confirmation"]: limitations.append("Ações sensíveis exigem confirmação.")
    if not limitations: limitations.append("Funciona dentro das permissões locais declaradas no catálogo.")
    return (_frontmatter("naty-skill") + f"\n# {skill['name'].replace('_', ' ').title()}\n\n"
            f"## O que faz\n\n{skill['description']}\n\n## Exemplos\n\n{examples}\n\n"
            f"## Precisa de internet?\n\n{'Sim.' if skill['requires_network'] else 'Não.'}\n\n"
            f"## Confirmação\n\n{'Sim, para ações sensíveis.' if skill['requires_confirmation'] else 'Não para operações normais.'}\n\n"
            "## Limitações\n\n" + "\n".join(f"- {item}" for item in limitations) + "\n")


def _capabilities(skills: list[dict]) -> str:
    lines = ["Gerado a partir do SkillRegistry real da NATY.", ""]
    categories: dict[str, list[dict]] = {}
    for skill in skills: categories.setdefault(skill["category"], []).append(skill)
    for category in sorted(categories):
        lines.extend((f"## {category.title()}", ""))
        for skill in sorted(categories[category], key=lambda item: item["name"]):
            qualifiers = []
            if skill["requires_network"]: qualifiers.append("internet")
            if skill["requires_credentials"]: qualifiers.append("credenciais")
            if skill["requires_confirmation"]: qualifiers.append("confirmação em ações sensíveis")
            suffix = f" _Requer: {', '.join(qualifiers)}._" if qualifiers else ""
            lines.append(f"- **{skill['name']}** — {skill['description']}{suffix}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _write_new(path: Path, content: str, changed: list[Path]) -> None:
    if path.exists(): return
    atomic_write(path, content)
    changed.append(path)


def _upsert_managed(path: Path, heading: str, block: str, changed: list[Path]) -> None:
    existing = path.read_text(encoding="utf-8") if path.exists() else heading + "\n"
    updated = replace_managed_block(existing, block)
    if updated != existing:
        atomic_write(path, updated)
        changed.append(path)


def sync_catalog(managed: Path) -> list[Path]:
    managed = managed.expanduser().resolve()
    if managed.name.casefold() != "naty":
        raise ValueError("O destino deve ser a pasta gerenciada Naty.")
    skills = build_registry(_NoopRouter()).status()
    changed: list[Path] = []
    for folder in ("00 - Sistema", "05 - Memórias", "07 - Skills", "08 - Workspaces", "09 - Automação", "99 - Templates"):
        (managed / folder).mkdir(parents=True, exist_ok=True)

    _upsert_managed(managed / "00 - Sistema" / "Capacidades.md", "# Capacidades", _capabilities(skills), changed)
    _write_new(managed / "00 - Sistema" / "Privacidade.md", _frontmatter("system") + "\n# Privacidade\n\n- Dados locais permanecem locais quando uma integração externa não é necessária.\n- Clipboard e tela são acessados somente por comando explícito.\n- A NATY não captura teclas nem grava janelas continuamente.\n- Somente a pasta `Naty` do Vault é gerenciada.\n", changed)
    _write_new(managed / "00 - Sistema" / "Comandos Úteis.md", _frontmatter("system") + "\n# Comandos Úteis\n\n- Como está meu computador?\n- Onde paramos?\n- Como está meu dia?\n- Quais modos eu tenho?\n- Tem algo importante?\n- Em que programa eu estou?\n- Resume o que eu copiei.\n- O que você sabe fazer?\n", changed)
    _upsert_managed(managed / "00 - Sistema" / "Skills Sugeridas.md", "# Skills Sugeridas", "Nenhuma capacidade sugerida foi confirmada pelo usuário até agora.", changed)

    by_name = {skill["name"]: skill for skill in skills}
    for name, filename in SKILL_FILES.items():
        _write_new(managed / "07 - Skills" / filename, _skill_note(by_name[name]), changed)

    _write_new(managed / "08 - Workspaces" / "README.md", _frontmatter("workspace-index") + "\n# Workspaces\n\nModos seguros podem abrir aplicativos, URLs, arquivos e pastas permitidos ou iniciar um timer. Configure caminhos antes de ativar; nenhum workspace pessoal é inventado ou ativado automaticamente.\n\n- [[Workspace]]\n", changed)
    _write_new(managed / "08 - Workspaces" / "Workspace.md", "---\ntype: naty-workspace\nstatus: draft\n---\n# {{name}}\n\n## Aliases\n\n## Apps e URLs\n\n## Arquivos e pastas\n\n## Timer de foco\n\n## Observações\n", changed)
    _write_new(managed / "09 - Automação" / "Receitas de Automação.md", _frontmatter("automation-recipes") + "\n# Receitas de Automação\n\nExemplos seguros, não ativados automaticamente:\n\n- briefing diário em horário configurado;\n- lembrete de planejamento semanal;\n- abrir um workspace configurado;\n- lembrete recorrente;\n- aviso com cooldown para tarefa vencida.\n", changed)
    _write_new(managed / "05 - Memórias" / "Decisões Técnicas.md", _frontmatter("technical-decisions") + "\n# Decisões Técnicas\n\n- Desktop em C#/.NET/WPF e Core em Python comunicam-se por Named Pipes.\n- SQLite é a fonte de verdade estruturada; Obsidian mantém conhecimento consolidado.\n- Skills usam permissões explícitas e ações Windows são limitadas por allowlist.\n- Processamento pesado pode ser delegado ao ChatGPT por handoff assistido, sem scraping ou cookies.\n- A arquitetura é local-first e não inclui MiniMax.\n", changed)
    templates = {
        "Workspace.md": "---\ntype: workspace\nstatus: draft\n---\n# {{name}}\n\n## Objetivo\n\n## Ações permitidas\n\n## Timer\n",
        "Automação.md": "---\ntype: automation\nstatus: draft\n---\n# {{name}}\n\n## Gatilho\n\n## Ação permitida\n\n## Confirmação\n",
        "Decisão.md": "---\ntype: decision\ndate: {{date}}\n---\n# {{title}}\n\n## Contexto\n\n## Decisão\n\n## Consequências\n",
    }
    for filename, content in templates.items(): _write_new(managed / "99 - Templates" / filename, content, changed)

    additions = "## Memória\n- [[Decisões do Projeto]]\n- [[Decisões Técnicas]]\n\n## Workspaces\n- [[Workspaces]]\n- [[Workspace]]\n\n## Automação\n- [[Receitas de Automação]]"
    _upsert_managed(managed / "INDEX.md", "# NATY — Índice", additions, changed)
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("managed_path", type=Path)
    parser.add_argument("--database", type=Path)
    args = parser.parse_args()
    changed = sync_catalog(args.managed_path)
    for path in changed: print(path)
    print(f"changed={len(changed)}")
    if args.database:
        from database.connection import Database
        from database.migrations import migrate
        from knowledge.graph import KnowledgeGraph
        from knowledge.obsidian_index import ObsidianIndex
        db = Database(args.database)
        migrate(db)
        index = ObsidianIndex(db, args.managed_path.parent, args.managed_path)
        report = index.index(validate=True)
        KnowledgeGraph(db).rebuild()
        found = index.search("clipboard briefing workspace", limit=10)
        print(f"indexed={report['indexed']} skipped={report['skipped']} invalid={report['invalid_markdown']}")
        print("fts=" + ", ".join(item["title"] for item in found[:5]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
