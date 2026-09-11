import io
import base64
import datetime
from typing import Union
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

        # 1. Header Banner
        header_table = Table(
            [
                [
                    Paragraph("<b>DATIA</b> | Executive Analytics", title_style),
                    Paragraph(f"<b>Fecha:</b> {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}<br/><b>BD:</b> {data.target_database or 'SQLite Demo'}", subtitle_style)
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
        question_p = Paragraph(f"<b>Consulta Analizada:</b> <i>\"{data.question}\"</i>", body_style)
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

        # 3. KPI Cards Grid
        if data.kpis:
            kpi_cols = min(len(data.kpis), 4)
            col_w = 540 / kpi_cols
            kpi_cells = []
            for k in data.kpis[:kpi_cols]:
                cell_content = [
                    Paragraph(f"<font size=7 color='#64748B'><b>{k.title.upper()}</b></font>", body_style),
                    Spacer(1, 2),
                    Paragraph(f"<font size=13 color='#312E81'><b>{k.value}</b></font>", body_style)
                ]
                if k.subtitle:
                    cell_content.append(Paragraph(f"<font size=7 color='#94A3B8'>{k.subtitle}</font>", body_style))
                kpi_cells.append(cell_content)

            kpi_table = Table([kpi_cells], colWidths=[col_w] * kpi_cols)
            kpi_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, -1), COLOR_BG_LIGHT),
                ('BOX', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ('INNERGRID', (0, 0), (-1, -1), 0.5, COLOR_BORDER),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
                ('LEFTPADDING', (0, 0), (-1, -1), 8),
                ('RIGHTPADDING', (0, 0), (-1, -1), 8),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ]))
            story.append(kpi_table)
            story.append(Spacer(1, 8))

        # 4. Diagnóstico & Contexto General
        story.append(Paragraph("1. Diagnóstico & Contexto General", section_heading))
        overview_text = ReportDataCompiler.compile_summary_text(data)

        risk_badge = ""
        if data.executive_report and data.executive_report.risk_level:
            risk_badge = f" [Nivel de Riesgo: <b>{data.executive_report.risk_level}</b>]"

        diag_content = [Paragraph(f"{overview_text}{risk_badge}", body_style)]
        if data.executive_report and data.executive_report.business_impact:
            diag_content.append(Spacer(1, 4))
            diag_content.append(Paragraph(f"<b>Impacto en el Negocio:</b> {data.executive_report.business_impact}", body_style))

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
            story.append(Paragraph("2. Hallazgos Clave & Puntos Críticos", section_heading))
            findings_data = [[Paragraph(f"• {f}", body_style)] for f in findings]
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
            story.append(Paragraph("3. Recomendaciones Estratégicas Accionables", section_heading))
            recs_data = [[Paragraph(f"<b>{i}.</b> {r}", body_style)] for i, r in enumerate(recommendations, 1)]
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
            try:
                img_data_str = data.chart_image_base64
                if "," in img_data_str:
                    img_data_str = img_data_str.split(",", 1)[1]
                img_bytes = base64.b64decode(img_data_str)
                img_stream = io.BytesIO(img_bytes)

                chart_img = Image(img_stream, width=500, height=200)
                chart_img.hAlign = 'CENTER'

                chart_block = [
                    Paragraph("4. Visualización Analítica", section_heading),
                    chart_img,
                    Spacer(1, 6)
                ]
                story.append(KeepTogether(chart_block))
            except Exception:
                pass

        # 8. Technical Traceability
        trace = data.traceability
        trace_title = "4. Trazabilidad Técnica & Gobernanza" if not data.chart_image_base64 else "5. Trazabilidad Técnica & Gobernanza"
        story.append(Paragraph(trace_title, section_heading))

        val_status = trace.validation_status if trace else "APROBADO"
        rows_ret = trace.rows_returned if trace else len(data.data_rows)
        exec_ms = trace.execution_time_ms if trace else 0

        trace_meta_p = Paragraph(
            f"<b>Estado AST:</b> {val_status} | <b>Filas:</b> {rows_ret} | <b>Latencia:</b> {exec_ms} ms",
            body_style
        )

        trace_cells = [[trace_meta_p]]
        if trace and trace.sql_executed:
            sql_p = Paragraph(f"<b>SQL Validado:</b><br/>{trace.sql_executed}", sql_code_style)
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
