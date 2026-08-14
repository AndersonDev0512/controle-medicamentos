# Controle de Medicamentos

Este repositório é uma aplicação Streamlit para controle simples de medicamentos usando Google Sheets como backend.

## Pré-requisitos

- Python 3.9+ instalado
- `pip` para instalar dependências
- Conta de serviço (Service Account) do Google com permissões para acessar a planilha Google Sheets

Instale dependências:

```bash
pip install -r requirements.txt
```

## Configuração local

Existem três formas suportadas para fornecer as credenciais da Service Account e o ID da planilha:

1) Usando `st.secrets` (arquivo local para desenvolvimento): crie o arquivo `.streamlit/secrets.toml` na raiz do repositório com, por exemplo:

```toml
gcp_service_account = '''
{
  "type": "service_account",
  "project_id": "...",
  "private_key_id": "...",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "...@...iam.gserviceaccount.com",
  "client_id": "...",
  ...
}
'''

SPREADSHEET_ID = "<SUA_SPREADSHEET_ID_AQUI>"
CLINIC_NAME = "Minha Clínica"
RESPONSIBLE_EMAIL = "seu@email.com"
```

Observação: preserve quebras de linha em `private_key` ou cole o JSON inteiro entre `'''` (triple quotes).

2) Usando variável de ambiente com o JSON:

PowerShell:

```powershell
$env:GCP_SERVICE_ACCOUNT = Get-Content C:\caminho\service-account.json -Raw
$env:SPREADSHEET_ID = "<SUA_SPREADSHEET_ID_AQUI>"
python -m streamlit run app.py
```

Bash:

```bash
export GCP_SERVICE_ACCOUNT="$(cat /path/service-account.json)"
export SPREADSHEET_ID="<SUA_SPREADSHEET_ID_AQUI>"
python -m streamlit run app.py
```

3) Usando `GOOGLE_APPLICATION_CREDENTIALS` apontando para o arquivo JSON:

PowerShell:

```powershell
$env:GOOGLE_APPLICATION_CREDENTIALS = 'C:\caminho\service-account.json'
python -m streamlit run app.py
```

Bash:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="/path/service-account.json"
export SPREADSHEET_ID="<SUA_SPREADSHEET_ID_AQUI>"
python -m streamlit run app.py
```

## Deploy no Streamlit Community Cloud (app.streamlit.io)

1. No painel do Streamlit Cloud, selecione seu repositório e conecte o app.
2. Em **Settings → Secrets**, adicione os seguintes segredos:
   - `gcp_service_account` → cole o JSON inteiro da Service Account (value deve ser o JSON, não o caminho).
   - `SPREADSHEET_ID` → o ID (ou URL) da sua planilha.
   - Opcional: `CLINIC_NAME`, `RESPONSIBLE_EMAIL`.

3. Publique o app. O código tenta `st.secrets['gcp_service_account']` primeiro, depois variáveis de ambiente e `GOOGLE_APPLICATION_CREDENTIALS`.

Observação importante: não faça commit do arquivo JSON da Service Account no repositório.

## Permissões da planilha

Após configurar o segredo, obtenha o `client_email` da Service Account (ex.: `xxx@yyy.iam.gserviceaccount.com`) e compartilhe a planilha com este e-mail (permissão de edição).

## Auditoria protegida

O aplicativo cria a aba `AUDITORIA` automaticamente na primeira alteração. Caso prefira criá-la antes, use exatamente esta primeira linha como cabeçalho:

```text
ID | Data | Hora | Usuário | Módulo | Registro | Campo Alterado | Valor Anterior | Valor Novo | Justificativa | Origem
```

Não inclua fórmulas nessa aba. Cada evento recebe um ID único, data, hora e `Origem = Sistema Streamlit` automaticamente.

Para bloquear a auditoria no Google Sheets:

1. Abra a aba `AUDITORIA` e selecione **Dados → Proteger páginas e intervalos**.
2. Escolha **Página** e marque `AUDITORIA`.
3. Em **Definir permissões**, selecione **Restringir quem pode editar**.
4. Mantenha apenas estes editores:
  - `anderson.erdeval@gmail.com`
  - `streamlit-medicamentos@medicamentos-504918.iam.gserviceaccount.com`
5. Para os demais usuários da planilha, conceda somente visualização ou comentário.

O proprietário da planilha continua podendo alterar proteções no Google Sheets. A conta de serviço precisa permanecer como editora da planilha para que o Streamlit consiga registrar auditorias.

## Erros comuns

- `gcp_service_account não encontrado`: verifique se o secret foi criado no Streamlit Cloud ou se exportou a variável de ambiente.
- `Planilha não encontrada`: confirme `SPREADSHEET_ID` e compartilhe a planilha com a conta de serviço.

## Segurança

- Nunca suba o JSON da Service Account ao repositório público.
- Use o painel de Secrets do Streamlit para manter as credenciais seguras.

## Ajuda

Se quiser, eu posso gerar um `.streamlit/secrets.toml` de exemplo (local) ou adicionar instruções no `CONTRIBUTING.md`. Deseja que eu crie o arquivo de exemplo? 
