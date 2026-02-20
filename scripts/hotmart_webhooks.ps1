param(
  [string]$BaseUrl = "http://localhost:8000",
  [string]$Token = "",
  [string]$Email = "usuario@teste.com"
)

$headers = @{
  "Content-Type"    = "application/json"
}

if ($Token) {
  $headers["x-hotmart-hottok"] = $Token
}

function Send-Webhook {
  param(
    [string]$Event,
    [hashtable]$Data
  )

  $payload = @{
    event = $Event
    data  = $Data
  } | ConvertTo-Json -Depth 8

  Write-Host "`n==> $Event"
  try {
    $response = Invoke-RestMethod -Method Post -Uri "$BaseUrl/api/hotmart/webhook" -Headers $headers -Body $payload
    $response | ConvertTo-Json -Depth 8
  } catch {
    Write-Host $_.Exception.Message
  }
}

Send-Webhook -Event "PURCHASE_APPROVED" -Data @{
  buyer = @{ email = $Email }
  transaction = @{ id = "tx-001"; status = "approved" }
  subscription = @{ id = "sub-001"; access_until = "2026-03-17T00:00:00Z" }
}

Send-Webhook -Event "SUBSCRIPTION_CHARGED" -Data @{
  buyer = @{ email = $Email }
  transaction = @{ id = "tx-002"; status = "charged" }
  subscription = @{ id = "sub-001"; next_charge_date = "2026-04-17T00:00:00Z" }
}

Send-Webhook -Event "SUBSCRIPTION_CANCELED" -Data @{
  buyer = @{ email = $Email }
  transaction = @{ id = "tx-003"; status = "canceled" }
  subscription = @{ id = "sub-001" }
}

Send-Webhook -Event "SUBSCRIPTION_EXPIRED" -Data @{
  buyer = @{ email = $Email }
  transaction = @{ id = "tx-004"; status = "expired" }
  subscription = @{ id = "sub-001" }
}
