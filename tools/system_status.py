from __future__ import annotations

from dataclasses import asdict

from core.models import ToolResult
from system_context.snapshot import SystemContextProvider


class SystemStatusTool:
    def __init__(self, provider: SystemContextProvider | None = None):
        self.provider = provider or SystemContextProvider()

    @staticmethod
    def _gib(mib) -> str:
        return f"{float(mib) / 1024:.1f} GiB"

    def status(self, focus: str = "general", diagnose: bool = False) -> ToolResult:
        snapshot = self.provider.collect()
        data = asdict(snapshot)
        memory, disk, naty = snapshot.memory, snapshot.disk, snapshot.naty_process_tree
        top = snapshot.top_processes[0] if snapshot.top_processes else None
        if diagnose:
            findings = []
            if (snapshot.cpu_percent or 0) >= 90:
                findings.append(f"CPU está em {snapshot.cpu_percent:.0f}%")
            if memory.get("percent", 0) >= 90:
                findings.append(f"memória está em {memory['percent']:.0f}%")
            if disk.get("percent", 0) >= 95:
                findings.append(f"o disco está {disk['percent']:.0f}% ocupado")
            if findings:
                message = "Encontrei pressão agora: " + ", ".join(findings) + "."
                if top:
                    message += f" O maior consumo de RAM é {top['name']} ({top['ram_mib']:.0f} MiB)."
            else:
                message = "Não encontrei pressão alta de CPU, memória ou disco nesta medição."
                if top:
                    message += f" O maior consumo de RAM agora é {top['name']} ({top['ram_mib']:.0f} MiB)."
        elif focus == "memory" and "percent" in memory:
            message = (f"A memória está em {memory['percent']:.0f}%: {self._gib(memory['used_mib'])} usados de "
                       f"{self._gib(memory['total_mib'])}, com {self._gib(memory['available_mib'])} disponíveis.")
        elif focus == "top_memory":
            message = (f"O maior consumo de RAM agora é {top['name']} com {top['ram_mib']:.0f} MiB."
                       if top else "Não consegui ler os processos em execução.")
        elif focus == "naty":
            message = (f"A árvore da NATY usa {naty['ram_mib']:.1f} MiB em {naty['processes']} processo(s)."
                       if naty.get("ram_mib") is not None else "Não consegui medir a árvore de processos da NATY.")
        else:
            parts = []
            if snapshot.cpu_percent is not None: parts.append(f"CPU {snapshot.cpu_percent:.0f}%")
            if "percent" in memory: parts.append(f"RAM {memory['percent']:.0f}%")
            if "percent" in disk: parts.append(f"disco {disk['percent']:.0f}% ocupado")
            message = "Seu computador está com " + ", ".join(parts) + "." if parts else "As métricas do computador estão indisponíveis agora."
        return ToolResult(True, message, data, type="system_status",
                          ui_hint={"mode": "context", "panel": "system", "title": "Sistema"})
