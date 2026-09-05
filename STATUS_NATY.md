# CURRENT HANDOFF

Branch: `feat/naty-v3-hybrid`

Commit: `HEAD` — `feat: package hybrid NATY Windows app`

Último bloco concluído: Bloco 8 — empacotamento e instalador híbridos para Windows.

Testes: suíte completa pré-package com 130 testes (129 aprovados + 1 skip DPAPI esperado); 6 testes de packaging; build WPF 0/0; smokes do Core e do Naty.exe empacotados com shutdown limpo; git diff check verde.

Funcional: `Naty.exe` WPF self-contained inicia `Core/Naty.Core.exe` silenciosamente; single-instance sinaliza a janela existente; shutdown encerra a árvore; build gera ZIP e `NatySetup.exe`; atalhos/startup opcionais; desinstalação preserva dados pessoais e modelos.

Não validado: instalação/desinstalação humana via wizard, segunda execução trazendo janela após instalação, testes dos botões Settings/voz, OneDrive entre dois PCs, hotkey após reinicialização e OAuth Google.

Próximo: Blocos 9 e 10 — diagnóstico interno, aceite guiado e benchmark final da árvore de processos.

---

# STATUS ATUAL DA NATY

> Auditoria de continuidade realizada em 04/09/2026, no workspace `C:\Users\yster\Desktop\NATY`.
>
> Este documento separa rigorosamente **estado atual verificável** de **última validação histórica registrada**. Nenhuma funcionalidade foi implementada, refatorada ou alterada durante esta auditoria.

## CHECKPOINT ATUAL — ARQUITETURA HÍBRIDA (substitui o estado operacional da auditoria abaixo)

- Branch atual: `feat/naty-v3-hybrid`.
- BLOCO A: **CONCLUÍDO** — `.venv` restaurada; baseline Python verde.
- BLOCO B: **CONCLUÍDO** — Desktop C#/.NET/WPF, protocolo JSON v1 e Windows Named Pipes funcionando.
- BLOCO C: **PARCIAL** — pipeline de captura e provider whisper.cpp implementados; A/B real ainda bloqueado pela ausência de binário/modelos auditados e teste falado do usuário.
- Blocos D–H: **PENDENTES**; não iniciados porque o BLOCO C ainda não cumpre o critério de aceite real.
- SDK local: .NET 8.0.424 em `.dotnet`; ambiente Python em `.venv` com dependências base/voz.
- Configuração local restaurada com Obsidian real e microfone funcional atual ID 13 (Realtek WDM-KS, 44.100 Hz).
- Desktop WPF validado por build e captura real em `artifacts/naty-wpf-final.png`.
- Última suíte completa: 99 testes, 98 pass, 1 skip DPAPI esperado.
- Benchmark curto: árvore Desktop + Core = 183,83 MiB RSS e 0,0% CPU instantânea após 3 s.
- A auditoria original das seções seguintes permanece como histórico do estado anterior às correções deste checkpoint.

## CHECKPOINT — CICLO FUNCIONAL

BLOCO: respostas, Router, pesquisa e Obsidian
status: **CONCLUÍDO**
feito: fallback genérico removido; classificação funcional; ToolResult estruturado; pesquisa real com fontes; retrieval FTS5/grafo com resposta sem invenção.
testes: pesquisa web real retornou 5 fontes; Obsidian real respondeu para NATY Agent e informou corretamente que não existe memória sobre TCC.

BLOCO: tarefas, planejamento, lembretes e automações
status: **CONCLUÍDO**
feito: criação/conclusão de tarefas, resumo de hoje/amanhã, lembretes com horário por extenso e automações ONE_TIME, DAILY e WEEKLY persistidas e executadas pelo scheduler.
testes: fluxos end-to-end cobertos em banco temporário, incluindo disparo único anti-repetição.

BLOCO: launcher, mídia, IPC e front
status: **CONCLUÍDO**
feito: launcher allowlist, mídia por teclas Windows, payload IPC com data/sources/ui/error, Brain Mode, ContextDrawer lazy e até 6 nós reais destacados.
testes: Named Pipe com resposta estruturada e shutdown limpo; WPF 0 erros/0 avisos; capturas artifacts/naty-functional-brain.png e artifacts/naty-functional-context.png.

Pendente: validação humana do microfone/Whisper, credenciais Google e confirmação manual em aplicativos instalados das ações Spotify/mídia.

## 1. Estado geral

- A base de código da **NATY V2.1.0** está presente e versionada em Git.
- O núcleo implementado é local-first e determinístico: tarefas, projetos, listas, lembretes, agenda local, notas, memória consentida, planejamento, pesquisa, Obsidian, voz e integrações opcionais estão representados no código.
- O checkout está na branch `main`, acompanhando `origin/main`, no commit `4fa3a97`.
- O código-fonte está íntegro como repositório, mas **o ambiente de execução não está preparado neste momento**: não existem `.venv`, `.build-venv`, Python instalado, modelo Vosk local, banco `data/naty.db`, logs, build, pacote instalável nem aplicativo instalado.
- O Vault `C:\Users\yster\Documents\Obsidian Vault` existe e a subpasta `Naty` contém atualmente 33 arquivos Markdown.
- Portanto, o estado real é: **implementação V2.1 presente no código; dados Markdown presentes; execução, testes e instalação não reproduzidos nesta auditoria por ausência do runtime Python e dos artefatos gerados**.
- As últimas execuções bem-sucedidas permanecem registradas em `STATUS_V2_1.md` e `BENCHMARK.md`, mas devem ser tratadas como evidência histórica da mesma máquina, não como uma validação do estado operacional atual.

## 2. Último bloco concluído

### BLOCO 3 — APLICATIVO WINDOWS REAL

- Estado registrado: **CONCLUÍDO (100%) na última validação histórica**.
- Commit principal: `99bd29e` — `feat: melhora voz e empacota NATY como aplicativo Windows`.
- Correção posterior: `4fa3a97` — `fix: atualiza ícone da NATY nos atalhos do Windows`.
- Entrega histórica: build PyInstaller onedir, `Naty.exe`, ZIP instalável 2.1.0, instalação por usuário, atalhos, tray, hotkey, ícones, Vosk empacotado e separação entre binários e dados mutáveis.
- Validação histórica: 86 testes executados, 85 aprovados, 1 skip DPAPI esperado; smoke do executável e do aplicativo instalado com código de saída 0.
- Limite desta conclusão: `dist/`, `installer/`, modelo Vosk, instalação e atalhos são artefatos ignorados pelo Git e **não existem mais no estado atual**. O código de build/instalação permanece, mas a entrega não foi reconstruída nesta auditoria.

## 3. Bloco atual

**Nenhum bloco em andamento.**

- O repositório estava limpo antes da criação deste relatório e não há implementação parcial não commitada.
- O BLOCO 2 (voz real) continua **adiado e não aprovado por teste humano final**, mas não está ativo. Em 04/09/2026 o usuário autorizou seguir para o BLOCO 3 antes de concluir o ajuste fino da voz.
- O BLOCO 4 está apenas marcado como pendente; nenhum experimento de framework visual foi iniciado no código atual.

## 4. Próximo bloco recomendado

### Gate de restauração e, depois, BLOCO 4 — NOVA EXPERIÊNCIA VISUAL

Antes de iniciar uma nova implementação, o próximo desenvolvedor deve restaurar uma baseline reproduzível:

1. instalar Python 3.11+ para Windows com Tcl/Tk;
2. recriar `.venv` e instalar dependências;
3. executar a suíte completa e os smokes possíveis;
4. criar uma nova `config.toml` sem assumir que a configuração histórica ainda existe;
5. confirmar que as 33 notas do Vault continuam preservadas e confinadas a `Obsidian Vault\Naty`;
6. somente se for necessário distribuir novamente, baixar o modelo Vosk com consentimento, reconstruir o pacote e reinstalar.

Com a baseline validada, iniciar o **BLOCO 4** medindo a UI Tkinter atual contra CustomTkinter e PySide6 antes de escolher tecnologia. Não migrar a interface por preferência estética sem medir startup, RAM, CPU em idle, tamanho do pacote, acessibilidade e custo de manutenção.

## 5. Arquitetura REAL atual

### Core

- `NatyAssistant` compõe configuração, logging rotativo, SQLite, repositórios, tools, conectores, pesquisa, knowledge graph, retrieval, conversa, skills e roteadores.
- O fluxo principal é: texto ou push-to-talk → `IntentRouter` baseado em regras → `AgentRouter` → skill/tool determinística ou `ConversationEngine` → `ResponseFormatter` → UI/TTS.
- `SessionContext` mantém contexto curto da conversa e a entidade corrente; o histórico curto não é uma memória semântica autônoma.
- `EventBus` publica estados funcionais da aplicação. Não há exposição de cadeia de raciocínio.
- Falhas de módulos opcionais são isoladas e não devem impedir o uso das tarefas locais.

### Interface

- A interface real é Python com **Tkinter/ttk**, não Electron, web, C# ou WPF.
- `MainWindow` implementa dashboard escuro em três colunas, conversa, tarefas, contexto, módulos e métricas.
- `KnowledgeGraphCanvas` desenha o grafo em Canvas; `MiniWindow` é o HUD always-on-top acionado pela hotkey.
- Há onboarding, janela de configurações, diagnóstico de voz, tray via `pystray` e hotkey global.
- O grafo pausa/limita animação quando não está visível para preservar recursos.

### Voz

- `VoiceSessionManager` coordena escuta, resposta falada e follow-up na mesma sessão/contexto.
- O STT e o TTS são carregados fora do caminho obrigatório do core; a voz pode ser desativada.
- A hotkey padrão é `CTRL+ALT+SPACE`; wake word permanece desativado.

### STT

- Implementação: **Vosk local** por `voice/vosk_stt.py` com captura `sounddevice` PCM16 mono.
- Sample rate preferencial: 16 kHz; se o driver rejeitar, tenta o sample rate nativo do dispositivo.
- Blocos de áudio: aproximadamente 100 ms.
- Há ganho automático local limitado, com noise floor; ganho máximo padrão 12×.
- Não existe um modelo VAD dedicado. A detecção usa nível RMS após ganho (`>= 0.012`), resultados parciais do Vosk e encerra após 1,2 s sem atividade depois de fala detectada.
- O modelo permanece em memória durante os follow-ups e pode ser descarregado ao fim da sessão.

### TTS

- Provider padrão: **Windows SAPI/COM**.
- O código enumera vozes e prioriza voz feminina pt-BR; se `voice` estiver vazio, a seleção preferencial atual é Microsoft Maria.
- Piper existe apenas como provider opcional/scaffold e não faz parte da instalação base.

### Obsidian

- O Vault é cérebro externo legível; SQLite continua sendo a fonte operacional.
- A raiz do Vault e a pasta gerenciada são configurações distintas.
- Leitura, indexação e escrita são confinadas à subpasta exata `Naty/`; um caminho gerenciado diferente de `<Vault>\Naty` é rejeitado.
- O índice é incremental por `mtime`/hash, usa SQLite FTS5 e extrai título, tags, frontmatter e wikilinks.
- Escritas geradas usam frontmatter, bloco `<!-- NATY:BEGIN -->`/`<!-- NATY:END -->` e substituição atômica, preservando texto pessoal fora do bloco.
- O retrieval limita quantidade de notas e caracteres e insere o conteúdo como dado local não confiável, não como instrução.

### SQLite

- Implementação via `sqlite3` da biblioteca padrão, com WAL, foreign keys, migrations, repositórios e FTS5.
- Entidades: projetos, tarefas, lembretes, compromissos, listas/itens, notas, memórias, preferências, histórico, pesquisas, automações, documentos Obsidian, nós/arestas e contas de conectores.
- Estado atual: `data/naty.db` não existe. Será criado/migrado no primeiro startup bem-sucedido.

### Skills

- `SkillRegistry` é fechado e mapeia intents permitidas para tools explícitas.
- Não há shell arbitrário, execução dinâmica de plugins ou download automático de skills.
- Skills atuais cobrem tarefas, listas, lembretes, projetos, notas, agenda, planejamento, pesquisa, conversa e Google Workspace opcional.

### Router

- `IntentRouter`/`RuleParser` tentam primeiro intents determinísticas.
- `AgentRouter` envia intents conhecidas ao registro de skills; pedidos desconhecidos e confirmações contextuais seguem para `ConversationEngine`.
- A conversa usa retrieval local e só usa LLM quando a IA local está explicitamente habilitada e disponível.

### Pesquisa

- Provider padrão implementado: DDGS.
- A sessão preserva consulta, resultados, fontes, claims, comparação e horário de observação.
- Leitura de páginas é limitada por timeout e tamanho; comparações leem no máximo três páginas.
- Perplexity é opcional e só entra quando habilitada e com chave em variável de ambiente.
- O fallback de navegador apenas constrói/abre uma URL após ação explícita.

### Conectores

- Registro lazy para Gmail e Google Calendar.
- OAuth Desktop App é opcional; token é protegido com DPAPI do usuário do Windows e não deve ir para TOML/log.
- Pesquisa/leitura e criação de rascunho são separadas do envio; envio e ações destrutivas exigem confirmação.
- Estado atual: sem configuração, credenciais ou token Google verificáveis.

### Sincronização

- Implementado: sincronização local e dirigida de listas/notas do SQLite para Markdown dentro de `Naty/`, além de indexação Markdown → FTS/grafo.
- Não implementado: sincronização genérica bidirecional de todas as entidades, nuvem, desktop ↔ notebook, resolução de conflitos ou end-to-end encryption.
- Não existe serviço de sync em background independente.

### IA

- O core não depende de LLM.
- `LlamaCppProvider` opcional suporta modelo GGUF local, CPU, carregamento lazy, limites de arquivo/RAM e unload por inatividade.
- Recomendação documentada: Qwen3 0.6B Q4_K_M, mas nenhum modelo local existe agora.
- `NoAIProvider` mantém o fallback determinístico quando IA está desligada ou indisponível.

### Comunicação externa

- Possíveis acessos externos, todos opcionais: DDGS/páginas web, Perplexity e APIs Google OAuth.
- Não há integração implementada com ChatGPT, Codex, WhatsApp, Telegram, e-mail SMTP genérico, socket local, Named Pipes ou serviço remoto próprio.
- A NATY não delega tarefas a outro agente no estado atual.

## 6. Arquivos importantes

| Arquivo/pasta | Papel atual |
|---|---|
| `main.py` | Entry point GUI/CLI; flags `--cli`, `--command`, `--no-tray` e smoke interno. |
| `config.py` | Defaults, persistência TOML, paths de recursos e dados do app empacotado. |
| `config.example.toml` | Referência completa de configuração sem segredos. |
| `core/assistant.py` | Composition root da aplicação. |
| `core/agent_router.py` / `core/intent_router.py` | Roteamento em camadas. |
| `conversation/engine.py` | Conversa contextual, memória consentida e fallback de IA. |
| `database/migrations.py` | Schema SQLite/FTS5. |
| `knowledge/obsidian_index.py` | Indexação incremental do Vault. |
| `knowledge/retriever.py` | Recuperação limitada de contexto Markdown. |
| `knowledge/graph.py` | Grafo observável de conhecimento. |
| `tools/obsidian.py` | Escrita confinada e atômica no Vault. |
| `skills/registry.py` | Registro fechado de capacidades e permissões. |
| `research/` | DDGS, Perplexity opcional, leitura, comparação e auditoria. |
| `connectors/google/` | OAuth, Gmail e Calendar opcionais. |
| `voice/vosk_stt.py` | STT local, captura, threshold e unload. |
| `voice/audio_processing.py` | Ganho automático PCM16 local. |
| `voice/sapi_tts.py` | TTS SAPI e seleção de voz. |
| `voice/manager.py` | Sessão de voz e follow-up. |
| `ui/main_window.py` | Dashboard principal. |
| `ui/mini_window.py` | HUD da hotkey. |
| `ui/voice_settings.py` | Diagnóstico e configuração de voz. |
| `naty.spec` | Empacotamento PyInstaller e inclusão opcional do modelo Vosk. |
| `scripts/build_windows.py` | Build, pacote ZIP e chamada opcional ao Inno Setup. |
| `packaging/` | Instalador/desinstalador por usuário e metadados 2.1.0. |
| `tests/` | 16 módulos com 86 métodos de teste atuais. |
| `BENCHMARK.md` | Última medição detalhada registrada. |
| `STATUS_V2_1.md` | Histórico dos blocos 0–3 e pendências 4–10. |
| `README.md` / `ARCHITECTURE.md` / `ROADMAP.md` | Uso, arquitetura e visão de evolução; contêm pontos históricos divergentes listados abaixo. |

## 7. Tecnologias e dependências

### INSTALADO / verificável agora

- Windows 11 e PowerShell.
- Git, com repositório e remote GitHub acessíveis localmente.
- Python Launcher `C:\Windows\py.exe`, **sem qualquer interpretador Python registrado** (`py -0p` retorna `No installed Pythons found!`).
- Windows SAPI com duas vozes: Microsoft Zira Desktop (`en-US`, feminina) e Microsoft Maria Desktop (`pt-BR`, feminina).
- Vault Markdown em `C:\Users\yster\Documents\Obsidian Vault\Naty` com 33 notas.

### IMPLEMENTADO no código

- Python 3.11+; última build histórica usou Python 3.12.7/Tk 8.6.13.
- Tkinter/ttk, `sqlite3`, FTS5, TOML via `tomllib`, logging rotativo e threading.
- DDGS `>=9.5,<10`, Pillow `>=11,<13`, psutil `>=7,<8`, pystray `>=0.19,<1`.
- PyInstaller `>=6,<7` para build.
- Empacotamento Windows por usuário com PowerShell e script opcional Inno Setup.

### OPCIONAL e não instalado/verificado agora

- Voz: sounddevice `>=0.5,<1`, Vosk `>=0.3.45,<1` e `vosk-model-small-pt-0.3`.
- IA local: llama-cpp-python `>=0.3.16,<0.4` e modelo GGUF escolhido pelo usuário.
- Google: google-api-python-client, google-auth e google-auth-oauthlib.
- Perplexity por API key em `NATY_PERPLEXITY_API_KEY`.
- Piper TTS externo/modelo, sem integração de setup na instalação base.
- Inno Setup 6 para gerar Setup `.exe`; o `.iss` existe, mas não há build atual.

### PLANEJADO / NÃO IMPLEMENTADO

- Avaliação e possível migração visual para CustomTkinter ou PySide6.
- Orquestração/delegação para ChatGPT, launcher inteligente, autoevolução controlada e sync multi-dispositivo.
- Wake word “Naty”, app Android, memória semântica vetorial, assinatura digital, SBOM, update/rollback.
- C#/WPF, Named Pipes e divisão em processos/serviços não foram adotados nem implementados.

## 8. Testes

### Inventário atual

- 16 arquivos `tests/test_*.py`.
- 86 métodos `test_*` descobríveis no código atual.
- O teste DPAPI é dependente do perfil Windows e pode ser pulado quando a proteção não está disponível.

### Último resultado histórico registrado

- Suíte completa após o BLOCO 3: **86 executados; 85 aprovados; 0 falhas; 1 skip DPAPI esperado; resultado geral OK**.
- `compileall`: aprovado.
- Build PyInstaller 6.22.2: aprovado.
- Smoke `dist/Naty/Naty.exe --no-tray --smoke-gui`: exit code 0.
- Smoke do executável instalado: exit code 0.
- Smoke com tray/hotkey: exit code 0.
- Metadados: ProductVersion 2.1.0.

### Estado desta auditoria

- **Não executados agora.** Motivo objetivo: `.venv` e `.build-venv` não existem e o launcher `py` não encontra Python instalado.
- Assim, o número 85+1 é a última evidência histórica, não uma garantia de que a máquina atual executa a suíte sem reinstalar dependências.

### Comandos de reprodução

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
.\.venv\Scripts\python.exe -m compileall .
.\.venv\Scripts\python.exe -m scripts.smoke_gui
.\.venv\Scripts\python.exe -m scripts.smoke_obsidian_real
.\.venv\Scripts\python.exe -m scripts.smoke_voice --listen --speak
```

### Dependências manuais/externas

- GUI/tray/hotkey: sessão desktop interativa e Tcl/Tk.
- Voz: dependências de voz, modelo Vosk, microfone permitido pelo Windows e fala humana.
- Google: credencial OAuth, consentimento do usuário e rede.
- Pesquisa DDGS/Perplexity: rede; Perplexity também requer chave.
- IA local: llama-cpp-python, GGUF e memória suficiente.

## 9. Benchmarks

Valores abaixo são os **últimos números registrados**, medidos em 04/09/2026. Não foram repetidos nesta auditoria.

### Core/UI (`BENCHMARK.md`)

| Medida | Valor registrado |
|---|---:|
| Startup do core | 348,45 ms |
| RAM RSS média em idle, sem GUI | 41,77 MiB |
| CPU média em idle | 0,0% |
| Comando local simples | 39,61 ms |
| RSS após comando | 41,85 MiB |
| Pesquisa local determinística, 5 resultados | 48,87 ms |
| RSS durante pesquisa local | 41,88 MiB |
| 100 inserções SQLite | 1.882,1 ms |
| Sincronização Obsidian, 3 itens | 86,11 ms |
| Índice incremental, 50 documentos | 467,28 ms |
| Retrieval FTS, 6 resultados | 44,97 ms |
| Grafo, 51 nós/100 arestas | 19,81 ms |
| Inicialização SAPI sem fala | 1,9 ms |
| Startup GUI + tray + hotkey | 842,66 ms |
| UI visível | 66,76 MiB / 0,0% CPU |
| Grafo ativo | 66,76 MiB / 0,0% CPU |
| Minimizada | 66,77 MiB / 0,0% CPU |
| Carga do modelo Vosk | 423,52 ms; +87,74 MiB RSS |

### Obsidian real, histórico do BLOCO 1

- Indexação/validação completa de 33 notas: 845,58 ms.
- Reconstrução do grafo: 28,33 ms.
- Três retrievals reais: 27,01 ms, 28,01 ms e 27,20 ms.
- Resultado histórico do grafo: 35 nós e 88 relações.

### Voz real, histórico do BLOCO 2

- Captura técnica Vosk de 3 s com carga e unload: 3,94 s.
- Último bloco do smoke de ganho: entrada 0,063%; saída 0,5793%; ganho 9,2×.

### Empacotamento, histórico do BLOCO 3

- ZIP instalável: 77,41 MiB.
- SHA-256 histórico: `B72ACDC7B24725E9AD4A4F09FDCA8E66A4BDE5240A1191F782EFA5D15B794139`.
- Modelo Vosk incluído: 14 arquivos, 51,07 MiB.

### NÃO MEDIDO

- Latência STT com uma amostra de fala controlada e transcrição correta: **NÃO MEDIDO**.
- Taxa de acerto da NATY para a voz normal do usuário após ganho automático: **NÃO MEDIDO**.
- LLM local/Qwen no hardware-alvo: **NÃO MEDIDO**.
- Google real autorizado: **NÃO MEDIDO**.
- Rede DDGS real no benchmark principal: **NÃO MEDIDO**.
- CustomTkinter, PySide6, C#/WPF e Named Pipes: **NÃO MEDIDO / NÃO IMPLEMENTADO**.

## 10. Voz — estado detalhado

### Estado operacional atual

- Código de voz: presente.
- SAPI no Windows: presente; Maria pt-BR e Zira en-US foram enumeradas nesta auditoria.
- `.venv`, `sounddevice`, `vosk` e modelo Vosk no projeto: ausentes/não verificáveis.
- `config.toml`: ausente; portanto **não há microfone nem voz persistidos atualmente**.
- Com os defaults do código, `microphone_device = -1` usa o dispositivo padrão do sistema, `voice = ""` escolhe Maria preferencialmente, ganho automático fica ativo e o máximo é 12×.

### Última configuração/validação histórica

- Microfone que abriu corretamente: `Microfone (Fuxi-H3)` por WDM-KS, device ID 14.
- Entradas MME/DirectSound do Fuxi-H3 falharam naquele teste.
- Sample rate: 16 kHz, com fallback para a taxa nativa do driver.
- Voz TTS escolhida: Microsoft Maria Desktop, pt-BR, feminina.
- Fluxo: hotkey → até 8 s para primeira fala → resposta SAPI → janela de follow-up de 8 s → timeout encerra e descarrega o STT.
- O primeiro teste humano funcionou apenas com voz muito alta e produziu transcrição ruim.
- Depois disso foi adicionado ganho automático; o smoke técnico capturou/amplificou áudio, porém **não houve nova aprovação humana falando em volume normal**.

### Variantes e decisões

- Provider STT base: Vosk small pt-BR por ser local e leve.
- O modelo Vosk pt-BR maior, historicamente documentado com 1,6 GB/GPLv3, não foi baixado automaticamente por custo de recursos/licença.
- Piper não faz parte do pacote base; SAPI é o TTS padrão gratuito do Windows.
- Wake word não existe; escuta contínua não deve ser simulada sem modelo confiável e decisão explícita de privacidade.

### Próxima validação obrigatória de voz

1. recriar ambiente e instalar `requirements-voice.txt`;
2. baixar o modelo pelo `setup_voice.bat` somente após consentimento;
3. abrir **Configurações > Voz > Diagnóstico** e confirmar o ID real atual do microfone;
4. falar em volume normal no teste de microfone;
5. testar `Ctrl+Alt+Espaço`, uma pergunta e ao menos um follow-up sem nova hotkey;
6. registrar transcrição, latência, níveis, ganho e percepção humana antes de concluir o BLOCO 2.

## 11. Interface — estado detalhado

- Framework atual: Tkinter/ttk.
- Visual: tema escuro, cabeçalho, três colunas, área de conversa/comando, cards laterais, grafo Canvas e indicador de estado.
- HUD: janela compacta always-on-top, aberta pela hotkey global.
- Tray: menu com abrir, ouvir, nova tarefa, lista de compras, configurações e sair.
- Onboarding: nome, idioma, Vault, opt-in de preparação da pasta Naty, voz, proatividade, IA local e Google.
- Configurações: hotkey, Vault, notificações, proatividade, IA, inicialização com Windows e acesso ao diagnóstico de voz.
- Diagnóstico de voz: lista microfones, sample rate/API, waveform/nível, estado Vosk, transcrição e latência.
- Estado de validação atual: o código existe, mas a UI não foi aberta nesta auditoria por ausência de Python/Tcl/Tk e por não haver `Naty.exe` instalado.
- BLOCO 4 permanece pendente; CustomTkinter e PySide6 não foram adicionados às dependências nem prototipados.

## 12. Obsidian — estado detalhado

- Vault esperado e encontrado: `C:\Users\yster\Documents\Obsidian Vault`.
- Subpasta gerenciada esperada e encontrada: `C:\Users\yster\Documents\Obsidian Vault\Naty`.
- Contagem atual: 33 arquivos Markdown dentro de `Naty/`; 34 no Vault inteiro, incluindo o arquivo de boas-vindas fora de `Naty/`.
- Pastas atuais: `00 - Sistema`, `01 - Eu`, `02 - Dashboard`, `03 - Projetos`, `04 - Listas`, `05 - Memórias`, `06 - Pesquisas`, `07 - Skills` e `99 - Templates`.
- Não existem atualmente as pastas `07 - Diário` e `08 - Notas` mostradas no exemplo do `README.md`; o Vault real usa `07 - Skills`.
- A configuração histórica apontava para os caminhos acima, mas `config.toml` não existe agora; logo, o próximo startup usará Obsidian desabilitado até nova configuração/onboarding.
- O banco local atual também não existe, portanto as 33 notas estão no filesystem, mas **não há índice FTS/grafo SQLite atual para consultar**.
- Última validação histórica: 33 documentos válidos, 55 wikilinks, 1 projeto, 8 skills, 1 memória, 0 Markdown inválido, 0 documento fora de `Naty/`, grafo com 35 nós/88 relações e 3/3 retrievals aprovados.
- Regra de segurança que deve permanecer: nunca indexar/escrever fora de `<Vault>\Naty`; nunca apagar ou sobrescrever conteúdo pessoal fora do bloco gerenciado.

## 13. Configuração importante

### Arquivo real atual

- `C:\Users\yster\Desktop\NATY\config.toml`: **não existe**.
- `%LOCALAPPDATA%\NATY\config.toml`: **não existe**.
- Não há configuração pessoal ou segredo no repositório.

### Defaults efetivos definidos no código

| Chave | Valor padrão |
|---|---|
| `first_run_completed` | `false` |
| `language` | `pt-BR` |
| `hotkey` | `CTRL+ALT+SPACE` |
| `voice_enabled` / `tts_enabled` | `true` / `true` |
| `wake_word_enabled` | `false` |
| `tts_provider` / `stt_provider` | `sapi` / `vosk` |
| `vosk_model_path` | vazio; autodetecta modelo empacotado se existir |
| `microphone_device` | `-1` (padrão do sistema) |
| `microphone_gain` / `automatic_gain_enabled` | `12.0` / `true` |
| `voice` / `voice_rate` / `voice_volume` | vazio / `0` / `100` |
| `conversation_followup_seconds` | `8` (limitado pelo manager a 5–15) |
| `unload_stt_after_use` | `true` |
| `ai_enabled` | `false` |
| `ai_threads` / `ai_context_size` | `4` / `2048` |
| `ai_max_ram_mb` / `ai_min_available_ram_mb` | `1800` / `2200` |
| `ai_idle_unload_seconds` | `120` |
| `obsidian_enabled` | `false` |
| `obsidian_vault_path` / `naty_obsidian_path` | vazios |
| `obsidian_max_notes` / `obsidian_max_chars` | `6` / `8000` |
| `research_enabled` | `true` |
| `max_search_results` / `research_timeout_seconds` | `5` / `10` |
| `max_response_size` / `max_cpu_threads` | `1.000.000` / `4` |
| `start_with_windows` | `false` |
| `notifications_enabled` | `true` |
| `proactivity_enabled` | `false` |
| `morning_briefing` / `evening_review` | `false` / `false` |
| `overdue_followup` | `true` |
| `morning_briefing_time` / `evening_review_time` | `08:00` / `19:00` |
| `google_enabled` / `perplexity_enabled` | `false` / `false` |
| `privacy_mode` / `performance_monitor_enabled` | `true` / `true` |
| `scheduler_interval_seconds` / `daily_summary_time` | `30` / `08:00` |
| `data_dir` / `log_dir` | `data` / `logs` |

- Não existe chave de “modo aprendizado”; esse recurso não está implementado.
- Segredos Google/Perplexity não foram encontrados nem expostos nesta auditoria.

## 14. Limitações e bugs conhecidos

- Não há Python instalado, venv, dependências ou executável: a NATY não pode ser iniciada no estado atual sem restauração do ambiente ou reinstalação do pacote.
- Não há banco SQLite atual; tarefas, listas, memórias e índices históricos locais não estão disponíveis neste checkout.
- Não há modelo Vosk atual; STT está indisponível mesmo que o código seja iniciado com dependências básicas.
- A voz ainda precisa de teste humano final após o ganho automático; precisão do modelo pequeno é uma limitação conhecida.
- O device ID 14 é histórico e não deve ser reutilizado cegamente: IDs do PortAudio podem mudar após reboot/driver/dispositivo.
- O executável não é assinado digitalmente; um pacote futuro pode acionar SmartScreen.
- Não há Setup `.exe` atual; Inno Setup não estava instalado na última build. Somente os scripts permanecem.
- O ZIP, a instalação e os atalhos descritos no README/status histórico estão ausentes atualmente.
- Google não foi autorizado em conta real; o teste DPAPI depende do perfil Windows.
- LLM local não foi medido no hardware-alvo e não deve ser ativado por padrão.
- Pesquisa web depende da rede e das fontes; resultados não são garantidos.
- Não há sync multi-dispositivo, resolução de conflitos, wake word ou app móvel.
- `README.md` descreve uma estrutura Obsidian com `07 - Diário`/`08 - Notas`, enquanto o Vault real contém `07 - Skills` e não contém essas duas pastas.
- `ROADMAP.md` ainda cita empacotamento como próximo passo genérico, embora o BLOCO 3 tenha sido implementado historicamente.

## 15. Decisões que não devem ser rediscutidas sem nova evidência

- A NATY é **local-first** e deve funcionar sem LLM e sem nuvem.
- O núcleo determinístico, SQLite e regras têm prioridade sobre modelos pesados.
- Hardware modesto, baixa RAM/CPU em idle e startup rápido são requisitos de produto.
- Componentes pesados devem ser opcionais, lazy e descarregáveis.
- Nenhum modelo, conta, custo, startup automático ou escrita no Vault é habilitado sem escolha explícita.
- SQLite é a fonte operacional; Obsidian é cérebro externo legível e superfície de conhecimento.
- Toda gestão de Markdown fica confinada a `<Vault>\Naty` e preserva conteúdo pessoal fora dos blocos gerenciados.
- Memórias pessoais só são persistidas após linguagem explícita como “lembre que”.
- Envio de e-mail, exclusões e ações remotas destrutivas exigem confirmação em segundo turno.
- Não incluir shell arbitrário em skills.
- Não ativar wake word improvisado nem escuta contínua sem modelo confiável e revisão de privacidade.
- Não baixar automaticamente o Vosk maior, Qwen, Piper ou qualquer dependência/modelo opcional.
- SAPI continua o TTS base gratuito; Vosk small continua a baseline STT até teste comparativo real justificar mudança.
- Não escolher framework visual antes de medir Tkinter, CustomTkinter e PySide6 no hardware-alvo.

## 16. Itens discutidos, mas NÃO implementados

- **PLANEJADO / NÃO IMPLEMENTADO — BLOCO 4:** nova experiência visual; comparação Tkinter/CustomTkinter/PySide6.
- **PLANEJADO / NÃO IMPLEMENTADO — BLOCO 5:** NATY como orquestradora de agentes/processos.
- **PLANEJADO / NÃO IMPLEMENTADO — BLOCO 6:** delegação para ChatGPT.
- **PLANEJADO / NÃO IMPLEMENTADO — BLOCO 7:** launcher inteligente.
- **PLANEJADO / NÃO IMPLEMENTADO — BLOCO 8:** autoevolução controlada.
- **PLANEJADO / NÃO IMPLEMENTADO — BLOCO 9:** sincronização desktop/notebook.
- **PLANEJADO / NÃO IMPLEMENTADO — BLOCO 10:** teste completo ponta a ponta de todas as integrações.
- **PLANEJADO / NÃO IMPLEMENTADO:** wake word treinado para “Naty”.
- **PLANEJADO / NÃO IMPLEMENTADO:** Android, sync ponta a ponta e resolução de conflitos multi-dispositivo.
- **PLANEJADO / NÃO IMPLEMENTADO:** memória semântica/vetorial.
- **PLANEJADO / NÃO IMPLEMENTADO:** assinatura de código, SBOM, scan de segurança, atualização e rollback.
- **NÃO IMPLEMENTADO:** C#/WPF, processo UI separado, serviço Windows e comunicação por Named Pipes.
- **NÃO IMPLEMENTADO:** modo aprendizado/autotreino/autonomia para editar o próprio código.
- **OPCIONAL NÃO INSTALADO:** Piper TTS.
- **IMPLEMENTAÇÃO DE BUILD PRESENTE, ARTEFATO AUSENTE:** Setup Inno e ZIP instalável.

## 17. Como executar

### Pré-requisito atual

Instalar Python 3.11 ou mais recente para Windows, incluindo Tcl/Tk. O launcher `py` existe, mas não há interpretador registrado.

### Ambiente básico e GUI

```powershell
cd C:\Users\yster\Desktop\NATY
.\setup_naty.bat
.\run_naty.bat
```

Equivalente manual:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

### CLI

```powershell
.\.venv\Scripts\python.exe main.py --cli
.\.venv\Scripts\python.exe main.py --command "lista minhas tarefas"
```

### Voz opcional

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-voice.txt
.\setup_voice.bat
.\.venv\Scripts\python.exe -m scripts.smoke_voice --listen --speak
```

### Testes

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

### Build Windows

```powershell
py -3.12 -m venv .build-venv
.\.build-venv\Scripts\python.exe -m pip install -r requirements-dev.txt -r requirements-voice.txt
.\.build-venv\Scripts\python.exe -m scripts.build_windows
```

- Saída esperada: `dist\Naty\Naty.exe` e `installer\Naty-Windows-2.1.0.zip`.
- O aplicativo instalado normalmente ficaria em `%LOCALAPPDATA%\Programs\NATY`, mas esse caminho não existe agora.

## HANDOFF PARA O PRÓXIMO DESENVOLVEDOR

1. **Qual foi o último bloco concluído?** BLOCO 3, aplicativo Windows real, concluído historicamente e fechado nos commits `99bd29e`/`4fa3a97`; artefatos gerados não estão mais presentes.
2. **Existe trabalho em andamento?** Não. Nenhum bloco em andamento. O BLOCO 2 está adiado aguardando validação humana; o BLOCO 4 ainda não começou.
3. **Qual é o próximo bloco?** Restaurar e validar a baseline; depois iniciar o BLOCO 4 com benchmark comparativo de UI.
4. **O que existe de fato agora?** Código V2.1 versionado, scripts, testes, documentação, assets e 33 notas no Vault `Naty/`.
5. **O que não existe agora?** Python, venvs, dependências verificadas, `config.toml`, banco, logs, modelo Vosk, build, ZIP, instalação e atalhos.
6. **O que não deve ser rediscutido?** Local-first, core sem LLM, SQLite operacional, Obsidian confinado, consentimento explícito, confirmação de ações de risco e componentes pesados opcionais/lazy.
7. **Quais são as dependências críticas?** Python 3.11+ com Tcl/Tk para qualquer execução; requirements base; dependências/modelo Vosk apenas para voz; credenciais/modelos externos somente por opt-in.
8. **Qual é a evidência de qualidade disponível?** 86 testes no código; último resultado histórico 85 pass + 1 skip; benchmarks exatos neste documento; nenhum deles foi rerodado agora.
9. **Qual validação do usuário está pendente?** Falar em volume normal após ganho automático, validar transcrição, resposta SAPI e follow-up sem nova hotkey.
10. **Qual deve ser a primeira ação segura?** Ler este arquivo e `STATUS_V2_1.md`, conferir `git status`, instalar runtime, rodar testes em ambiente limpo, criar configuração nova sem segredo e preservar integralmente o Vault antes de tocar no BLOCO 4.

## 19. Git

- Repositório Git: **sim**.
- Branch atual: `main`.
- Upstream: `origin/main`.
- Remote: `https://github.com/BrunnoRa/NATY.git`.
- Commit atual: `4fa3a976648303fab023ff843e56637cafd41a05` — `fix: atualiza ícone da NATY nos atalhos do Windows` — 04/09/2026 15:55:50 -03:00.
- Commits anteriores visíveis:
  - `99bd29e` — `feat: melhora voz e empacota NATY como aplicativo Windows`;
  - `b070f19` — `feat: initial NATY V2.1 with Obsidian integration`.
- Estado antes desta auditoria: working tree limpo, sem modificações ou arquivos não rastreados.
- Estado após a entrega solicitada: somente `STATUS_NATY.md` foi criado e ficará não rastreado até ser adicionado/commitado pelo usuário.
- Nenhum commit, push, pull, branch, tag ou alteração de histórico foi realizado nesta auditoria.

---

## Divergências confirmadas entre documentação histórica e estado atual

- `README.md` e `STATUS_V2_1.md` descrevem aplicativo instalado, atalhos e ZIP; todos estão ausentes agora.
- `STATUS_V2_1.md` descreve `.venv`, config, banco e modelo usados nos blocos anteriores; esses itens estão ausentes agora.
- O Vault e suas 33 notas estão presentes, mas não há `config.toml` nem banco/índice atual conectando a aplicação a eles.
- A estrutura real do Vault inclui `07 - Skills`, enquanto o exemplo do README mostra `07 - Diário` e `08 - Notas`.
- `ROADMAP.md` trata empacotamento como próximo passo genérico; o histórico mais recente mostra o BLOCO 3 concluído e o BLOCO 4 como próximo bloco de produto.
- Não há divergência de código não commitado: o checkout estava limpo antes deste relatório.

## BLOCO A

Status: **CONCLUÍDO**

Implementado: restauração da `.venv`, dependências base/voz, SDK .NET local, baseline reproduzível e relatório de correções.

Arquivos: `.gitignore`, `NuGet.Config`, `FIX_REPORT.md` e ambientes locais ignorados.

Testes: baseline histórica repetida; 86 executados, 85 aprovados, 1 skip DPAPI; `compileall` aprovado.

Limitações: o Python da venv deriva do runtime local disponibilizado pelo ambiente Codex; distribuição final ainda precisa ser autocontida.

Próximo: BLOCO B.

## BLOCO B

Status: **CONCLUÍDO**

Implementado: `core_host.py`, IPC JSON v1, Windows Named Pipe `Naty.Core.v1`, timeout/reconexão, dashboard real, shutdown limpo, Desktop WPF, HUD, hotkey, tray, métricas e KnowledgeGraph real.

Arquivos: `ipc/`, `core_host.py`, `desktop/Naty.Desktop/`, `scripts/smoke_ipc.py`, `tests/test_ipc.py`, `ARCHITECTURE.md` e `README.md`.

Testes: 6/6 IPC; smoke real ping/dashboard/shutdown; build WPF 0 warnings/0 errors; captura visual aprovada.

Limitações: instalador híbrido/autocontido ainda não foi produzido; os comandos de mídia e a voz não estão ligados ao HUD.

Próximo: BLOCO C.

## BLOCO C

Status: **PARCIAL**

Implementado: pipeline mono PCM16 com sample rate nativo, ganho, pre-roll 300 ms, VAD energético, silêncio final 1.100 ms, máximo 20 s, métricas RMS/peak/clipping, whisper.cpp pt configurável, Vosk fallback e `scripts/stt_ab_test.py`.

Arquivos: `voice/capture_pipeline.py`, `voice/whisper_cpp.py`, `voice/vosk_stt.py`, `voice/devices.py`, `voice/manager.py`, `scripts/stt_ab_test.py`, `scripts/process_tree_memory.py`, `scripts/smoke_voice.py`, configurações e testes.

Testes: 6 testes de IPC, 5 de pipeline/availability e 2 de WER; diagnóstico real capturou no microfone ID 13.

Limitações: nenhum binário/modelo Whisper foi baixado; WER/latência/RAM de Base e Small permanecem não medidos; fala natural e playback da gravação ainda não foram validados; por isso o bloco não está concluído.

Próximo: obter binário oficial whisper.cpp e modelos multilíngues auditados com consentimento, executar o A/B com as dez frases e integrar o vencedor ao HUD; só então iniciar o BLOCO D.
