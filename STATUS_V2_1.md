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

## BLOCO 2 — VOZ REAL: EM ANDAMENTO — AGUARDANDO VALIDAÇÃO FALADA

### Concluído nesta etapa

- Corrigido o caminho local do modelo para `C:\Users\yster\Desktop\NATY\NATY\models\vosk\vosk-model-small-pt-0.3`.
- Diagnóstico de microfone implementado em **Configurações > Voz > Diagnóstico**:
  - lista todas as entradas e APIs do Windows;
  - identifica o dispositivo padrão;
  - mostra canais e sample rate;
  - mostra nível e waveform em tempo real;
  - informa instalação do Vosk e caminho do modelo;
  - exibe última transcrição e latência;
  - botão `TESTAR MICROFONE` com contagem regressiva de 2 segundos e captura de até 7 segundos;
  - mensagens específicas para permissão, driver/host, dispositivo, sample rate, silêncio e áudio não reconhecido.
- Seleção explícita de microfone persistida. Nesta máquina, as entradas MME/DirectSound do `Fuxi-H3` falharam, mas `Microfone (Fuxi-H3)` via WDM-KS, ID 14, abriu corretamente e ficou configurado.
- Vosk tenta 16 kHz e pode recorrer ao sample rate nativo quando o driver exigir.
- Enumeração SAPI migrada para fallback COM robusto após falha de `System.Speech` nesta máquina.
- Vozes reais encontradas:
  - Microsoft Zira Desktop — `en-US`, feminina;
  - Microsoft Maria Desktop — `pt-BR`, feminina.
- Microsoft Maria Desktop configurada e priorizada; a tela mostra instruções gratuitas do Windows quando não houver voz feminina pt-BR.
- Criada `VoiceSession` com `conversation_followup_seconds` configurável entre 5 e 15 segundos, padrão 8:
  - hotkey abre uma sessão;
  - transcrição é executada;
  - a resposta é falada;
  - a Naty volta a ouvir sem exigir nova hotkey;
  - turnos seguintes reutilizam o mesmo `SessionContext`;
  - silêncio/timeout encerra a sessão.
- Após o primeiro teste humano funcionar com volume/transcrição ruins, foi implementado processamento PCM16 local:
  - ganho automático habilitado por padrão;
  - limite configurável `microphone_gain = 12.0` (1×–20× na interface);
  - noise floor para não elevar silêncio digital indiscriminadamente;
  - blocos reduzidos para aproximadamente 100 ms;
  - nível após ganho exibido no diagnóstico;
  - modelo Vosk mantido em memória durante os follow-ups e descarregado ao encerrar a sessão.
- A limitação do reconhecedor foi confirmada na fonte oficial: o `vosk-model-small-pt-0.3` publica 68,92% de erro no CORAA e 32,60% no Common Voice. O único modelo pt maior listado tem 1,6 GB, licença GPLv3 e pode consumir recursos incompatíveis com a meta leve; ele não foi baixado automaticamente.

### Testes após ajuste de sensibilidade

- Suíte completa: 81 casos descobertos, 80 aprovados e 1 `skipped` DPAPI; resultado geral `OK`.
- Teste unitário confirma amplificação superior a 4× para sinal baixo, limite máximo de ganho e silêncio digital preservado.
- Smoke real com dispositivo 14: 19 blocos em 16 kHz; último bloco medido em 0,063% na entrada e 0,5793% após ganho de 9,2×.
- O smoke sem fala permaneceu sem transcrição, como esperado; é necessária nova validação com fala normal para aprovar a melhoria.
- `scripts/smoke_voice.py` agora fornece diagnóstico reproduzível, teste falado opcional e teste SAPI.

### Arquivos alterados

- Configuração: `config.py`, `config.example.toml` e configuração local ignorada `config.toml`.
- Voz: `voice/devices.py`, `voice/vosk_stt.py`, `voice/sapi_tts.py`, `voice/manager.py`.
- Interface: `ui/voice_settings.py`, `ui/main_window.py`.
- Setup/smoke: `scripts/setup_voice.py`, `scripts/smoke_voice.py`.
- Testes: `tests/test_voice_v2.py`.
- Documentação: `README.md`, `ARCHITECTURE.md`, `PRIVACY.md`, `STATUS_V2_1.md`.

### Testes e smoke

- Testes focados de voz: 6/6 aprovados.
- Suíte completa: 81 casos descobertos, 80 aprovados e 1 caso DPAPI `skipped`; resultado geral `OK`.
- Teste unitário de sessão: primeira pergunta, follow-up e encerramento por timeout aprovados.
- Diagnóstico real: 6 entradas enumeradas; dispositivo 14 abriu e capturou nível.
- Smoke técnico Vosk real: modelo disponível, captura a 16 kHz, 12 blocos recebidos em 3,94 s e unload confirmado.
- Smoke SAPI: enumeração COM, seleção de Maria pt-BR e execução da frase de teste concluídas sem erro de processo.

### Benchmark

- Captura técnica Vosk de 3 segundos, incluindo carregamento e unload do modelo: 3,94 s.
- O Vosk permanece lazy e foi descarregado ao terminar; não adiciona RAM permanente ao idle.
- Captura curta do diagnóstico: aproximadamente 1 segundo; pico observado em ambiente silencioso: 0,01%.

### Limitações / critério restante

- O primeiro teste humano confirmou que o fluxo funciona, mas exigia voz muito alta e produzia transcrição ruim. O ganho automático foi implementado depois desse teste e ainda precisa ser revalidado falando em volume normal.
- A precisão máxima continua limitada pelo modelo compacto pt-BR disponível no Vosk; ganho corrige sensibilidade, mas não elimina erros acústicos/linguísticos do modelo.
- O Python embutido da sessão continua sem Tcl/Tk utilizável, mas isso não afeta o aplicativo: o build passou a usar o Python 3.12 oficial com Tk 8.6.13.
- Por esses motivos, o Bloco 2 não foi marcado como concluído. Em 04/09/2026, o usuário pediu explicitamente para adiar a correção fina da voz e autorizou iniciar o Bloco 3.

### Próximo passo obrigatório

- Em uma sessão desktop com áudio, abrir **Voz > Diagnóstico**, clicar em `TESTAR MICROFONE` e falar uma frase; depois testar `Ctrl+Alt+Espaço`, fazer uma pergunta e uma continuação sem pressionar a hotkey novamente.
- Alternativa no terminal: `.\.venv\Scripts\python.exe -m scripts.smoke_voice --listen --speak`.

## BLOCO 3 — APLICATIVO WINDOWS REAL: CONCLUÍDO

### Entrega

- Gerado `Naty.exe` em modo onedir, sem dependência de `.bat`, com Python/Tk, tray, hotkey, Vosk, `sounddevice`, DDGS e o modelo pt-BR incluídos.
- Instalado para o usuário atual em `%LOCALAPPDATA%\Programs\NATY`, sem exigir administrador.
- Criados e validados atalhos no Desktop e no menu Iniciar, ambos apontando para o executável instalado.
- `Iniciar NATY junto com Windows` permanece OFF por padrão. A opção existente na interface agora registra corretamente apenas `Naty.exe` no modo empacotado, sem duplicar executável/argumento.
- Criado pacote simples `installer/Naty-Windows-2.1.0.zip`, com instalador e desinstalador por usuário. Também foi preparado `packaging/Naty.iss` para gerar um Setup tradicional quando Inno Setup estiver disponível.
- Configuração, SQLite e logs do aplicativo empacotado foram movidos para `%LOCALAPPDATA%\NATY`, separados dos binários e preservados durante atualização.
- A desinstalação remove atalhos, startup, binários e dados próprios da Naty. Ela não referencia nem remove o Vault do Obsidian.
- A configuração pessoal `config.toml` não entra no pacote. Em uma instalação nova, o modelo Vosk incluído é descoberto automaticamente.
- O segundo logo fornecido pelo usuário foi adotado como identidade oficial em `assets/naty_source.png`. Foram gerados PNGs 16/32/48/128/256 com cantos transparentes e ICO multirresolução; aplicados à janela, tray, executável e atalhos.

### Arquivos alterados/criados

- Empacotamento: `.gitignore`, `naty.spec`, `packaging/version_info.txt`, `packaging/Naty.iss`, `packaging/install_naty.ps1`, `packaging/uninstall_naty.ps1`, `packaging/Instalar Naty.cmd`.
- Build/assets: `scripts/build_windows.py`, `scripts/generate_assets.py`, `assets/naty_source.png`, `assets/naty.ico` e `assets/naty_*.png`.
- Runtime: `config.py`, `main.py`, `tools/system.py`, `ui/main_window.py`, `ui/tray.py`.
- Testes/documentação: `tests/test_packaging.py`, `README.md`, `STATUS_V2_1.md`.

### Testes e smoke

- Suíte completa: 86 testes executados, 85 aprovados e 1 skip esperado de DPAPI; nenhuma regressão.
- `compileall` de todo o código: aprovado.
- Build PyInstaller 6.22.2 com Python 3.12.7/Tk 8.6.13: aprovado.
- Primeiro smoke do executável encontrou a ausência de `vosk/libvosk.dll`; o spec foi corrigido e o pacote reconstruído.
- Smoke final de `dist/Naty/Naty.exe --no-tray --smoke-gui`: exit code 0.
- Smoke final do executável já instalado: exit code 0.
- Smoke final com tray e hotkey ativos no executável instalado: exit code 0.
- Atalhos Desktop/Menu Iniciar: existência e destino conferidos.
- Metadados do executável: ProductVersion 2.1.0.

### Benchmark/artefato

- ZIP instalável após adoção do logo oficial: 77,41 MiB; SHA-256 `C1BD0BDC691233888408245DD43F73B07DE6326275B85C97FDB7905D60E5B058`.
- Modelo Vosk incluído: 14 arquivos, 51,07 MiB.
- A interface do smoke permanece aberta por 2,5 segundos e encerra sozinha; o fluxo completo de processo retornou código 0.

### Limitações reais

- O executável não possui assinatura digital; o Windows pode mostrar SmartScreen em cópias baixadas da internet.
- Inno Setup não está instalado nesta máquina, portanto o artefato produzido nesta sessão é o ZIP instalável. O script `.iss` está pronto para um Setup `.exe` futuro.
- O reconhecimento falado continua com a limitação registrada no Bloco 2 e será retomado depois, por decisão do usuário.

### Próximo bloco

- BLOCO 4 — medir Tkinter atual, CustomTkinter e PySide6 antes de decidir o framework da nova experiência visual.

## BLOCO 4 — NOVA EXPERIÊNCIA VISUAL: PENDENTE

## BLOCO 5 — NATY COMO ORQUESTRADORA: PENDENTE

## BLOCO 6 — DELEGAÇÃO PARA CHATGPT: PENDENTE

## BLOCO 7 — LAUNCHER INTELIGENTE: PENDENTE

## BLOCO 8 — AUTOEVOLUÇÃO CONTROLADA: PENDENTE

## BLOCO 9 — SINCRONIZAÇÃO DESKTOP/NOTEBOOK: PENDENTE

## BLOCO 10 — TESTE COMPLETO: PENDENTE
