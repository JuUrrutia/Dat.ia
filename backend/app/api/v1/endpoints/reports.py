import io
import json
import datetime
import logging
from typing import Any, Optional, Tuple
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.report_schema import ReportExportRequest, ReportExportData
from app.services.report_generator import ReportGeneratorService

router = APIRouter()
logger = logging.getLogger(__name__)

def _record_export_audit(
    db: Session,
    user: User,
    question: str,
    export_format: str,
    target_database: str = "demo_corporativa.db",
    rows_count: int = 0
):
    try:
        user_role_name = user.role.name if user.role else ("Administrador" if user.is_admin else "Usuario")
        log = AuditLog(
            user_id=user.id,
            username=user.username,
            user_role=user_role_name,
            question_prompt=question,
            sql_generated=f"-- EXPORTACIÓN DE INFORME EN FORMATO {export_format.upper()}",
            validation_status=f"EXPORTADO_{export_format.upper()}",
            target_database=target_database,
            execution_time_ms=0,
            rows_returned=rows_count,
            error_message=None
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.warning(f"No se pudo registrar la auditoría de exportación: {e}")

def _resolve_report_data(
    audit_log_id: int,
    current_user: User,
    chart_image_base64: Optional[str],
    db: Session
) -> Tuple[ReportExportData, AuditLog]:
    audit_log = db.query(AuditLog).filter(AuditLog.id == audit_log_id).first()
    if not audit_log:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Registro de auditoría no encontrado."
        )

    # Ownership validation: only the creator or platform admin can export results
    if audit_log.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acceso denegado: No tienes permisos para exportar consultas de otro usuario."
        )

    if not audit_log.result_snapshot:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El registro de auditoría no contiene snapshot de resultados para exportar."
        )

    try:
        raw_data = json.loads(audit_log.result_snapshot)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error al deserializar snapshot de resultados: {str(e)}"
        )

    report_data = ReportExportData(
        question=raw_data.get("question", audit_log.question_prompt),
        summary_text=raw_data.get("summary_text"),
        executive_report=raw_data.get("executive_report"),
        kpis=raw_data.get("kpis", []),
        gauges=raw_data.get("gauges", []),
        data_columns=raw_data.get("data_columns", []),
        data_rows=raw_data.get("data_rows", []),
        traceability=raw_data.get("traceability"),
        chart_image_base64=chart_image_base64,
        target_database=audit_log.target_database or "demo_corporativa.db"
    )

    return report_data, audit_log

@router.post("/export/pdf")
def export_pdf_report(
    report_in: ReportExportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> StreamingResponse:
    """
    Generates and streams a professional executive PDF document based on server-persisted audit snapshot.
    Available to the user who executed the query (or Admin).
    """
    report_data, audit_log = _resolve_report_data(
        audit_log_id=report_in.audit_log_id,
        current_user=current_user,
        chart_image_base64=report_in.chart_image_base64,
        db=db
    )

    try:
        pdf_bytes = ReportGeneratorService.generate_pdf(report_data)
    except Exception as e:
        logger.error(f"Error generando PDF: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generando documento PDF: {str(e)}"
        )

    _record_export_audit(
        db=db,
        user=current_user,
        question=report_data.question,
        export_format="PDF",
        target_database=report_data.target_database or "demo_corporativa.db",
        rows_count=len(report_data.data_rows)
    )

    filename = f"informe_ejecutivo_datia_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )

@router.post("/export/excel")
def export_excel_report(
    report_in: ReportExportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> StreamingResponse:
    """
    Generates and streams a multi-sheet structured Excel workbook based on server-persisted audit snapshot.
    Available to the user who executed the query (or Admin).
    """
    report_data, audit_log = _resolve_report_data(
        audit_log_id=report_in.audit_log_id,
        current_user=current_user,
        chart_image_base64=None,
        db=db
    )

    try:
        excel_bytes = ReportGeneratorService.generate_excel(report_data)
    except Exception as e:
        logger.error(f"Error generando Excel: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generando archivo Excel: {str(e)}"
        )

    _record_export_audit(
        db=db,
        user=current_user,
        question=report_data.question,
        export_format="EXCEL",
        target_database=report_data.target_database or "demo_corporativa.db",
        rows_count=len(report_data.data_rows)
    )

    filename = f"datos_datia_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"

    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )
