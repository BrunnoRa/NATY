# Baseline real antes da V2

Medição realizada em 4 de setembro de 2026, antes da primeira alteração funcional da V2.

## Ambiente

- Windows 11 `10.0.26200`, CPU Intel64 Family 6 Model 140, 4 núcleos físicos/8 lógicos e 15,73 GiB de RAM.
- Python 3.12.14 na `.venv`.
- A pasta não é um repositório Git.
- Banco `data/naty.db` íntegro (`PRAGMA integrity_check = ok`) e sem registros nas nove entidades consultadas.

## Funcionalidade encontrada

- SQLite/migrations, tarefas, projetos, listas, lembretes, compromissos, notas e memórias.
- Parser determinístico pt-BR, contexto curto, planner, Obsidian com escrita atômica e DDGS.
- GUI Tkinter clara, mini janela, tray, RegisterHotKey, SAPI, Vosk opcional, scheduler e confirmação para apagar tarefas.
- NoAIProvider e LlamaCppProvider básico; o LLM não participa do roteamento.

## Validação

- 47/47 testes offline passaram em 2,147 s.
- Aplicativo gráfico abriu e encerrou corretamente (`BASELINE_APP_OK`).
- Benchmark repetido sem sobrescrever o documento V1:
  - core: 324,19 ms até pronto;
  - GUI + tray + hotkey: 745,61 ms;
  - idle reportado: 5,16 MiB RSS e 0,0% CPU;
  - comando local: 58,28 ms;
  - pipeline de pesquisa local: 10,75 ms;
  - 100 inserções SQLite: 2.293,91 ms;
  - Obsidian: 17,93 ms.

## Lacunas confirmadas

- Vosk e sounddevice não instalados; microfone/STT não testados.
- Sem instalador de voz, escolha de microfone, detecção robusta de silêncio ou listagem de vozes.
- Sem bootstrap rico do Vault, frontmatter, FTS5, retrieval ou grafo.
- Sem ConversationEngine, SkillRegistry ou uso contextual do LLM.
- LlamaCppProvider sem limite de RAM, lock ou descarregamento temporizado.
- Sem Gmail/Google Calendar/OAuth/DPAPI.
- Pesquisa sem sessão/claims/cross-check e salvamento ainda no layout V1.
- Sem onboarding ou proatividade configurável.
- GUI funcional, mas não possui dashboard/grafo/status detalhado de módulos.

## Referências estudadas

- Microsoft JARVIS: planejamento, seleção, execução e geração de resposta. A Naty não adotará seu conjunto pesado de modelos/servidores.
- OpenJarvis: primitives/registries, execução on-demand, memória e eficiência como requisito. A Naty não adotará Docker, engines permanentes ou loops agentivos irrestritos.
