import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.logging import logger
from app.api.v1.router import api_router
from app.core.database import SessionLocal
from app.db.init_db import init_db

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    description="Backend Sidecar Python para Democratización de Datos Corporativos con IA Local"
)

# CORS configuration for Vite dev server & Electron desktop app
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API v1 router
app.include_router(api_router, prefix=settings.API_V1_STR)

@app.on_event("startup")
def on_startup():
    logger.info("Iniciando Servidor Backend FastAPI...")
    # 1. Ensure a working SQLite database exists if needed
    try:
        import os
        db_path = settings.SQLITE_DB_PATH
        if not os.path.exists(db_path):
            logger.info(f"No se encontró base de datos SQLite activa. Generando demo automática en {db_path}...")
            try:
                from setup_demo_db import setup_demo_sqlite
                setup_demo_sqlite()
            except Exception as e_demo:
                logger.warning(f"No se pudo autogenerar demo SQLite: {e_demo}")
    except Exception as e:
        logger.warning(f"Aviso al verificar base de datos SQLite: {str(e)}")

    # 2. Initialize App Metadata (Users, Roles, RBAC permissions)
    try:
        db = SessionLocal()
        init_db(db)
        db.close()
        logger.info("Base de datos de metadatos e identidades inicializada correctamente.")
    except Exception as e:
        logger.warning(f"Aviso de inicio de base de datos: {str(e)}. El sistema operará en modo contingencia.")

@app.get("/")
def root():
    return {
        "status": "online",
        "app": settings.PROJECT_NAME,
        "mode": "100% Offline Standalone",
        "docs": "/docs"
    }

if __name__ == "__main__":
    uvicorn.run("main:app", host=settings.HOST, port=settings.PORT, reload=True)
