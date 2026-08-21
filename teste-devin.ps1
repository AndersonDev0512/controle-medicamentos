$headers = @{
    Authorization = "Bearer apk_user_dXNlci05Y2RmYWY3NmM2OTc0NzhmYjM2MjA3NWRjODg0YjkyMV9vcmctZGZlMTk2ZGJhNWFkNDYwYjlkOGM5MTIxNTJiODJiODM6ZDdhMTcyN2UzNTlmNGRhYmI4ZDg0ZjBhODhhMjIxZTQ="
    "Content-Type" = "application/json"
}

$body = @{
    prompt = "Diga apenas OK"
} | ConvertTo-Json

$response = Invoke-RestMethod `
    -Uri "https://api.devin.ai/v1/sessions" `
    -Method Post `
    -Headers $headers `
    -Body $body

$response | ConvertTo-Json -Depth 10