# ProvaLab Local

## Requisitos
- Python 3.11+
- Node.js 18+

## Backend (FastAPI)
No diretorio raiz:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API local: `http://localhost:8000`  
Docs: `http://localhost:8000/docs`

## Frontend estatico
Em outro terminal:

```powershell
cd frontend\dist
python -m http.server 5173
```

Frontend local: `http://localhost:5173`

## Billing Premium (Hotmart)
Implementado:
- Campos de assinatura/trial em `profiles`.
- Webhook `POST /api/hotmart/webhook`.
- Idempotencia por evento em `payment_event_logs`.
- Liberacao premium por assinatura ativa ou trial valido.
- Bloqueio de conteudo premium nas rotas de exercicios/tentativas.
- Email de boas-vindas premium (Resend) em background.
- Status de assinatura para frontend em `GET /billing/status`.

## Variaveis de ambiente
No `.env` da raiz:

- `TRIAL_DAYS=7`
- `HOTMART_WEBHOOK_TOKEN=...`
- `HOTMART_CHECKOUT_URL=...`
- `RESEND_API_KEY=...`
- `RESEND_FROM_EMAIL=nao-responda@seudominio.com`
- `APP_BASE_URL=http://localhost:5173`

## Testes manuais do webhook
Header:
- `x-hotmart-hottok: <HOTMART_WEBHOOK_TOKEN>`

### PURCHASE_APPROVED
```powershell
curl -X POST "http://localhost:8000/api/hotmart/webhook" `
  -H "Content-Type: application/json" `
  -H "x-hotmart-hottok: SEU_TOKEN" `
  -d "{\"event\":\"PURCHASE_APPROVED\",\"data\":{\"buyer\":{\"email\":\"usuario@teste.com\"},\"transaction\":{\"id\":\"tx-001\",\"status\":\"approved\"},\"subscription\":{\"id\":\"sub-001\",\"access_until\":\"2026-03-17T00:00:00Z\"}}}"
```

### SUBSCRIPTION_CHARGED
```powershell
curl -X POST "http://localhost:8000/api/hotmart/webhook" `
  -H "Content-Type: application/json" `
  -H "x-hotmart-hottok: SEU_TOKEN" `
  -d "{\"event\":\"SUBSCRIPTION_CHARGED\",\"data\":{\"buyer\":{\"email\":\"usuario@teste.com\"},\"transaction\":{\"id\":\"tx-002\",\"status\":\"charged\"},\"subscription\":{\"id\":\"sub-001\",\"next_charge_date\":\"2026-04-17T00:00:00Z\"}}}"
```

### SUBSCRIPTION_CANCELED
```powershell
curl -X POST "http://localhost:8000/api/hotmart/webhook" `
  -H "Content-Type: application/json" `
  -H "x-hotmart-hottok: SEU_TOKEN" `
  -d "{\"event\":\"SUBSCRIPTION_CANCELED\",\"data\":{\"buyer\":{\"email\":\"usuario@teste.com\"},\"transaction\":{\"id\":\"tx-003\",\"status\":\"canceled\"},\"subscription\":{\"id\":\"sub-001\"}}}"
```

### SUBSCRIPTION_EXPIRED
```powershell
curl -X POST "http://localhost:8000/api/hotmart/webhook" `
  -H "Content-Type: application/json" `
  -H "x-hotmart-hottok: SEU_TOKEN" `
  -d "{\"event\":\"SUBSCRIPTION_EXPIRED\",\"data\":{\"buyer\":{\"email\":\"usuario@teste.com\"},\"transaction\":{\"id\":\"tx-004\",\"status\":\"expired\"},\"subscription\":{\"id\":\"sub-001\"}}}"
```

## Validacao rapida
1. Criar usuario via `/auth/signup`.
2. Confirmar trial via `/profiles/me` ou `/billing/status`.
3. Enviar `PURCHASE_APPROVED`.
4. Validar `plan=premium` e `subscription_status=active`.
5. Reenviar payload identico e validar resposta `duplicate=true`.
6. Enviar `SUBSCRIPTION_EXPIRED` e validar bloqueio de conteudo premium.
