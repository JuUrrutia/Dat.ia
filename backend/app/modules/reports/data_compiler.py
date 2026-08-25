from typing import Union, List, Dict, Any
from app.modules.admin_catalog.schemas import ReportExportData, ReportExportRequest

class ReportDataCompiler:
    """
    Compiles and sanitizes dataset metrics, executive reports, and traceability details for export.
    """

    @classmethod
    def compile_summary_text(cls, data: Union[ReportExportData, ReportExportRequest]) -> str:
        if data.executive_report and data.executive_report.overview:
            return data.executive_report.overview
        if data.summary_text:
            return data.summary_text
        return "Se procesó la consulta satisfactoriamente sobre el esquema corporativo autorizado."

    @classmethod
    def compile_findings(cls, data: Union[ReportExportData, ReportExportRequest]) -> List[str]:
        findings = data.executive_report.key_findings if (data.executive_report and data.executive_report.key_findings) else []
        if not findings and data.data_rows:
            findings = [
                f"Se procesaron {len(data.data_rows)} registros de la base de datos activa.",
                f"Columnas analizadas: {', '.join(data.data_columns[:5])}."
            ]
        return findings

    @classmethod
    def compile_recommendations(cls, data: Union[ReportExportData, ReportExportRequest]) -> List[str]:
        return data.executive_report.recommendations if (data.executive_report and data.executive_report.recommendations) else []

    @classmethod
    def compile_columns(cls, data: Union[ReportExportData, ReportExportRequest]) -> List[str]:
        columns = data.data_columns
        if not columns and data.data_rows:
            columns = list(data.data_rows[0].keys())
        return columns or []
