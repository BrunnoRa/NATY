# NATY V3.1

NATY é uma assistente pessoal local-first para Windows 11. A interface principal usa C#/.NET/WPF e conversa com o Core Python por Windows Named Pipes. Tarefas, listas, lembretes, planejamento, memória temporal e configurações continuam disponíveis sem LLM e sem serviços pagos.

## Instalação e primeiro uso

Para uso normal:

1. Execute `installer\NatySetup.exe`.
2. Abra a **NATY** pelo menu Iniciar ou pelo atalho da área de trabalho.
3. Se a voz ainda não estiver pronta, clique em **Configurar** e conclua os passos em **Configurações > Voz**.

O aplicativo verifica o pipeline de voz em segundo plano. O Whisper Base pode ser instalado ou reparado pela própria tela, o microfone é escolhido em uma lista amigável e os caminhos técnicos ficam recolhidos em **Detalhes avançados**. Modelos grandes não incluídos no instalador são oferecidos no primeiro uso; o usuário não precisa executar Python, PowerShell ou scripts de setup.

Dados mutáveis, configuração, banco e logs ficam em `%LOCALAPPDATA%\NATY`. A instalação é feita por usuário e não exige privilégios administrativos.

## Voz

`Ctrl+Alt+Espaço` ou o botão de microfone inicia o push-to-talk. O pipeline preferencial usa Whisper Base multilíngue para reconhecimento e Windows SAPI ou Piper para resposta falada.

Em **Configurações > Voz** é possível:

- escolher e persistir o microfone;
- instalar ou reparar o Whisper;
- escolher e configurar o TTS;
- testar a voz completa da NATY;
- abrir detalhes técnicos somente quando necessário.

Se algum componente estiver ausente, a NATY exibe “Configuração de voz incompleta” e oferece a correção dentro do aplicativo, sem apresentar um erro técnico no botão de voz.

## Brain Mode e Smart Router

O Smart Router prioriza ações locais e contexto pessoal antes de decidir entre pesquisa, conversa ou delegação:

1. skills locais e seguras;
2. memória, Obsidian e planejamento;
3. pesquisa factual com fontes;
4. delegação de análises profundas ao ChatGPT;
5. esclarecimento, somente quando o pedido for realmente ambíguo.

Perguntas naturais não precisam começar com “pesquisa”. Por exemplo:

```text
Quem criou Python?
O que é RAG?
Qual é a versão mais recente do Python?
Qual a diferença entre Java e C#?
Como funciona uma API REST?
```

Informações atuais usam pesquisa obrigatoriamente e aparecem na visão de pesquisa com fontes. Pedidos de decisão ou análise profunda preparam um `ContextPack` limitado à pergunta, contexto curto da sessão, projeto e memórias relevantes e aplicativo ativo quando útil; o Vault inteiro nunca é enviado.

## Exemplos de uso

```text
O que eu tenho hoje?
Onde paramos ontem?
O que você sabe sobre meu projeto NATY?
Meu computador está lento.
Adiciona café na lista.
Me lembra amanhã às três de falar com o professor.
Abra Spotify.
Próxima música.
Me ajuda a decidir se estudo Java ou segurança.
```

Conversa não vira ação automaticamente. “Estou cansado” considera o contexto disponível, e “Quero estudar Java” pergunta se o usuário deseja conversar ou adicionar o assunto ao planejamento.

## Memória e Obsidian

SQLite é a fonte operacional. O Obsidian funciona como cérebro externo legível e todas as leituras e escritas gerenciadas ficam confinadas à subpasta configurada `Naty/` do Vault. Memórias pessoais são persistidas somente após linguagem explícita ou confirmação do usuário.

## Desenvolvimento

Pré-requisitos: Python 3.11+ e SDK .NET 8.

```powershell
cd C:\Users\yster\Desktop\NATY
.\setup_naty.bat
.\.venv\Scripts\python.exe core_host.py --pipe Naty.Core.v1
```

Em outro terminal, compile e execute o Desktop:

```powershell
.\.dotnet\dotnet.exe build desktop\Naty.Desktop\Naty.Desktop.csproj
.\desktop\Naty.Desktop\bin\Debug\net8.0-windows\Naty.exe
```

O Desktop normalmente inicia o Core sozinho; os comandos separados servem para diagnóstico de desenvolvimento.

## Testes

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
.\.venv\Scripts\python.exe -m compileall -q .
.\.dotnet\dotnet.exe build desktop\Naty.Desktop\Naty.Desktop.csproj --no-restore
.\.dotnet\dotnet.exe test desktop\Naty.Desktop\Naty.Desktop.csproj --no-build
git diff --check
```

Os testes unitários não dependem de rede, conta real ou interação com microfone. Validações humanas de áudio e integrações autenticadas continuam separadas.

## Empacotamento

```powershell
.\.venv\Scripts\python.exe -m scripts.build_windows
```

Saídas esperadas:

- `installer\Naty-Windows-3.1.0.zip`;
- `installer\NatySetup.exe` quando o Inno Setup estiver disponível.

Consulte também `ARCHITECTURE.md`, `SECURITY.md`, `PRIVACY.md`, `LICENSES.md` e `STATUS_NATY.md`.
