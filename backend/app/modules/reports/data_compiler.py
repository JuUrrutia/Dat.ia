from typing import Union, List
from app.modules.admin_catalog.schemas import ReportExportData, ReportExportRequest

class ReportDataCompiler:
    """
    Compiles and sanitizes dataset metrics, executive reports, and traceability details for export.
    """

    # ponytail: un unico lugar para "no lo se". Ningun export de este modulo puede
    # afirmar un resultado que no tiene dato de respaldo.
    SIN_DATO = "No disponible"
    SIN_VALIDACION = "Sin registro de validación"

    @classmethod
    def compile_summary_text(cls, data: Union[ReportExportData, ReportExportRequest]) -> str:
        if data.executive_report and data.executive_report.overview:
            return data.executive_report.overview
        if data.summary_text:
            return data.summary_text
        # ponytail: sin resumen no se inventa exito. Antes decia "se procesó
        # satisfactoriamente sobre el esquema corporativo autorizado".
        return "No hay resumen disponible para esta consulta."

    @classmethod
    def compile_db_name(cls, data: Union[ReportExportData, ReportExportRequest]) -> str:
        """Nombre real de la base. Nunca se inventa: si no viene, 'No disponible'."""
        return getattr(data, "target_database", None) or cls.SIN_DATO

    @classmethod
    def compile_trace_line(cls, data: Union[ReportExportData, ReportExportRequest]) -> str:
        """Linea de trazabilidad sin defaults que affirmen un resultado."""
        trace = data.traceability
        status = (trace.validation_status if trace else None) or cls.SIN_VALIDACION
        rows = trace.rows_returned if trace else None
        ms = trace.execution_time_ms if trace else None
        return (
            f"Estado AST: {status} | "
            f"Filas: {cls.SIN_DATO if rows is None else rows} | "
            f"Latencia: {cls.SIN_DATO if ms is None else f'{ms} ms'}"
        )

    @classmethod
    def compile_findings(cls, data: Union[ReportExportData, ReportExportRequest]) -> List[str]:
        findings = data.executive_report.key_findings if (data.executive_report and data.executive_report.key_findings) else []
        if not findings and data.data_rows:
            findings = [
                f"Se procesaron {len(data.data_rows)} registros de la base de datos activa.",
                f"Columnas analizadas: {', '.join(data.data_columns[:5])}."
            ]
        if not findings and getattr(data, "include_raw_data", True) is False:
            # ponytail: con include_raw_data=False `generator.py` vacia data_rows
            # ANTES de compilar. Devolver [] hacia que el informe presentara "sin
            # hallazgos" cuando los hallazgos nunca se calcularon: dos entregables
            # del mismo dato con contenido distinto y sin declaracion. Se declara
            # la ausencia en vez de fingir un analisis sin filas.
            return [
                "No se incluyen hallazgos: este informe se generó con "
                "include_raw_data=False, por lo que los datos crudos de la consulta "
                "no se exportaron y no se corrió ningún análisis sobre ellos. "
                "El informe ejecutivo con hallazgos requiere include_raw_data=True."
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
