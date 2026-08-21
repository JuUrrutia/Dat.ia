import io
import datetime
import logging
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.audit_log import AuditLog
from app.schemas.report_schema import ReportExportRequest
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

@router.post("/export/pdf")
def export_pdf_report(
    report_in: ReportExportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> StreamingResponse:
    """
    Generates and streams a professional executive PDF document based on pre-computed query results.
    Available to any authenticated user for their active results.
    """
    try:
        pdf_bytes = ReportGeneratorService.generate_pdf(report_in)
    except Exception as e:
        logger.error(f"Error generando PDF: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generando documento PDF: {str(e)}"
        )

    _record_export_audit(
        db=db,
        user=current_user,
        question=report_in.question,
        export_format="PDF",
        target_database=report_in.target_database or "demo_corporativa.db",
        rows_count=len(report_in.data_rows)
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
    Generates and streams a multi-sheet structured Excel workbook (Executive Summary + Data Table).
    Available to any authenticated user.
    """
    try:
        excel_bytes = ReportGeneratorService.generate_excel(report_in)
    except Exception as e:
        logger.error(f"Error generando Excel: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error generando archivo Excel: {str(e)}"
        )

    _record_export_audit(
        db=db,
        user=current_user,
        question=report_in.question,
        export_format="EXCEL",
        target_database=report_in.target_database or "demo_corporativa.db",
        rows_count=len(report_in.data_rows)
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
