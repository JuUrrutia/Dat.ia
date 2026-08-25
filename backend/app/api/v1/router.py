from fastapi import APIRouter
from app.modules.auth.router import router as auth_router
from app.modules.chat_engine.router import router as chat_router
from app.modules.admin_catalog.router import router as admin_catalog_router
from app.modules.telemetry_audit.router import router as audit_router
from app.modules.system.router import router as system_router

api_router = APIRouter()
api_router.include_router(auth_router, prefix="/auth", tags=["Autenticación & Usuarios"])
api_router.include_router(chat_router, prefix="/chat", tags=["Consultas & Dashboards IA"])
api_router.include_router(chat_router, prefix="/llm", tags=["Motor LLM Local"])
api_router.include_router(admin_catalog_router, prefix="/connectors", tags=["Fuentes BD Corporativas"])
api_router.include_router(admin_catalog_router, prefix="", tags=["Catálogo Semántico & Diccionario de Datos"])
api_router.include_router(audit_router, prefix="/audit", tags=["Auditoría & Compliance"])
api_router.include_router(admin_catalog_router, prefix="", tags=["Exportación de Informes"])
api_router.include_router(system_router, prefix="/system", tags=["Estado del Sistema"])
