from app.modules.telemetry_audit.router import router as audit_router
from app.modules.system.router import router as system_router

__all__ = ["audit_router", "system_router"]
