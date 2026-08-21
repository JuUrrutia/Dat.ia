import csv
import io
import datetime
import math
from typing import Optional, Any
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_admin
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.audit_schema import AuditLogsPage, AuditLogOut

router = APIRouter()

def _apply_audit_filters(
    query,
    start_date: Optional[datetime.datetime] = None,
    end_date: Optional[datetime.datetime] = None,
    username: Optional[str] = None,
    target_database: Optional[str] = None,
    validation_status: Optional[str] = None
):
    if start_date:
        query = query.filter(AuditLog.timestamp >= start_date)
    if end_date:
        query = query.filter(AuditLog.timestamp <= end_date)
    if username:
        query = query.filter(AuditLog.username.ilike(f"%{username.strip()}%"))
    if target_database:
        query = query.filter(AuditLog.target_database.ilike(f"%{target_database.strip()}%"))
    if validation_status:
        query = query.filter(AuditLog.validation_status.ilike(f"%{validation_status.strip()}%"))
    return query

@router.get("", response_model=AuditLogsPage)
def get_audit_logs(
    start_date: Optional[datetime.datetime] = None,
    end_date: Optional[datetime.datetime] = None,
    username: Optional[str] = None,
    target_database: Optional[str] = None,
    validation_status: Optional[str] = None,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
) -> Any:
    """
    Returns paginated audit logs filtered by date range, user, target database or status.
    Protected by Administrator role.
    """
    base_query = db.query(AuditLog)
    filtered_query = _apply_audit_filters(
        base_query,
        start_date=start_date,
        end_date=end_date,
        username=username,
        target_database=target_database,
        validation_status=validation_status
    )

    total = filtered_query.count()
    total_pages = max(1, math.ceil(total / page_size)) if total > 0 else 1

    items = filtered_query.order_by(AuditLog.timestamp.desc()) \
        .offset((page - 1) * page_size) \
        .limit(page_size) \
        .all()

    return AuditLogsPage(
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
        items=[AuditLogOut.model_validate(item) for item in items]
    )

@router.get("/export")
def export_audit_logs_csv(
    start_date: Optional[datetime.datetime] = None,
    end_date: Optional[datetime.datetime] = None,
    username: Optional[str] = None,
    target_database: Optional[str] = None,
    validation_status: Optional[str] = None,
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
) -> StreamingResponse:
    """
    Generates and streams a downloadable CSV report of filtered audit logs.
    Protected by Administrator role.
    """
    base_query = db.query(AuditLog)
    filtered_query = _apply_audit_filters(
        base_query,
        start_date=start_date,
        end_date=end_date,
        username=username,
        target_database=target_database,
        validation_status=validation_status
    )

    logs = filtered_query.order_by(AuditLog.timestamp.desc()).all()

    output = io.StringIO()
    # Add UTF-8 BOM so Excel opens special characters correctly
    output.write('\ufeff')
    writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    # Header
    writer.writerow([
        "ID",
        "Fecha UTC",
        "Usuario",
        "Rol",
        "Pregunta / Prompt",
        "SQL Generado",
        "Estado Validación",
        "Base de Datos",
        "Tiempo Ejecución (ms)",
        "Filas Devueltas",
        "Mensaje de Error"
    ])

    for log in logs:
        writer.writerow([
            log.id,
            log.timestamp.strftime("%Y-%m-%d %H:%M:%S") if log.timestamp else "",
            log.username or "",
            log.user_role or "",
            log.question_prompt or "",
            log.sql_generated or "",
            log.validation_status or "",
            log.target_database or "",
            log.execution_time_ms or 0,
            log.rows_returned or 0,
            log.error_message or ""
        ])

    csv_data = output.getvalue()
    output.close()

    filename = f"datia_audit_logs_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"

    return StreamingResponse(
        io.BytesIO(csv_data.encode('utf-8-sig')),
        media_type="text/csv",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )
