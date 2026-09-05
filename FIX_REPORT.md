# Relatório de correções da NATY

## Baseline antes das correções

Data: 04/09/2026

### Git

- Branch: `feat/naty-v3-hybrid`.
- Commit base: `4fa3a97` (`fix: atualiza ícone da NATY nos atalhos do Windows`).
- Operações incompletas: nenhuma (`merge`, `rebase`, `git am`, `cherry-pick`, `revert` e `bisect` ausentes).
- Conflitos: nenhum.
- Arquivos modificados rastreados: nenhum.
- Arquivo não rastreado preservado: `STATUS_NATY.md`, criado na auditoria anterior.

### Python

- `.venv\Scripts\python.exe`: ausente.
- `.build-venv\Scripts\python.exe`: ausente.
- `py -0p`: nenhum interpretador instalado.
- Suíte solicitada: não iniciou; PowerShell não encontrou `.\.venv\Scripts\python.exe` (exit code 1).
- `compileall`: não iniciou pelo mesmo motivo (exit code 1).
- Erros de teste/import do código: não avaliáveis até restaurar o runtime.
- Última evidência histórica, não repetida: 86 testes, 85 aprovados e 1 skip DPAPI esperado.

### .NET / WPF

- `dotnet`: comando ausente (exit code 1).
- Soluções/projetos `.sln`, `.csproj`, C# ou XAML: inexistentes na baseline.
- `dotnet build` e `dotnet test`: não aplicáveis antes da criação do Desktop e instalação do SDK.

### Aplicação e dependências locais

- Aplicação instalada, build, ZIP, banco, configuração, modelo Vosk e atalhos: ausentes.
- Vault real: presente em `C:\Users\yster\Documents\Obsidian Vault\Naty`, com 33 arquivos Markdown.
- Imagem de referência de UI aprovada: não encontrada; somente os assets oficiais NATY em `assets/`.

### Erros priorizados

1. **P0 — aplicação não inicia:** runtime Python e ambiente virtual ausentes.
2. **P1 — build C# impossível:** SDK .NET ausente e Desktop WPF ainda não implementado.
3. **P1 — Core não comunica com UI:** não existe protocolo Named Pipes nem Desktop WPF.
4. **P1 — voz não atende ao requisito:** Vosk/SAPI são a implementação principal atual; modelo e dependências também estão ausentes.
5. **P2 — UI incorreta:** a UI principal ainda é Tkinter, rejeitada pela arquitetura final.

### Baseline numérica

- Testes Python executados: `0` (bloqueio ambiental).
- Testes Python no código: `86` métodos em 16 módulos.
- Testes .NET existentes: `0`.
- Builds concluídos nesta baseline: `0`.

## Correções realizadas

- Runtime de desenvolvimento restaurado em `.venv` e SDK .NET 8.0.424 instalado localmente em `.dotnet`.
- Baseline repetida com a venv: 86 testes, 85 aprovados e 1 skip DPAPI esperado; `compileall` aprovado.
- Criado protocolo IPC JSON v1 com validação, limite de 64 KiB e allowlist.
- Criado host Python em Windows Named Pipes e smoke real de ping/dashboard/shutdown.
- Criado Desktop WPF com reconexão, status de Core, dashboard, HUD, hotkey, tray, métricas e KnowledgeGraph real.
- Corrigido fundo claro herdado no painel de contexto após inspeção da primeira captura WPF.
- Corrigido falso positivo de Vosk disponível quando `vosk_model_path` estava vazio.
- Corrigido diagnóstico com `microphone_device = -1` para usar o dispositivo padrão real.
- Corrigido diagnóstico para tentar sample rate nativo após falha em 16 kHz.
- Implementado pipeline de captura com pre-roll, VAD energético, silêncio final, limite de duração, RMS, peak e clipping.
- Implementado provider whisper.cpp multilíngue configurável e teste A/B reutilizando o mesmo WAV.
- Microfone funcional atual identificado: ID 13, Realtek WDM-KS, 44.100 Hz.

## Validação após as correções

- Python final: 99 testes, 98 aprovados e 1 skip DPAPI esperado.
- Testes focados novos: 12/12 aprovados.
- `scripts.smoke_ipc`: aprovado.
- `scripts.smoke_voice` sem fala: captura aprovada no device 13.
- WPF: build aprovado com 0 warnings e 0 errors.
- Smoke visual WPF: Core conectado, Obsidian online, grafo real renderizado e screenshot salvo.
- Memória observada da árvore WPF + Core: 183,83 MiB; CPU instantânea 0,0% após 3 s.
- STT Whisper real/WER: pendente por ausência de binário e modelos base/small auditados.
