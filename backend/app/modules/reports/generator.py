import json
import datetime
from typing import Union, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.models.audit_log import AuditLog
from app.modules.admin_catalog.schemas import ReportExportData, ReportExportRequest
from app.modules.reports.pdf_exporter import PDFExporter
from app.modules.reports.excel_exporter import ExcelExporter

class ReportGeneratorService:
    """
    Generates professional, presentation-ready PDF reports and structured Excel (.xlsx) workbooks.
    Handles audit_log_id lookup, permissions checking, and export audit logging.
    """

    @classmethod
    def generate_pdf(cls, data: Union[ReportExportData, ReportExportRequest]) -> bytes:
        return PDFExporter.generate_pdf(data)

    @classmethod
    def generate_excel(cls, data: Union[ReportExportData, ReportExportRequest]) -> bytes:
        return ExcelExporter.generate_excel(data)

    @classmethod
    def _resolve_user_role_name(cls, user: User) -> str:
        if hasattr(user, 'role_name') and user.role_name:
            return user.role_name
        if hasattr(user, 'role') and user.role and hasattr(user.role, 'name'):
            return user.role.name
        return "Administrador" if user.is_admin else "Usuario"

    @classmethod
    def export_pdf(cls, db: Session, current_user: User, req: ReportExportRequest) -> Tuple[bytes, str]:
        if req.audit_log_id:
            log_entry = db.query(AuditLog).filter(AuditLog.id == req.audit_log_id).first()
            if not log_entry:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Registro de auditoría no encontrado."
                )
            if not current_user.is_admin and log_entry.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permisos para exportar consultas de otro usuario."
                )
            if log_entry.result_snapshot:
                data_dict = json.loads(log_entry.result_snapshot)
                if req.chart_image_base64:
                    data_dict["chart_image_base64"] = req.chart_image_base64
                data_obj = ReportExportData(**data_dict)
                pdf_bytes = PDFExporter.generate_pdf(data_obj)

                export_audit = AuditLog(
                    user_id=current_user.id,
                    username=current_user.username,
                    user_role=cls._resolve_user_role_name(current_user),
                    question_prompt=data_obj.question,
                    sql_generated=data_obj.traceability.sql_executed if data_obj.traceability else None,
                    validation_status="EXPORTADO_PDF",
                    target_database=data_obj.target_database,
                    execution_time_ms=data_obj.traceability.execution_time_ms if data_obj.traceability else 0,
                    rows_returned=len(data_obj.data_rows),
                    result_snapshot=log_entry.result_snapshot
                )
                db.add(export_audit)
                db.commit()
                filename = f"informe_ejecutivo_datia_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
                return pdf_bytes, filename

        pdf_bytes = PDFExporter.generate_pdf(req)
        filename = f"informe_ejecutivo_datia_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
        return pdf_bytes, filename

    @classmethod
    def export_excel(cls, db: Session, current_user: User, req: ReportExportRequest) -> Tuple[bytes, str]:
        if req.audit_log_id:
            log_entry = db.query(AuditLog).filter(AuditLog.id == req.audit_log_id).first()
            if not log_entry:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Registro de auditoría no encontrado."
                )
            if not current_user.is_admin and log_entry.user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="No tienes permisos para exportar consultas de otro usuario."
                )
            if log_entry.result_snapshot:
                data_dict = json.loads(log_entry.result_snapshot)
                data_obj = ReportExportData(**data_dict)
                excel_bytes = ExcelExporter.generate_excel(data_obj)

                export_audit = AuditLog(
                    user_id=current_user.id,
                    username=current_user.username,
                    user_role=cls._resolve_user_role_name(current_user),
                    question_prompt=data_obj.question,
                    sql_generated=data_obj.traceability.sql_executed if data_obj.traceability else None,
                    validation_status="EXPORTADO_EXCEL",
                    target_database=data_obj.target_database,
                    execution_time_ms=data_obj.traceability.execution_time_ms if data_obj.traceability else 0,
                    rows_returned=len(data_obj.data_rows),
                    result_snapshot=log_entry.result_snapshot
                )
                db.add(export_audit)
                db.commit()
                filename = f"datos_datia_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
                return excel_bytes, filename

        excel_bytes = ExcelExporter.generate_excel(req)
        filename = f"datos_datia_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return excel_bytes, filename
