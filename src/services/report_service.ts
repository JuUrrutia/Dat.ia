import { apiClient } from './api_client';
import { QueryResult } from '../types';

export const reportService = {
  /**
   * Captures the rendered SVG/Canvas chart from the DOM into a high-resolution PNG Base64 string.
   */
  async captureChartAsBase64(): Promise<string | undefined> {
    try {
      const svgEl = document.querySelector('.echarts-for-react svg') as SVGElement | null;
      if (svgEl) {
        const svgString = new XMLSerializer().serializeToString(svgEl);
        const dataUri = 'data:image/svg+xml;base64,' + window.btoa(unescape(encodeURIComponent(svgString)));

        const img = new Image();
        const svgRect = svgEl.getBoundingClientRect();
        const width = Math.max(svgRect.width || 600, 600) * 2;
        const height = Math.max(svgRect.height || 360, 360) * 2;

        return new Promise<string | undefined>((resolve) => {
          img.onload = () => {
            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext('2d');
            if (ctx) {
              // Fill dark background for chart
              ctx.fillStyle = '#18181B';
              ctx.fillRect(0, 0, width, height);
              ctx.drawImage(img, 0, 0, width, height);
              const dataUrl = canvas.toDataURL('image/png');
              resolve(dataUrl);
            } else {
              resolve(undefined);
            }
          };
          img.onerror = () => {
            resolve(undefined);
          };
          img.src = dataUri;
        });
      }

      // Check for canvas fallback
      const canvasEl = document.querySelector('.echarts-for-react canvas') as HTMLCanvasElement | null;
      if (canvasEl) {
        return canvasEl.toDataURL('image/png');
      }

      return undefined;
    } catch {
      return undefined;
    }
  },

  async exportExecutiveReportPdf(result: QueryResult | { audit_log_id?: number }, chartBase64?: string): Promise<void> {
    const auditId = (result as any).audit_log_id || (result as QueryResult).traceability?.audit_log_id;
    if (!auditId) {
      throw new Error('No se encontró el identificador de auditoría para generar la exportación.');
    }

    const payload = {
      audit_log_id: auditId,
      chart_image_base64: chartBase64,
    };

    const res = await apiClient.post('/reports/export/pdf', payload, {
      responseType: 'blob',
    });

    const blob = new Blob([res.data], { type: 'application/pdf' });
    const url = window.URL.createObjectURL(blob);
    try {
      const link = document.createElement('a');
      link.href = url;
      const nowStr = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
      link.setAttribute('download', `informe_ejecutivo_datia_${nowStr}.pdf`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } finally {
      window.URL.revokeObjectURL(url);
    }
  },

  async exportExecutiveReportExcel(result: QueryResult | { audit_log_id?: number }): Promise<void> {
    const auditId = (result as any).audit_log_id || (result as QueryResult).traceability?.audit_log_id;
    if (!auditId) {
      throw new Error('No se encontró el identificador de auditoría para generar la exportación.');
    }

    const payload = {
      audit_log_id: auditId,
    };

    const res = await apiClient.post('/reports/export/excel', payload, {
      responseType: 'blob',
    });

    const blob = new Blob([res.data], {
      type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    });
    const url = window.URL.createObjectURL(blob);
    try {
      const link = document.createElement('a');
      link.href = url;
      const nowStr = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
      link.setAttribute('download', `datos_datia_${nowStr}.xlsx`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } finally {
      window.URL.revokeObjectURL(url);
    }
  },
};
