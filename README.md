# ProvaLab Local

## Requisitos
- Python 3.11+
- Node.js 18+

## 1) Backend (FastAPI)
No diretório raiz:

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

API local: `http://localhost:8000`  
Docs: `http://localhost:8000/docs`

## 2) Frontend (bundle estático já compilado)
Em outro terminal:

```powershell
cd frontend\dist
python -m http.server 5173
```

Frontend local: `http://localhost:5173`

## Observações
- O backend usa SQLite local por padrão (`sqlite:///./provalab.db`).
- O frontend foi configurado para consumir `http://localhost:8000`.
