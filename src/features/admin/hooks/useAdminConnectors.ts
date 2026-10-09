import { useState } from 'react';
import { CorporateConnection, ConnectionTestResult, connectorService } from '../services/connector_service';

export function useAdminConnectors(connectors: CorporateConnection[]) {
  const [filterDbType, setFilterDbType] = useState<string>('ALL');
  const [testingId, setTestingId] = useState<number | null>(null);
  const [testResultsMap, setTestResultsMap] = useState<Record<number, ConnectionTestResult>>({});
  const [isUploadModalOpen, setIsUploadModalOpen] = useState(false);

  const handleTestCardConnection = async (conn: CorporateConnection) => {
    setTestingId(conn.id);
    const result = await connectorService.testConnection({
      name: conn.name,
      db_type: conn.db_type,
      host: conn.host,
      port: conn.port,
      database_name: conn.database_name,
      username: conn.username,
    });

    // Resultado real del servidor. No se maquilla un fallo como verificado.
    setTestingId(null);
    setTestResultsMap((prev) => ({ ...prev, [conn.id]: result }));
  };

  const filteredConnectors = connectors.filter(
    (c) => filterDbType === 'ALL' || c.db_type === filterDbType
  );

  return {
    filterDbType,
    setFilterDbType,
    testingId,
    testResultsMap,
    isUploadModalOpen,
    setIsUploadModalOpen,
    handleTestCardConnection,
    filteredConnectors,
  };
}
