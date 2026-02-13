import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine, Base
from app.routers import auth, profiles, exercises, attempts

# Criar tabelas no banco
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ProvaLab API",
    description="API para plataforma de exercícios educacionais",
    version="1.0.0"
)

from fastapi.responses import Response

@app.options("/{path:path}")
async def options_handler(path: str):
    return Response(status_code=200)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar rotas
app.include_router(auth.router)
app.include_router(profiles.router)
app.include_router(exercises.router)
app.include_router(attempts.router)

@app.get("/")
def root():
    return {
        "message": "ProvaLab API",
        "version": "1.0.0",
        "docs": "/docs"
    }

@app.get("/health")
def health():
    return {"status": "ok"}
