import json
import datetime
from typing import Union, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.modules.auth.models import User
from app.modules.telemetry_audit.models import AuditLog
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
    def _audit_rows_returned(cls, data_obj: ReportExportData, original_rows: int) -> int:
        """Filas que devolvio la consulta, no las que se exportaron.

        `traceability.rows_returned` es la fuente (es lo que arma
        chat_engine/router.py:110). Si el snapshot no lo trae, o trae 0 pero el
        snapshot si tiene filas, gana el conteo real: auditar 0 sobre una consulta
        que devolvio 5000 filas es justamente el dato falsificado que se
        corrige aca.
        """
        if data_obj.traceability and data_obj.traceability.rows_returned:
            return data_obj.traceability.rows_returned
        return original_rows

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
            if not log_entry.result_snapshot:
                # ponytail: antes caia al `generate_pdf(req)` de abajo, que
                # reventaba con AttributeError -> 500. El log existe, pero sin
                # resultado: eso es 409, no un documento a medias.
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Esta consulta no tiene resultado exportable: el registro de auditoría no guardó snapshot de la respuesta."
                )
            try:
                data_dict = json.loads(log_entry.result_snapshot)
            except (TypeError, ValueError):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Esta consulta no tiene resultado exportable: el snapshot del registro de auditoría está corrupto."
                )
            if req.chart_image_base64:
                data_dict["chart_image_base64"] = req.chart_image_base64
            if req.custom_title:
                data_dict["question"] = req.custom_title
            if req.custom_notes:
                data_dict["custom_notes"] = req.custom_notes
            data_dict["include_raw_data"] = req.include_raw_data
            # ponytail: el audit graba lo que devolvio la consulta, no lo que se
            # exporto. include_raw_data=False vacia data_rows para el documento,
            # no para el registro de auditoria.
            original_rows = len(data_dict.get("data_rows") or [])
            if not req.include_raw_data:
                data_dict["data_rows"] = []
                data_dict["data_columns"] = []

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
                rows_returned=cls._audit_rows_returned(data_obj, original_rows),
                result_snapshot=log_entry.result_snapshot
            )
            db.add(export_audit)
            db.commit()
            filename = f"informe_ejecutivo_datia_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
            return pdf_bytes, filename

        # fail-closed: sin audit_log_id no hay documento. Antes caia en
        # generate_pdf(req) con un ReportExportRequest -> AttributeError -> 500.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Se requiere audit_log_id para exportar un informe."
        )

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
            if not log_entry.result_snapshot:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Esta consulta no tiene resultado exportable: el registro de auditoría no guardó snapshot de la respuesta."
                )
            try:
                data_dict = json.loads(log_entry.result_snapshot)
            except (TypeError, ValueError):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Esta consulta no tiene resultado exportable: el snapshot del registro de auditoría está corrupto."
                )
            if req.custom_title:
                data_dict["question"] = req.custom_title
            if req.custom_notes:
                data_dict["custom_notes"] = req.custom_notes
            data_dict["include_raw_data"] = req.include_raw_data
            original_rows = len(data_dict.get("data_rows") or [])
            if not req.include_raw_data:
                data_dict["data_rows"] = []
                data_dict["data_columns"] = []

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
                rows_returned=cls._audit_rows_returned(data_obj, original_rows),
                result_snapshot=log_entry.result_snapshot
            )
            db.add(export_audit)
            db.commit()
            filename = f"datos_datia_{datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
            return excel_bytes, filename

        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Se requiere audit_log_id para exportar un informe."
        )
