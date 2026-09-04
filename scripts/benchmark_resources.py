from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile
import time

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    import psutil
except ImportError as exc:
    raise SystemExit("Instale psutil: python -m pip install psutil") from exc

from database.connection import Database
from config import Settings
from database.migrations import migrate
from database.repositories.lists import ListRepository
from database.repositories.tasks import TaskRepository
from tools.obsidian import ObsidianTool
from knowledge.graph import KnowledgeGraph
from knowledge.obsidian_index import ObsidianIndex


def mean(values): return sum(values) / len(values) if values else 0.0


def process_tree(process):
    try: children = process.children(recursive=True)
    except (psutil.NoSuchProcess, psutil.AccessDenied): children = []
    return [process, *children]


def prime_cpu(process) -> None:
    for item in process_tree(process):
        try: item.cpu_percent(None)
        except (psutil.NoSuchProcess, psutil.AccessDenied): pass


def tree_sample(process) -> tuple[int, float]:
    rss, cpu = 0, 0.0
    for item in process_tree(process):
        try: rss += item.memory_info().rss; cpu += item.cpu_percent(None)
        except (psutil.NoSuchProcess, psutil.AccessDenied): pass
    return rss, cpu


def measure_gui_idle(root: Path, flags: int, child_env: dict) -> dict:
    started = time.perf_counter()
    child = subprocess.Popen([sys.executable, "-m", "scripts.benchmark_gui_worker", str(root)], stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True, encoding="utf-8", creationflags=flags, env=child_env)
    ready = child.stdout.readline().strip(); startup_ms = (time.perf_counter() - started) * 1000
    if ready != "READY":
        error = child.stderr.read(); child.wait(timeout=5)
        reason = error.strip() or "Tk/tray indisponível"
        if "init.tcl" in reason: reason = "Tcl/Tk indisponível no runtime Python isolado desta execução"
        return {"available": False, "reason": reason}
    process = psutil.Process(child.pid); prime_cpu(process)
    def sample():
        rss, cpu = [], []
        for _ in range(2):
            time.sleep(1); sample_rss, sample_cpu = tree_sample(process); rss.append(sample_rss); cpu.append(sample_cpu)
        return round(mean(rss)/1024**2, 2), round(mean(cpu), 2)
    visible_rss, visible_cpu = sample()
    graph_marker = child.stdout.readline().strip()
    graph_rss, graph_cpu = sample()
    minimized_marker = child.stdout.readline().strip()
    minimized_rss, minimized_cpu = sample()
    child.wait(timeout=5)
    return {"available": True, "startup_ms": round(startup_ms, 2),
            "visible_rss_mib": visible_rss, "visible_cpu_percent": visible_cpu,
            "graph_active_rss_mib": graph_rss, "graph_active_cpu_percent": graph_cpu, "graph_marker": graph_marker,
            "idle_rss_mib": minimized_rss, "idle_cpu_percent": minimized_cpu, "minimized_marker": minimized_marker}


def measure() -> dict:
    with tempfile.TemporaryDirectory(prefix="naty-benchmark-") as temp:
        root = Path(temp)
        started = time.perf_counter()
        flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        child_env = os.environ.copy(); child_env["PYTHONIOENCODING"] = "utf-8"
        child = subprocess.Popen([sys.executable, "-m", "scripts.benchmark_worker", str(root)], stdin=subprocess.PIPE,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", creationflags=flags, env=child_env)
        ready = child.stdout.readline().strip()
        startup_ms = (time.perf_counter() - started) * 1000
        if ready != "READY":
            error = child.stderr.read(); child.kill(); raise RuntimeError(f"Worker falhou: {error}")
        process = psutil.Process(child.pid)
        idle_rss = []
        prime_cpu(process)
        idle_cpu = []
        for _ in range(3):
            time.sleep(1); sample_rss, sample_cpu = tree_sample(process); idle_rss.append(sample_rss); idle_cpu.append(sample_cpu)
        op_started = time.perf_counter(); child.stdin.write(json.dumps({"text": "cria tarefa benchmark 10 minutos"}) + "\n"); child.stdin.flush()
        child.stdout.readline(); command_ms = (time.perf_counter() - op_started) * 1000
        peak_rss = tree_sample(process)[0]
        research_started = time.perf_counter(); child.stdin.write('{"command":"research"}\n'); child.stdin.flush(); child.stdout.readline()
        research_ms = (time.perf_counter() - research_started) * 1000; research_rss = tree_sample(process)[0]
        child.stdin.write('{"command":"stop"}\n'); child.stdin.flush(); child.wait(timeout=5)

        db = Database(root / "operations.db"); migrate(db); tasks = TaskRepository(db)
        started = time.perf_counter()
        for n in range(100): tasks.create(f"Tarefa {n}", estimated_minutes=10)
        db_100_ms = (time.perf_counter() - started) * 1000
        vault = root / "vault"; vault.mkdir(); lists = ListRepository(db); record = lists.create("Lista de Compras")
        for item in ("Arroz", "Café", "Leite"): lists.add_item(record["id"], item)
        obsidian = ObsidianTool(True, str(vault), lists)
        started = time.perf_counter(); obsidian.sync_list(record["id"]); obsidian_ms = (time.perf_counter() - started) * 1000

        knowledge_vault = root / "knowledge-vault"; knowledge_vault.mkdir()
        for n in range(50):
            (knowledge_vault / f"Nota {n}.md").write_text(f"# Nota {n}\nProjeto Atlas assunto {n} [[Nota {(n + 1) % 50}]]", encoding="utf-8")
        index = ObsidianIndex(db, knowledge_vault)
        started = time.perf_counter(); index_report = index.index(); index_ms = (time.perf_counter() - started) * 1000
        started = time.perf_counter(); retrieved = index.search("Projeto Atlas", 6); retrieval_ms = (time.perf_counter() - started) * 1000
        graph = KnowledgeGraph(db); started = time.perf_counter(); graph_nodes, graph_edges = graph.rebuild(); graph_ms = (time.perf_counter() - started) * 1000

        optional = {"vosk": False, "sounddevice": False, "tts_sapi": os.name == "nt"}
        for module in ("vosk", "sounddevice"):
            try: __import__(module); optional[module] = True
            except ImportError: pass
        vm = psutil.virtual_memory()
        live_settings = Settings.load()
        voice_metrics = {"available": False, "reason": "Vosk, modelo ou dependência indisponível"}
        try:
            from vosk import Model
            model_path = Path(live_settings.vosk_model_path)
            if model_path.is_dir():
                before = psutil.Process().memory_info().rss; started = time.perf_counter(); model = Model(str(model_path)); loaded = psutil.Process().memory_info().rss
                voice_metrics = {"available": True, "model_load_ms": round((time.perf_counter()-started)*1000,2), "rss_delta_mib": round((loaded-before)/1024**2,2), "listening": "não medido sem fala controlada"}
                del model
        except Exception as exc:
            voice_metrics = {"available": False, "reason": f"{type(exc).__name__}: {exc}"}
        tts_started = time.perf_counter()
        from voice.sapi_tts import SapiTTS
        SapiTTS(); tts_init_ms = (time.perf_counter() - tts_started) * 1000
        gui = measure_gui_idle(root, flags, child_env)
        return {
            "measured_at": datetime.now().astimezone().isoformat(timespec="seconds"),
            "hardware": {"platform": platform.platform(), "processor": platform.processor() or "não informado pelo sistema",
                         "physical_cores": psutil.cpu_count(logical=False), "logical_cores": psutil.cpu_count(),
                         "total_ram_gib": round(vm.total / 1024**3, 2), "python": platform.python_version()},
            "startup_ms": round(startup_ms, 2), "idle_rss_mib": round(mean(idle_rss) / 1024**2, 2),
            "idle_cpu_percent": round(mean(idle_cpu), 2), "command_ms": round(command_ms, 2),
            "peak_core_rss_mib": round(peak_rss / 1024**2, 2), "database_100_inserts_ms": round(db_100_ms, 2),
            "obsidian_sync_ms": round(obsidian_ms, 2), "optional": optional,
            "knowledge": {"documents": index_report["indexed"], "index_ms": round(index_ms,2), "retrieval_ms": round(retrieval_ms,2), "retrieved": len(retrieved), "graph_ms": round(graph_ms,2), "nodes": len(graph_nodes), "edges": len(graph_edges)},
            "research_local_ms": round(research_ms, 2), "research_rss_mib": round(research_rss / 1024**2, 2),
            "tts_provider_init_ms": round(tts_init_ms, 3),
            "voice": voice_metrics,
            "llm": {"available": False, "reason": "não configurada"} if not live_settings.ai_enabled else {"available": True, "measurement": "execute scripts/benchmark_llm.py"},
            "google": {"available": False, "reason": "não autorizado"} if not live_settings.google_enabled else {"available": True, "measurement": "execute os smokes Gmail/Calendar"},
            "research_measurement": "pipeline medido com provider local determinístico; rede externa não incluída",
            "gui": gui,
        }


def markdown(data: dict) -> str:
    h = data["hardware"]
    knowledge = data["knowledge"]
    gui = data.get("gui", {})
    gui_rows = (f"| Startup completo (GUI + tray + hotkey) | {gui['startup_ms']} ms |\n"
                f"| UI visível — RAM / CPU | {gui['visible_rss_mib']} MiB / {gui['visible_cpu_percent']}% |\n"
                f"| Grafo ativo — RAM / CPU | {gui['graph_active_rss_mib']} MiB / {gui['graph_active_cpu_percent']}% |\n"
                f"| Minimizada — RAM / CPU | {gui['idle_rss_mib']} MiB / {gui['idle_cpu_percent']}% |") if gui.get("available") else ""
    return f"""# Benchmark da Naty

Medição local gerada em `{data['measured_at']}` por `scripts/benchmark_resources.py`. Os valores descrevem esta execução e não são uma promessa para outras máquinas.

## Ambiente

- Sistema: {h['platform']}
- Processador: {h['processor']}
- Núcleos: {h['physical_cores']} físicos / {h['logical_cores']} lógicos
- RAM total detectada: {h['total_ram_gib']} GiB
- Python: {h['python']}

## Resultados

| Medida | Valor observado |
|---|---:|
| Startup do core até pronto | {data['startup_ms']} ms |
| RAM RSS média em idle (core, sem GUI) | {data['idle_rss_mib']} MiB |
| CPU média em idle (3 amostras) | {data['idle_cpu_percent']}% |
| Comando local simples | {data['command_ms']} ms |
| RSS após comando local | {data['peak_core_rss_mib']} MiB |
| Pipeline de pesquisa local (5 resultados) | {data['research_local_ms']} ms |
| RSS durante pipeline de pesquisa local | {data['research_rss_mib']} MiB |
| 100 inserções SQLite | {data['database_100_inserts_ms']} ms |
| Sincronização Obsidian (3 itens) | {data['obsidian_sync_ms']} ms |
| Índice Obsidian incremental ({knowledge['documents']} documentos) | {knowledge['index_ms']} ms |
| Retrieval FTS ({knowledge['retrieved']} resultados) | {knowledge['retrieval_ms']} ms |
| Grafo ({knowledge['nodes']} nós / {knowledge['edges']} arestas) | {knowledge['graph_ms']} ms |
| Inicialização do provider SAPI (sem fala) | {data['tts_provider_init_ms']} ms |
{gui_rows}

## Não medido nesta execução

- Voz/STT: {json.dumps(data['voice'], ensure_ascii=False)}
- IA local: {json.dumps(data['llm'], ensure_ascii=False)}
- Google: {json.dumps(data['google'], ensure_ascii=False)}
- Pesquisa na rede: {data['research_measurement']}. Latência DDGS real varia por conexão e fonte.
{('- GUI/tray: medido em fases visível, grafo ativo e minimizada, com tray e hotkey ativos.' if gui.get('available') else '- GUI/tray: não medido nesta execução: ' + gui.get('reason', 'indisponível'))}

As métricas de processo somam o lançador da `.venv` e todos os processos-filhos recursivos para não subestimar o runtime Python deste ambiente.

## Reproduzir

```powershell
python scripts/benchmark_resources.py
```

O script cria dados temporários, mede um processo-filho real e atualiza este arquivo. Não usa internet, GPU, microfone nem LLM.
"""


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--json", action="store_true"); parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args(); data = measure()
    if not args.no_write: (PROJECT_ROOT / "BENCHMARK.md").write_text(markdown(data), encoding="utf-8")
    print(json.dumps(data, ensure_ascii=False, indent=2) if args.json else markdown(data)); return 0


if __name__ == "__main__": raise SystemExit(main())
