# Benchmark da Naty

Medição local gerada em `2026-09-04T14:21:53-03:00` por `scripts/benchmark_resources.py`. Os valores descrevem esta execução e não são uma promessa para outras máquinas.

## Ambiente

- Sistema: Windows-11-10.0.26200-SP0
- Processador: Intel64 Family 6 Model 140 Stepping 1, GenuineIntel
- Núcleos: 4 físicos / 8 lógicos
- RAM total detectada: 15.73 GiB
- Python: 3.12.14

## Resultados

| Medida | Valor observado |
|---|---:|
| Startup do core até pronto | 348.45 ms |
| RAM RSS média em idle (core, sem GUI) | 41.77 MiB |
| CPU média em idle (3 amostras) | 0.0% |
| Comando local simples | 39.61 ms |
| RSS após comando local | 41.85 MiB |
| Pipeline de pesquisa local (5 resultados) | 48.87 ms |
| RSS durante pipeline de pesquisa local | 41.88 MiB |
| 100 inserções SQLite | 1882.1 ms |
| Sincronização Obsidian (3 itens) | 86.11 ms |
| Índice Obsidian incremental (50 documentos) | 467.28 ms |
| Retrieval FTS (6 resultados) | 44.97 ms |
| Grafo (51 nós / 100 arestas) | 19.81 ms |
| Inicialização do provider SAPI (sem fala) | 1.9 ms |
| Startup completo (GUI + tray + hotkey) | 842.66 ms |
| UI visível — RAM / CPU | 66.76 MiB / 0.0% |
| Grafo ativo — RAM / CPU | 66.76 MiB / 0.0% |
| Minimizada — RAM / CPU | 66.77 MiB / 0.0% |

## Não medido nesta execução

- Voz/STT: {"available": true, "model_load_ms": 423.52, "rss_delta_mib": 87.74, "listening": "não medido sem fala controlada"}
- IA local: {"available": false, "reason": "não configurada"}
- Google: {"available": false, "reason": "não autorizado"}
- Pesquisa na rede: pipeline medido com provider local determinístico; rede externa não incluída. Latência DDGS real varia por conexão e fonte.
- GUI/tray: medido em fases visível, grafo ativo e minimizada, com tray e hotkey ativos.

As métricas de processo somam o lançador da `.venv` e todos os processos-filhos recursivos para não subestimar o runtime Python deste ambiente.

## Reproduzir

```powershell
python scripts/benchmark_resources.py
```

O script cria dados temporários, mede um processo-filho real e atualiza este arquivo. Não usa internet, GPU, microfone nem LLM.
