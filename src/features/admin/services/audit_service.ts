import { apiClient } from '../../../shared/api/api_client';
import { AuditLogsPage, AuditFilterParams } from '../../../types';

export const auditService = {
  async getAuditLogs(params?: AuditFilterParams): Promise<AuditLogsPage> {
    const res = await apiClient.get<AuditLogsPage>('/audit', { params });
    return res.data;
  },

  async exportAuditLogsCsv(params?: AuditFilterParams): Promise<void> {
    const res = await apiClient.get('/audit/export', {
      params,
      responseType: 'blob',
    });

    const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    const nowStr = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    link.setAttribute('download', `datia_audit_logs_${nowStr}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },
};
