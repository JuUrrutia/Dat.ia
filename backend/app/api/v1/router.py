from fastapi import APIRouter
from app.api.v1.endpoints import auth, chat, connectors, catalog, llm, audit, reports, system

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Autenticación & Usuarios"])
api_router.include_router(chat.router, prefix="/chat", tags=["Consultas & Dashboards IA"])
api_router.include_router(connectors.router, prefix="/connectors", tags=["Fuentes BD Corporativas"])
api_router.include_router(catalog.router, prefix="/catalog", tags=["Catálogo Semántico & Diccionario de Datos"])
api_router.include_router(llm.router, prefix="/llm", tags=["Motor LLM Local"])
api_router.include_router(audit.router, prefix="/audit", tags=["Auditoría & Compliance"])
api_router.include_router(reports.router, prefix="/reports", tags=["Exportación de Informes"])
api_router.include_router(system.router, prefix="/system", tags=["Estado del Sistema"])

