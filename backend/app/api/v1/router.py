from fastapi import APIRouter
from app.api.v1.endpoints import auth, chat, connectors, llm

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Autenticación & Usuarios"])
api_router.include_router(chat.router, prefix="/chat", tags=["Consultas & Dashboards IA"])
api_router.include_router(connectors.router, prefix="/connectors", tags=["Fuentes BD Corporativas"])
api_router.include_router(llm.router, prefix="/llm", tags=["Motor LLM Local"])
