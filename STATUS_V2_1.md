# Status NATY V2.1

Atualizado em: 2026-09-04

## BLOCO 0 — BASELINE: CONCLUÍDO

### Concluído

- Documentação obrigatória lida: `README.md`, `ARCHITECTURE.md`, `BASELINE_V2.md`, `BENCHMARK.md`, `SECURITY.md`, `PRIVACY.md` e `ROADMAP.md`.
- Suíte V2 validada sem regressões funcionais.
- Smoke gráfico tentado no runtime disponível nesta sessão.

### Arquivos alterados

- `STATUS_V2_1.md` (criado).

### Testes

- `python -m unittest discover -s tests -p "test_*.py" -v`: 75 casos descobertos, 74 aprovados e 1 caso DPAPI marcado como `skipped` porque o perfil Windows do runner não oferece proteção DPAPI; resultado geral `OK`.
- `python -m scripts.smoke_gui`: não abriu a janela porque o Python embutido da sessão não possui Tcl/Tk utilizável (`init.tcl` ausente).

### Limitações

- Não há instalação de Python desktop registrada no `py` launcher desta sessão; a validação visual da janela precisa ser repetida em um runtime com Tcl/Tk. O problema ocorre antes do código da aplicação criar a interface e não causou regressão nos testes.
- A pasta fornecida não possui metadados Git acessíveis, portanto o estado foi auditado diretamente pelos arquivos.

### Próximo bloco

- BLOCO 1 — configurar e importar com segurança o Vault real do usuário, validar Markdown/wikilinks, FTS5, grafo e os três casos reais de retrieval.

## BLOCO 1 — OBSIDIAN REAL DO USUÁRIO: CONCLUÍDO

### Concluído

- Configuração ativa separada em:
  - `obsidian_vault_path = C:\Users\yster\Documents\Obsidian Vault`;
  - `naty_obsidian_path = C:\Users\yster\Documents\Obsidian Vault\Naty`.
- Leitura, indexação e escrita da Naty confinadas à subpasta exata `Naty/`; configuração que aponte para fora dela é rejeitada.
- Base manual existente preservada: o importador não executa bootstrap nem sobrescreve notas.
- Markdown real validado como UTF-8, com checagem de conteúdo, H1 e fechamento de frontmatter.
- FTS5 alimentado e verificado com 33 documentos.
- KnowledgeGraph reconstruído com 35 nós e 88 relações; notas de projeto, skill e memória recebem tipos próprios no grafo.
- Ranking de retrieval aprimorado com stopwords pt-BR, prioridade de título exato e expansão leve para contexto de delegação.
- Relatório real:
  - Arquivos encontrados: 33;
  - Notas indexadas: 33;
  - Links encontrados: 55;
  - Projetos: 1;
  - Skills: 8;
  - Memórias: 1;
  - Markdown inválido: 0;
  - Documentos fora de `Naty/`: 0.
- Os três casos reais de retrieval passaram:
  - `Naty, o que você sabe sobre você mesma?` → `Naty/00 - Sistema/NATY.md`;
  - `Quais são minhas preferências para a Naty?` → `Naty/01 - Eu/Preferências.md`;
  - `Como decidimos lidar com tarefas pesadas?` → contexto de delegação em `NATY.md`, `Decisões do Projeto.md`, `Modos de Uso.md`, `Fluxo de Delegação.md` e skill correspondente.
- Smoke da aplicação em modo CLI consultou o Vault real e retornou `NATY` como primeira fonte.

### Arquivos alterados

- Configuração/runtime: `config.py`, `config.toml`, `core/assistant.py`.
- Obsidian/conhecimento: `knowledge/obsidian_bootstrap.py`, `knowledge/obsidian_index.py`, `knowledge/graph.py`, `tools/obsidian.py`.
- Interface de configuração: `ui/onboarding.py`, `ui/main_window.py`.
- Validação reproduzível: `scripts/smoke_obsidian_real.py`.
- Testes: `tests/test_core.py`, `tests/test_knowledge_v2.py`, `tests/test_obsidian.py`.
- Documentação: `README.md`, `ARCHITECTURE.md`, `PRIVACY.md`, `STATUS_V2_1.md`.
- Dados locais: `data/naty.db` recebeu somente o índice FTS5 e o grafo derivados das 33 notas existentes.

### Testes e smoke

- Testes focados (`knowledge_v2`, `obsidian`, `core`): 19/19 aprovados.
- Suíte completa: 78 casos descobertos, 77 aprovados e 1 `skipped`; os 75 casos anteriores continuam sem falhas e foram adicionados 3 casos de segurança/retrieval. O único skip é o caso DPAPI indisponível no perfil Windows do runner.
- `python -m scripts.smoke_obsidian_real`: aprovado contra `C:\Users\yster\Documents\Obsidian Vault\Naty`, sem fixtures.
- `python main.py --command "Naty, o que voce sabe sobre voce mesma?"`: aprovado, usando a aplicação e banco atuais.
- `PRAGMA integrity_check`: `ok`.

### Benchmark

- Validação/indexação completa das 33 notas reais: 845,58 ms.
- Reconstrução do grafo real: 28,33 ms.
- Retrieval dos três casos: 27,01 ms, 28,01 ms e 27,20 ms.
- A indexação normal no startup continua incremental e ignora arquivos cujo `mtime` não mudou; a medição de 845,58 ms inclui reler e validar todos os arquivos propositalmente.

### Limitações reais

- A validação visual da GUI continua pendente por ausência de Tcl/Tk no Python embutido desta sessão; CLI, core, indexação, FTS5 e grafo foram executados normalmente.
- O console do runner usa uma página de código que pode exibir acentos como caracteres substitutos; os arquivos, strings Python e registros SQLite permanecem em UTF-8 e os testes com acentos passaram.
- O relatório classifica projetos, skills e memórias pela estrutura de pastas atual do Vault; não tenta inferir tipos arbitrários fora dessas pastas.
- Nenhum arquivo Markdown do Vault foi criado, apagado ou sobrescrito neste bloco.

### Próximo bloco

- BLOCO 2 — VOZ REAL. Começar pelo diagnóstico de dispositivos/microfone e somente considerar o bloco concluído após validar o fluxo real de fala, Vosk, execução e resposta SAPI.

## BLOCO 2 — VOZ REAL: PENDENTE

## BLOCO 3 — APLICATIVO WINDOWS REAL: PENDENTE

## BLOCO 4 — NOVA EXPERIÊNCIA VISUAL: PENDENTE

## BLOCO 5 — NATY COMO ORQUESTRADORA: PENDENTE

## BLOCO 6 — DELEGAÇÃO PARA CHATGPT: PENDENTE

## BLOCO 7 — LAUNCHER INTELIGENTE: PENDENTE

## BLOCO 8 — AUTOEVOLUÇÃO CONTROLADA: PENDENTE

## BLOCO 9 — SINCRONIZAÇÃO DESKTOP/NOTEBOOK: PENDENTE

## BLOCO 10 — TESTE COMPLETO: PENDENTE
