import io
import base64
import datetime
from typing import Union
from xml.sax.saxutils import escape
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether, HRFlowable

from app.modules.admin_catalog.schemas import ReportExportData, ReportExportRequest
from app.modules.reports.data_compiler import ReportDataCompiler

class PDFExporter:
    """
    Generates presentation-ready executive PDF reports using ReportLab.
    """

    # Cuantas tarjetas de KPI entran por fila. Los KPIs NO se truncan: si hay mas
    # que esto se agregan filas (el PDF no puede mostrar un subconjunto distinto
    # del que muestra el Excel sin decirlo).
    KPI_COLS_PER_ROW = 4

    @classmethod
    def generate_pdf(cls, data: Union[ReportExportData, ReportExportRequest]) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=36,
            rightMargin=36,
            topMargin=36,
            bottomMargin=36
        )

        styles = getSampleStyleSheet()

        COLOR_PRIMARY = colors.HexColor("#312E81")
        COLOR_ACCENT = colors.HexColor("#4F46E5")
        COLOR_DARK = colors.HexColor("#0F172A")
        COLOR_MUTED = colors.HexColor("#64748B")
        COLOR_BG_LIGHT = colors.HexColor("#F8FAFC")
        COLOR_BORDER = colors.HexColor("#E2E8F0")

        title_style = ParagraphStyle(
            'DocTitle', parent=styles['Heading1'],
            fontName='Helvetica-Bold', fontSize=18, leading=22,
            textColor=COLOR_PRIMARY, spaceAfter=4
        )

        subtitle_style = ParagraphStyle(
            'DocSubTitle', parent=styles['Normal'],
            fontName='Helvetica', fontSize=9, leading=12,
            textColor=COLOR_MUTED, spaceAfter=10
        )

        section_heading = ParagraphStyle(
            'SectionHeading', parent=styles['Heading2'],
            fontName='Helvetica-Bold', fontSize=11, leading=14,
            textColor=COLOR_ACCENT, spaceBefore=8, spaceAfter=4
        )

        body_style = ParagraphStyle(
            'BodyDark', parent=styles['Normal'],
            fontName='Helvetica', fontSize=9, leading=13,
            textColor=COLOR_DARK
        )

        sql_code_style = ParagraphStyle(
            'SqlCode', parent=styles['Code'],
            fontName='Courier', fontSize=8, leading=11,
            textColor=COLOR_PRIMARY
        )

        story = []

        # La numeracion de secciones deriva de lo que se imprime, no de lo que se
        # intento imprimir: si un chart no se pudo renderizar, el informe no deja
        # un hueco entre la seccion 3 y la siguiente.
        section_no = 0

        def section(title: str) -> Paragraph:
            nonlocal section_no
            section_no += 1
            return Paragraph(f"{section_no}. {title}", section_heading)

        def kpi_row_table(cells: list, n_cols: int) -> Table:
            table = Table([cells], colWidths=[540 / n_cols] * n_cols)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_LIGHT),
                ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            return table

        # 1. Header Banner
        header_table = Table(
            [
                [
                    Paragraph("<b>DATIA</b> | Executive Analytics", title_style),
                    Paragraph(f"<b>Fecha:</b> {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}<br/><b>BD:</b> {escape(ReportDataCompiler.compile_db_name(data))}", subtitle_style)
                ]
            ],
            colWidths=[360, 180]
        )
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))
        story.append(header_table)
        story.append(HRFlowable(width="100%", thickness=1.5, color=COLOR_ACCENT, spaceBefore=4, spaceAfter=8))

        # 2. Question / Prompt Box
        # ponytail: todo dato (usuario o LLM) va con escape(). El markup lo pone
        # el template, nunca el dato: si no, '<b>ALTAS</b>' desaparece del PDF y
        # '<img src=y>' lo revienta con ValueError -> 500.
        question_p = Paragraph(f"<b>Consulta Analizada:</b> <i>\"{escape(str(data.question))}\"</i>", body_style)
        q_table = Table([[question_p]], colWidths=[540])
        q_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_LIGHT),
            ('BOX', (0, 0), (-1, -1), 0.75, COLOR_BORDER),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(q_table)
        story.append(Spacer(1, 8))

        # 2b. Custom Notes (if provided)
        if getattr(data, 'custom_notes', None):
            notes_p = Paragraph(f"<b>Notas Ejecutivas & Contexto:</b><br/>{escape(str(data.custom_notes))}", body_style)
            notes_table = Table([[notes_p]], colWidths=[540])
            notes_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#EEF2FF")),
                ('BOX', (0, 0), (-1, -1), 0.75, colors.HexColor("#C7D2FE")),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ]))
            story.append(notes_table)
            story.append(Spacer(1, 8))

        # 3. KPI Cards Grid
        if data.kpis:
            pending = []
            for k in data.kpis:
                cell_content = [
                    Paragraph(f"<font size=7 color='#64748B'><b>{escape(k.title.upper())}</b></font>", body_style),
                    Spacer(1, 2),
                    Paragraph(f"<font size=13 color='#312E81'><b>{escape(str(k.value))}</b></font>", body_style)
                ]
                if k.subtitle:
                    cell_content.append(Paragraph(f"<font size=7 color='#94A3B8'>{escape(str(k.subtitle))}</font>", body_style))
                pending.append(cell_content)
                if len(pending) == cls.KPI_COLS_PER_ROW:
                    story.append(kpi_row_table(pending, cls.KPI_COLS_PER_ROW))
                    story.append(Spacer(1, 4))
                    pending = []
            if pending:
                story.append(kpi_row_table(pending, len(pending)))
            story.append(Spacer(1, 8))

        # 4. Diagnóstico & Contexto General
        story.append(section("Diagnóstico & Contexto General"))
        overview_text = ReportDataCompiler.compile_summary_text(data)

        risk_badge = ""
        if data.executive_report and data.executive_report.risk_level:
            risk_badge = f" [Nivel de Riesgo: <b>{escape(str(data.executive_report.risk_level))}</b>]"

        diag_content = [Paragraph(f"{escape(overview_text)}{risk_badge}", body_style)]
        if data.executive_report and data.executive_report.business_impact:
            diag_content.append(Spacer(1, 4))
            diag_content.append(Paragraph(f"<b>Impacto en el Negocio:</b> {escape(str(data.executive_report.business_impact))}", body_style))

        diag_table = Table([[diag_content]], colWidths=[540])
        diag_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_LIGHT),
            ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        story.append(diag_table)
        story.append(Spacer(1, 8))

        # 5. Hallazgos Clave
        findings = ReportDataCompiler.compile_findings(data)
        if findings:
            story.append(section("Hallazgos Clave & Puntos Críticos"))
            findings_data = [[Paragraph(f"• {escape(str(f))}", body_style)] for f in findings]
            findings_table = Table(findings_data, colWidths=[540])
            findings_table.setStyle(TableStyle([
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(findings_table)
            story.append(Spacer(1, 6))

        # 6. Recomendaciones Estratégicas
        recommendations = ReportDataCompiler.compile_recommendations(data)
        if recommendations:
            story.append(section("Recomendaciones Estratégicas Accionables"))
            recs_data = [[Paragraph(f"<b>{i}.</b> {escape(str(r))}", body_style)] for i, r in enumerate(recommendations, 1)]
            recs_table = Table(recs_data, colWidths=[540])
            recs_table.setStyle(TableStyle([
                ('TOPPADDING', (0, 0), (-1, -1), 2),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
                ('LEFTPADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(recs_table)
            story.append(Spacer(1, 6))

        # 7. Chart Image
        if data.chart_image_base64:
            chart_img = None
            try:
                img_data_str = data.chart_image_base64
                if "," in img_data_str:
                    img_data_str = img_data_str.split(",", 1)[1]
                chart_img = Image(io.BytesIO(base64.b64decode(img_data_str)), width=500, height=200)
                chart_img.hAlign = 'CENTER'
            except Exception:
                chart_img = None

            story.append(section("Visualización Analítica"))
            if chart_img is not None:
                story.append(KeepTogether([chart_img, Spacer(1, 6)]))
            else:
                # ponytail: no se pierde en silencio. Antes el `except: pass`
                # dejaba el informe sin figura y con un hueco en la numeracion.
                story.append(Paragraph("Imagen no disponible: el gráfico no pudo incrustarse en este informe.", body_style))
                story.append(Spacer(1, 6))

        # 8. Technical Traceability
        trace = data.traceability
        story.append(section("Trazabilidad Técnica & Gobernanza"))

        val_status = (trace.validation_status if trace else None) or ReportDataCompiler.SIN_VALIDACION
        rows_ret = trace.rows_returned if trace else None
        exec_ms = trace.execution_time_ms if trace else None
        rows_txt = ReportDataCompiler.SIN_DATO if rows_ret is None else str(rows_ret)
        ms_txt = ReportDataCompiler.SIN_DATO if exec_ms is None else f"{exec_ms} ms"

        trace_meta_p = Paragraph(
            f"<b>Estado AST:</b> {escape(val_status)} | <b>Filas:</b> {rows_txt} | <b>Latencia:</b> {ms_txt}",
            body_style
        )

        trace_cells = [[trace_meta_p]]
        if trace and trace.sql_executed:
            sql_p = Paragraph(f"<b>SQL Validado:</b><br/>{escape(str(trace.sql_executed))}", sql_code_style)
            trace_cells.append([sql_p])

        trace_table = Table(trace_cells, colWidths=[540])
        trace_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_LIGHT),
            ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(trace_table)

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
