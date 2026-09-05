# Aceite manual da NATY V3

Use o aplicativo instalado e marque cada item. Registre falhas com horário e a mensagem mostrada pela interface; não inclua tokens ou credenciais.

- [ ] **Hotkey:** pressione `Ctrl+Alt+Space`; o HUD deve abrir. Em Configurações → Sobre → Executar diagnóstico, Hotkey deve aparecer como **OK**.
- [ ] **Voz/pesquisa:** diga “Naty, pesquisa as principais novidades sobre inteligência artificial hoje.” Deve ocorrer Whisper → pesquisa com fontes → Context/Research → TTS.
- [ ] **Follow-up:** diga “E qual dessas é mais importante?”; a resposta deve manter o contexto anterior.
- [ ] **Reminder:** diga “Me lembra amanhã às três de falar com o professor.”; confirme a persistência no dashboard.
- [ ] **Automation:** diga “Todo domingo às sete da noite me lembra de planejar a semana.”
- [ ] **Obsidian:** pergunte “O que você sabe sobre meu projeto?”; a resposta não deve inventar conteúdo ausente.
- [ ] **Spotify:** diga “Abre Spotify.” e depois “Próxima música.”
- [ ] **ChatGPT:** diga “Quero analisar profundamente minha carreira.”; confira o pacote de contexto sem segredos.
- [ ] **Learning:** diga “Prefiro respostas mais curtas pela manhã.”; a NATY deve pedir consentimento antes de guardar.
- [ ] **Sync:** no simulador/teste, crie no device A, importe no B, conclua no B e importe no A.
- [ ] **Tray:** feche a janela com “Fechar para a bandeja” habilitado; a NATY deve continuar na bandeja.
- [ ] **Exit:** use Bandeja → Sair; `Naty.exe`, `Naty.Core.exe`, Whisper e Piper não devem permanecer em execução.

## Teste de precisão das 10 frases

Abra Configurações → Voz → **Teste de precisão (10 frases)**. O modo guiado usa o pipeline STT atual sem executar os comandos falados e registra automaticamente transcrição, WER e latência. Fale naturalmente, mantenha a mesma distância do microfone e não altere ganho/modelo entre frases. Ao final, copie a tabela para o registro de aceite. Resultado sugerido:

| # | Frase | Transcrição | WER | Latência |
|---:|---|---|---:|---:|
| 1–10 | preencher durante o aceite |  |  |  |

Critério: nenhuma falha silenciosa; eventuais erros devem aparecer de forma amigável e o restante da NATY deve continuar disponível.
