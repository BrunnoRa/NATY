# Licenças de terceiros

As versões abaixo correspondem ao ambiente validado em 4 de setembro de 2026. Consulte os arquivos de licença instalados ao redistribuir.

| Biblioteca | Finalidade | Licença | Link oficial | Observação relevante |
|---|---|---|---|---|
| Python | Runtime | PSF License | https://www.python.org/psf/license/ | Manter avisos aplicáveis na redistribuição. |
| ddgs 9.16.0 | Pesquisa web | MIT | https://github.com/deedy5/ddgs | Preservar copyright e licença. Resultados seguem termos das fontes. |
| Pillow 12.3.0 | Imagem do tray | MIT-CMU/HPND | https://github.com/python-pillow/Pillow | Preservar avisos da licença. |
| pystray 0.19.5 | Ícone de bandeja | LGPL-3.0 | https://github.com/moses-palmer/pystray | Ao distribuir, cumprir LGPL e permitir substituição/relink da biblioteca. |
| psutil 7.2.2 | Benchmark | BSD-3-Clause | https://github.com/giampaolo/psutil | Preservar copyright, condições e disclaimer. |
| Click 8.5.0 | Dependência do DDGS | BSD-3-Clause | https://github.com/pallets/click | Preservar copyright e disclaimer. |
| lxml 6.1.3 | Parsing usado pelo DDGS | BSD-3-Clause | https://lxml.de/ | Inclui componentes com avisos próprios; revisar wheel na redistribuição. |
| primp 2.0.0 | Cliente HTTP do DDGS | MIT | https://github.com/deedy5/primp | Preservar copyright e licença. |
| six 1.17.0 | Compatibilidade do pystray | MIT | https://github.com/benjaminp/six | Preservar copyright e licença. |
| Vosk 0.3.45+ (opcional) | STT offline | Apache-2.0 | https://github.com/alphacep/vosk-api | Modelos podem ter licenças próprias; verificar antes de distribuir. |
| sounddevice 0.5+ (opcional) | Captura do microfone | MIT | https://github.com/spatialaudio/python-sounddevice | Depende de PortAudio, licença MIT. |
| Piper atual (não incluído) | TTS local neural | GPL-3.0 | https://github.com/OHF-Voice/piper1-gpl | Não é dependência base; se instalado pelo usuário, roda isolado por subprocesso. O repositório legado MIT está arquivado. |
| llama-cpp-python (opcional) | LLM local | MIT | https://github.com/abetlen/llama-cpp-python | Cada modelo GGUF possui licença independente. |
| Qwen3 0.6B GGUF (opcional) | Conversa local | Apache-2.0 | https://huggingface.co/Qwen/Qwen3-0.6B-GGUF | Modelo recomendado, não redistribuído. |
| Google API Python Client/Auth (opcional) | Gmail e Calendar | Apache-2.0 | https://github.com/googleapis/google-api-python-client | OAuth e termos das APIs também se aplicam. |
| PyInstaller (desenvolvimento) | Empacotamento | GPL-2.0-or-later com exceção | https://pyinstaller.org/ | A exceção permite distribuir aplicações geradas; revisar hooks/dependências. |

Windows SAPI e Tkinter fazem parte da plataforma/runtime e não são empacotados como dependências PyPI independentes pela Naty.
