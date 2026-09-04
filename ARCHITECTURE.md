# Arquitetura V2

## Fluxo principal

```text
texto / push-to-talk
  → IntentRouter (regras)
  → AgentRouter
      → SkillRegistry fechado → ToolRouter → repositório/conector
      → ConversationEngine → retrieval local → LLM opcional
  → ResponseFormatter
  → UI / SAPI opcional
```

A sequência segue o que foi útil em JARVIS: planejar/rotear, selecionar capacidade, executar e responder. A implementação não copia sua pilha pesada de modelos. De OpenJarvis, adota local-first, engines preguiçosas, skills explícitas, memória e agentes agendados, mantendo tudo apropriado para Windows e pouca RAM.

## Primitivas

- `core/`: estado, eventos, contexto curto, roteadores e monitor de recursos;
- `skills/`: registro fechado de intents e permissões; não há shell arbitrário;
- `tools/`: operações determinísticas sobre domínios;
- `database/`: SQLite, WAL, foreign keys, migrations e repositórios;
- `knowledge/`: bootstrap, parser Markdown, índice incremental FTS5, retrieval limitado e grafo;
- `conversation/`: diálogo determinístico e fallback de IA;
- `research/`: `ResearchProvider`, DDGS, Perplexity opcional, leitura limitada, claims e fallback;
- `connectors/`: registro preguiçoso, Google OAuth, Gmail e Calendar;
- `voice/`: Vosk, SAPI/COM, diagnóstico de dispositivos e `VoiceSession` com janela configurável de continuação;
- `scheduler/`: lembretes, briefing/revisão opt-in e follow-up anti-spam;
- `ui/`: dashboard, HUD, onboarding, voz e grafo sem expor cadeia de raciocínio.

## Dados e contexto

SQLite é a fonte operacional. O Vault é fonte de conhecimento e superfície legível. A raiz do Vault e a subpasta gerenciada `Naty/` são configurações distintas; o índice e as escritas são confinados à subpasta, mantendo caminhos relativos à raiz para compatibilidade com o Obsidian. O índice guarda caminho, título, tags, corpo normalizado, frontmatter, wikilinks, mtime e hash. Arquivos sem mudança são ignorados; removidos saem do índice. O `ContextPack` limita quantidade/tamanho e marca cada trecho como `DADO LOCAL`.

O grafo contém somente relações observáveis: agente, notas, projetos, tarefas, memórias e wikilinks. A animação é esparsa, pausa quando não está visível e indica estados funcionais (`LISTENING`, `RETRIEVING`, `RESEARCHING`, `GMAIL`, `SPEAKING`); nunca exibe raciocínio interno.

## Carregamento sob demanda e falhas

LLM, Vosk, clientes Google e chamadas web não são necessários ao startup do core. Falhas retornam mensagens locais e não comprometem tarefas. `LlamaCppProvider` verifica arquivo/RAM, usa CPU e timer de unload. Vosk tenta 16 kHz e recorre ao sample rate nativo quando o driver exigir. O PCM16 passa por ganho automático limitado, com noise floor, antes do reconhecimento; o modelo fica carregado durante a `VoiceSession` e pode ser liberado ao encerrá-la. A sessão falada mantém o mesmo `SessionContext` durante follow-ups e encerra no timeout. DDGS e conectores têm timeout/fallback. Logs são rotativos.

## Confirmações

Ações de leitura e criação local normal executam diretamente. Exclusão em massa, envio de Gmail e exclusões remotas criam uma ação pendente e só seguem após `sim`; `cancelar` limpa a pendência.
