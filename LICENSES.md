# Componentes e licenças

Esta lista documenta decisões de arquitetura; os arquivos de licença das dependências continuam sendo a autoridade.

| Componente | Uso | Licença/decisão |
|---|---|---|
| Vosk e `vosk-model-small-pt-0.3` | STT local opcional | Apache-2.0; origem oficial |
| Qwen3 0.6B GGUF | LLM local opcional | Apache-2.0; origem oficial Qwen/Hugging Face |
| llama.cpp / llama-cpp-python | runtime LLM opcional | MIT |
| Google API Python Client/Auth | Gmail/Calendar opcional | Apache-2.0 |
| DDGS | pesquisa padrão | dependência Python; conferir licença da versão empacotada |
| Piper atual (`OHF-Voice/piper1-gpl`) | TTS opcional não incluído | GPL-3.0; isolado por subprocesso se o usuário instalar |
| Piper antigo (`rhasspy/piper`) | não adotado | repositório arquivado; apesar da licença MIT, não é base mantida |
| Windows SAPI | TTS padrão | componente do Windows; sem modelo redistribuído pela Naty |

O projeto não redistribui Vosk, Qwen, Piper ou credenciais. Os instaladores opcionais informam origem, tamanho e licença antes do download.
