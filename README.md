# NATY Agent V2

Naty é uma agente pessoal local para Windows 11. O núcleo funciona sem LLM e sem nuvem: tarefas, projetos, listas, lembretes, agenda local, notas, memória consentida, planejamento e busca no Vault usam regras, SQLite e FTS5. IA local, voz, pesquisa web e Google Workspace são camadas opcionais e isoladas.

## Requisitos e instalação

- Windows 11;
- Python 3.11 ou mais recente com Tcl/Tk;
- aproximadamente 100 MB para o núcleo;
- internet apenas para instalar pacotes/modelos, pesquisar ou usar integrações autorizadas.

Execute `setup_naty.bat` e depois `run_naty.bat`. Para desenvolvimento:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

Na primeira abertura, o onboarding pergunta nome, Vault, voz e proatividade. Ele não baixa modelo, conecta conta ou altera startup por conta própria.

## Uso

`Ctrl+Alt+Espaço` abre o HUD e inicia push-to-talk quando a voz está habilitada. A janela principal reúne tarefas do dia, conversa, grafo de conhecimento, contexto, módulos e métricas leves. Exemplos:

```text
cria tarefa entregar relatório sexta
adiciona café e leite na lista de compras
me lembra amanhã às 15h de ligar para João
estou cansada hoje
qual é a tarefa mais curta?
indo ao mercado
lembre que eu prefiro reuniões pela manhã
o que você lembra sobre mim?
pesquisa cadeira ergonômica
compara RX 7600 com RTX 4060
```

Memórias só são persistidas após linguagem explícita como “lembre que…”. Exclusões e envio de e-mail exigem confirmação em um segundo turno.

## Obsidian como cérebro externo

Escolha a raiz de um Vault no onboarding ou em Configurações. A configuração mantém separados `obsidian_vault_path` (raiz do Vault) e `naty_obsidian_path` (obrigatoriamente a subpasta `Naty/`). A indexação e todas as escritas ficam limitadas a essa subpasta. Com consentimento, a Naty cria somente arquivos ausentes dentro de `Naty/`:

```text
Naty/
  00 - Sistema/
  01 - Eu/
  02 - Dashboard/
  03 - Projetos/
  04 - Listas/
  05 - Memórias/{Pessoas,Lugares,Preferências,Fatos}/
  06 - Pesquisas/
  07 - Diário/
  08 - Notas/
  99 - Templates/
```

Markdown é indexado incrementalmente em SQLite FTS5. Wikilinks viram arestas do grafo. A recuperação é limitada por número de notas e caracteres; conteúdo recuperado entra no prompt como **dado não confiável**, nunca como instrução. Escritas geradas usam frontmatter, bloco `NATY:BEGIN/END` e replace atômico; texto pessoal fora do bloco é preservado.

Para validar e importar de forma reproduzível o Vault configurado sem criar nem sobrescrever notas existentes:

```powershell
.\.venv\Scripts\python.exe -m scripts.smoke_obsidian_real
```

## Voz local

SAPI é o TTS padrão e não requer download. A tela **Voz** lista microfones e vozes, testa cada um e permite ajustar velocidade e volume. Para STT pt-BR:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-voice.txt
setup_voice.bat
```

O instalador informa origem, tamanho e licença antes de baixar o `vosk-model-small-pt-0.3` oficial. Vosk carrega somente durante o uso e pode ser descarregado logo depois. Wake word permanece desligado: não existe modelo “Naty” confiável incluído. Piper não faz parte da instalação base; veja `LICENSES.md`.

## Pesquisa

DDGS é o provider padrão. Resultados, fontes, alegações e horário de observação são preservados. Comparações podem ler até três páginas com timeout e tamanho limitado. A pesquisa salva no Obsidian as seções Data, Consulta, Resumo, Resultados, Comparação, Fontes e Minha decisão.

Perplexity é opcional e potencialmente pago. Só é usada com `perplexity_enabled = true` e `NATY_PERPLEXITY_API_KEY` no ambiente. Se nenhum provider responder, a Naty oferece uma URL para abrir no navegador mediante ação explícita.

## IA local opcional

O funcionamento normal não usa IA. Para conversa mais aberta, o modelo recomendado para máquinas modestas é Qwen3 0.6B Q4_K_M (~484 MB, Apache-2.0):

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-local-ai.txt
setup_ai.bat
.\.venv\Scripts\python.exe -m scripts.benchmark_llm
```

O instalador pede confirmação antes do download. `llama.cpp` usa CPU (`n_gpu_layers=0`), respeita limites de arquivo/RAM, carrega sob demanda e descarrega após inatividade. Se falhar, o núcleo determinístico continua.

## Gmail e Google Calendar opcionais

1. Crie no Google Cloud um OAuth Client do tipo **Desktop app**.
2. Salve o JSON em um local privado e indique o caminho em `google_credentials_path`.
3. Instale `requirements-google.txt`.
4. Diga `conectar Google` e conclua o consentimento no navegador.

O token OAuth é protegido pelo DPAPI do usuário do Windows em `data/secrets/google.token`; nunca é salvo em TOML ou log. A Naty pode pesquisar/resumir mensagens, criar rascunhos e ler eventos. Enviar rascunho ou excluir mensagem/evento exige confirmação explícita. Exemplos: `mostra emails não lidos`, `cria rascunho de email para ana@example.com assunto Oi mensagem Tudo bem?`, `enviar rascunho`, `agenda Google`.

Para remover o token local, diga `desconectar Google` e confirme com `sim`; depois revogue o acesso também na página de segurança da conta Google se quiser invalidá-lo remotamente. Proatividade e cada componente (briefing, revisão e follow-up) podem ser ligados ou desligados em **Configurações**. RAM/CPU atuais aparecem no painel direito e a medição reproduzível é gerada por `scripts/benchmark_resources.py`.

## Testes e benchmark

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
.\.venv\Scripts\python.exe -m scripts.benchmark_resources
.\.venv\Scripts\python.exe -m scripts.smoke_research
.\.venv\Scripts\python.exe -m scripts.smoke_voice
.\.venv\Scripts\python.exe -m scripts.smoke_gmail
.\.venv\Scripts\python.exe -m scripts.smoke_calendar
.\.venv\Scripts\python.exe -m scripts.smoke_llm
```

Testes unitários não usam rede, microfone ou conta real. Smokes opcionais reportam `SKIP` quando a camada não foi configurada. Resultados desta máquina estão em `BENCHMARK.md`; o baseline imutável da V1 está em `BASELINE_V2.md`.

## Limitações reais

- o parser cobre formulações comuns em pt-BR, não linguagem arbitrária;
- a interface precisa de Python com Tcl/Tk e validação manual na sessão desktop;
- o smoke ao vivo do microfone abriu o dispositivo e carregou o Vosk, mas não obteve transcrição inteligível nesta sessão;
- wake word “Naty”, Android e sincronização multi-dispositivo não estão implementados;
- pesquisa depende da rede e das fontes; preços podem mudar;
- Google, Perplexity e IA local permanecem desativados até configuração explícita;
- empacotamento e assinatura do executável ainda não foram validados para distribuição.

Consulte `ARCHITECTURE.md`, `SECURITY.md`, `PRIVACY.md`, `LICENSES.md` e `ROADMAP.md`.
