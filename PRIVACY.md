# Privacidade

## Local por padrão

Tarefas, projetos, lembretes, agenda local, listas, notas, memórias, índice do Vault e histórico de ações ficam em `data/naty.db`. Configurações ficam em `config.toml`. O áudio do push-to-talk é processado em memória pelo Vosk e não é salvo. O contexto mantém no máximo 12 turnos em RAM; a conversa integral não é persistida.

## Quando dados saem do computador

- DDGS recebe a consulta; comparações podem acessar páginas escolhidas;
- Perplexity recebe consulta/contexto somente quando explicitamente habilitada;
- Google recebe operações Gmail/Calendar após OAuth e conforme os escopos consentidos;
- downloads de Vosk/Qwen acessam as origens mostradas pelo instalador.

Desative `research_enabled`, `perplexity_enabled` e `google_enabled` para manter o uso operacional offline.

## Controle e retenção

Memórias aparecem na tela **Memórias** e podem ser excluídas com confirmação. Desconectar Google remove o token protegido local; revogue também o acesso na conta Google para invalidação remota. Para backup, encerre a Naty e copie `data/naty.db`, `config.toml` e, se usado, `Naty/` no Vault. Para remoção total, encerre o aplicativo e exclua manualmente esses dados e modelos.

## Obsidian

A Naty só cria estrutura após consentimento. Arquivos existentes não são sobrescritos pelo bootstrap. Em arquivos gerenciados, somente blocos marcados são substituídos; o índice lê apenas o Markdown da subpasta `Naty/` do Vault selecionado e guarda texto normalizado localmente no SQLite. Notas fora dessa subpasta não são indexadas nem alteradas.
