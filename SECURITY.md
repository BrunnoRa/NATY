# Segurança

## Fronteiras

- texto web, e-mail, Markdown e dados recuperados são dados não confiáveis;
- nenhuma skill oferece shell ou execução dinâmica;
- o registro de skills e conectores é fechado;
- downloads aceitam HTTPS e hosts allowlisted, usam `.part`, tamanho mínimo, checksum quando publicado e replace final;
- modelos/binários não são executados a partir de resultados de pesquisa.

## Ações sensíveis

Apagar todas as tarefas, enviar rascunho e excluir e-mail/evento exigem confirmação explícita. Abrir OAuth, habilitar startup, preparar Vault, baixar modelo e ativar proatividade dependem de ação do usuário. O fallback de navegador só abre após comando próprio.

## Segredos Google

O JSON do cliente OAuth é indicado pelo usuário e não deve ficar no repositório. Tokens são criptografados com DPAPI para o usuário atual em `data/secrets/google.token`. Se o perfil Windows/DPAPI não estiver disponível, a operação falha: não existe fallback em texto simples. `.gitignore` exclui credenciais/tokens comuns.

## Logs e distribuição

Logs não devem conter áudio, token, senha, corpo integral de e-mail ou prompt recuperado. Antes de distribuir: gerar SBOM, auditar licenças, fixar hashes dos artefatos publicados, escanear dependências, assinar binário/instalador e testar rollback. PyInstaller presente é preparação, não atestado de segurança de distribuição.
