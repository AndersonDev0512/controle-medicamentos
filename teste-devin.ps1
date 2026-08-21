# Sua API Key
$API_KEY = "SUA_API_KEY"

# Pergunta
$PROMPT = @"
Analise o projeto Controle de Medicamentos.

Quero saber:
1. Qual arquivo controla o cadastro de medicamentos.
2. Qual arquivo controla o estoque de materiais.
3. Onde devo implementar um novo campo chamado Fornecedor.

Responda apenas com os nomes dos arquivos e uma breve justificativa.
"@

$headers = @{
    Authorization = "Bearer $API_KEY"
    "Content-Type" = "application/json"
}

$body = @{
    prompt = $PROMPT
} | ConvertTo-Json

$response = Invoke-RestMethod `
    -Uri "https://api.devin.ai/v1/sessions" `
    -Method POST `
    -Headers $headers `
    -Body $body

$response | ConvertTo-Json -Depth 10