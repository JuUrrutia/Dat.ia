import { useState, useEffect, useCallback } from 'react';
import { auditService } from '../../../services/audit_service';
import { AuditLog, AuditFilterParams } from '../../../types';

export function useAdminAudit() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [loading, setLoading] = useState<boolean>(false);
  const [exporting, setExporting] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Filters state
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [filterUsername, setFilterUsername] = useState<string>('');
  const [filterDatabase, setFilterDatabase] = useState<string>('');
  const [filterStatus, setFilterStatus] = useState<string>('');

  // Selected Log for Inspector Modal
  const [selectedLog, setSelectedLog] = useState<AuditLog | null>(null);

  const fetchLogs = useCallback(async (targetPage: number = 1) => {
    setLoading(true);
    setError(null);
    try {
      const params: AuditFilterParams = {
        page: targetPage,
        page_size: 20,
        start_date: startDate ? new Date(startDate).toISOString() : undefined,
        end_date: endDate ? new Date(endDate).toISOString() : undefined,
        username: filterUsername.trim() || undefined,
        target_database: filterDatabase.trim() || undefined,
        validation_status: filterStatus || undefined,
      };

      const res = await auditService.getAuditLogs(params);
      setLogs(res.items);
      setTotal(res.total);
      setPage(res.page);
      setTotalPages(res.total_pages);
    } catch {
      setError('No se pudieron cargar los registros de auditoría.');
    } finally {
      setLoading(false);
    }
  }, [startDate, endDate, filterUsername, filterDatabase, filterStatus]);

  useEffect(() => {
    fetchLogs(1);
  }, [fetchLogs]);

  const handleFilterSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchLogs(1);
  };

  const handleClearFilters = () => {
    setStartDate('');
    setEndDate('');
    setFilterUsername('');
    setFilterDatabase('');
    setFilterStatus('');
  };

  const handleExportCsv = async () => {
    setExporting(true);
    try {
      const params: AuditFilterParams = {
        start_date: startDate ? new Date(startDate).toISOString() : undefined,
        end_date: endDate ? new Date(endDate).toISOString() : undefined,
        username: filterUsername.trim() || undefined,
        target_database: filterDatabase.trim() || undefined,
        validation_status: filterStatus || undefined,
      };
      await auditService.exportAuditLogsCsv(params);
    } catch {
      alert('Error al exportar archivo CSV de auditoría.');
    } finally {
      setExporting(false);
    }
  };

  return {
    logs,
    total,
    page,
    totalPages,
    loading,
    exporting,
    error,
    startDate,
    endDate,
    filterUsername,
    filterDatabase,
    filterStatus,
    selectedLog,
    setSelectedLog,
    setStartDate,
    setEndDate,
    setFilterUsername,
    setFilterDatabase,
    setFilterStatus,
    fetchLogs,
    handleFilterSubmit,
    handleClearFilters,
    handleExportCsv,
  };
}
