# Roadmap

## V1 — baseline preservado

Core determinístico, SQLite, tarefas/listas/lembretes/projetos, Obsidian básico, pesquisa DDGS, Tkinter, tray, hotkey, SAPI/Vosk opcional, testes e benchmark. Evidências: `BASELINE_V2.md`.

## V2 — implementada neste repositório

- onboarding e dashboard escuro com HUD, estados e grafo;
- Obsidian estruturado, frontmatter, FTS5 incremental, retrieval e wikilinks;
- conversa contextual com memória explícita;
- skills fechadas e roteamento em camadas;
- pesquisa auditável, DDGS, Perplexity opcional e fallback;
- voz instalável/testável e seleção de dispositivo;
- llama.cpp/Qwen opcional com limites e unload;
- Gmail/Calendar OAuth opcional, DPAPI e confirmação de envio/exclusão;
- proatividade configurável e antirrepetição persistida;
- testes V1+V2, smokes e benchmark ampliado.

## Próximos passos

- validar GUI, tray, hotkey, SAPI e microfone numa instalação Python desktop com Tcl/Tk;
- concluir uma autorização Google real e validar os smokes somente leitura;
- testar Qwen em hardware-alvo de 8 GB antes de ativá-lo por padrão para qualquer perfil;
- melhorar edição visual de entidades, recorrências e ambiguidades do NLU;
- empacotar, gerar SBOM, escanear, assinar e testar atualização/rollback.

## Futuro, não implementado

- wake word treinado especificamente para “Naty”;
- Android e sincronização ponta a ponta;
- conflitos multi-dispositivo;
- memória semântica opcional com avaliação objetiva de custo/benefício.
