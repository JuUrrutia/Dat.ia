import React, { useState, useEffect, useRef } from 'react';
import { ShieldAlert, Users, Database, BookOpen, Plus, Edit3, Trash2, RefreshCw, CheckCircle2 } from 'lucide-react';
import { CorporateConnection, connectorService, ConnectionTestResult } from '../services/connector_service';
import { ConnectorModal } from '../components/admin/ConnectorModal';
import { AdminUsersTab } from '../components/admin/AdminUsersTab';
import { AdminCatalogTab } from '../components/admin/AdminCatalogTab';

const MOCK_USERS = [
  { id: 1, name: 'admin', email: 'admin@empresa.com', role: 'Administrador', is_admin: true },
  { id: 2, name: 'felipe_economista', email: 'felipe@empresa.com', role: 'Economista', is_admin: false },
  { id: 3, name: 'juan_ti', email: 'juan@empresa.com', role: 'TI', is_admin: false },
  { id: 4, name: 'nuevo_usuario', email: 'usuario@empresa.com', role: 'Usuario (Inicial)', is_admin: false },
];

const MOCK_CATALOG = [
  { table: 'fact_ventas', column: 'monto_total', desc: 'Monto bruto en USD antes de impuestos', formula: 'SUM(precio_unitario * cantidad)', is_ai: true },
  { table: 'fact_ventas', column: 'costo_total', desc: 'Costo de venta directo asociado', formula: 'SUM(costo_unitario * cantidad)', is_ai: true },
  { table: 'dim_clientes', column: 'rut_dni_cliente', desc: 'Documento personal cliente (ENMASCARADO)', formula: 'MASKED / HASH', is_ai: false },
  { table: 'fact_incidentes_ti', column: 'horas_resolucion', desc: 'Tiempo de resolución en horas SLA', formula: 'AVG(horas_resolucion)', is_ai: true },
];

export const AdminPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'users' | 'connectors' | 'catalog'>('connectors');

  // Connectors State
  const [connectors, setConnectors] = useState<CorporateConnection[]>([]);
  const isLoadingConnectorsRef = useRef(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingConnector, setEditingConnector] = useState<CorporateConnection | null>(null);

  const [testingId, setTestingId] = useState<number | null>(null);
  const [testResultsMap, setTestResultsMap] = useState<Record<number, ConnectionTestResult>>({});

  const [aiEnriching, setAiEnriching] = useState(false);
  const [aiSuccess, setAiSuccess] = useState(false);

  // Load Connectors
  const fetchConnectors = async () => {
    isLoadingConnectorsRef.current = true;
    try {
      const data = await connectorService.getConnectors();
      setConnectors(data);
    } catch {
      // Handled in connectorService fallback
    } finally {
      isLoadingConnectorsRef.current = false;
    }
  };

  useEffect(() => {
    fetchConnectors();
  }, []);

  const handleOpenCreateModal = () => {
    setEditingConnector(null);
    setIsModalOpen(true);
  };

  const handleOpenEditModal = (conn: CorporateConnection) => {
    setEditingConnector(conn);
    setIsModalOpen(true);
  };

  const handleDeleteConnector = async (id: number, name: string) => {
    if (!window.confirm(`¿Estás seguro de eliminar la conexión BD '${name}'?`)) return;
    try {
      await connectorService.deleteConnector(id);
      fetchConnectors();
    } catch (err: any) {
      alert(err.response?.data?.detail || 'Error al eliminar la conexión.');
    }
  };

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
    setTestingId(null);
    setTestResultsMap((prev) => ({ ...prev, [conn.id]: result }));
  };

  const handleRunAiCatalog = () => {
    setAiEnriching(true);
    setTimeout(() => {
      setAiEnriching(false);
      setAiSuccess(true);
      setTimeout(() => setAiSuccess(false), 3000);
    }, 1500);
  };

  return (
    <div className="flex-1 bg-dark-base overflow-y-auto p-6 space-y-6">
      {/* Header Banner */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <ShieldAlert className="w-5 h-5 text-purple-400" /> Panel de Gobernanza & Fuentes BD Corporativas
          </h1>
          <p className="text-xs text-gray-400">
            Administración de conexiones a PostgreSQL, SQL Server, MySQL y Oracle con cifrado AES-256
          </p>
        </div>
      </div>

      {/* Navigation Tabs */}
      <div className="flex items-center space-x-2 border-b border-dark-border pb-1">
        <button
          onClick={() => setActiveTab('connectors')}
          className={`flex items-center space-x-2 px-4 py-2 text-xs font-medium border-b-2 transition-colors ${
            activeTab === 'connectors' ? 'border-purple-500 text-purple-400 font-semibold' : 'border-transparent text-gray-400 hover:text-white'
          }`}
        >
          <Database className="w-4 h-4" />
          <span>Fuentes BD Corporativas ({connectors.length})</span>
        </button>

        <button
          onClick={() => setActiveTab('users')}
          className={`flex items-center space-x-2 px-4 py-2 text-xs font-medium border-b-2 transition-colors ${
            activeTab === 'users' ? 'border-purple-500 text-purple-400 font-semibold' : 'border-transparent text-gray-400 hover:text-white'
          }`}
        >
          <Users className="w-4 h-4" />
          <span>Usuarios & Asignación de Roles</span>
        </button>

        <button
          onClick={() => setActiveTab('catalog')}
          className={`flex items-center space-x-2 px-4 py-2 text-xs font-medium border-b-2 transition-colors ${
            activeTab === 'catalog' ? 'border-purple-500 text-purple-400 font-semibold' : 'border-transparent text-gray-400 hover:text-white'
          }`}
        >
          <BookOpen className="w-4 h-4" />
          <span>Catálogo Semántico (IA)</span>
        </button>
      </div>

      {/* Tab 1: Corporate DB Connectors */}
      {activeTab === 'connectors' && (
        <div className="glass-panel rounded-2xl p-6 border border-white/10 space-y-5">
          <div className="flex items-center justify-between border-b border-dark-border pb-4">
            <div>
              <h3 className="text-sm font-semibold text-white">Fuentes de Datos Corporativas Registradas</h3>
              <p className="text-xs text-gray-400">Conexiones operativas en modo Solo Lectura (`READ ONLY`)</p>
            </div>

            <button
              onClick={handleOpenCreateModal}
              className="flex items-center space-x-1.5 text-xs bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-medium px-4 py-2 rounded-xl shadow-lg shadow-purple-600/30 transition-colors"
            >
              <Plus className="w-4 h-4" />
              <span>Registrar Nueva BD Corporativa</span>
            </button>
          </div>

          {/* Connectors Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {connectors.map((c) => {
              const testRes = testResultsMap[c.id];
              return (
                <div key={c.id} className="glass-card p-5 rounded-2xl border border-white/10 space-y-4 hover:border-purple-500/30 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <div className="font-bold text-white text-sm flex items-center space-x-2">
                        <span>{c.name}</span>
                        <span className="text-[10px] bg-purple-500/10 text-purple-400 border border-purple-500/20 px-2 py-0.5 rounded font-mono uppercase">
                          {c.db_type}
                        </span>
                      </div>
                      <div className="text-xs text-gray-400 flex items-center space-x-2">
                        <span>Host: <span className="text-gray-200 font-mono">{c.host}:{c.port}</span></span>
                        <span>•</span>
                        <span>BD: <span className="text-gray-200 font-mono">{c.database_name}</span></span>
                      </div>
                    </div>

                    <div className="flex items-center space-x-1">
                      <button
                        onClick={() => handleOpenEditModal(c)}
                        title="Editar Conexión"
                        className="p-2 rounded-lg text-gray-400 hover:text-brand-400 hover:bg-brand-500/10 border border-transparent hover:border-brand-500/20 transition-colors"
                      >
                        <Edit3 className="w-3.5 h-3.5" />
                      </button>

                      <button
                        onClick={() => handleDeleteConnector(c.id, c.name)}
                        title="Eliminar Conexión"
                        className="p-2 rounded-lg text-gray-400 hover:text-rose-400 hover:bg-rose-500/10 border border-transparent hover:border-rose-500/20 transition-colors"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>

                  <div className="flex items-center justify-between text-xs pt-2 border-t border-dark-border/60">
                    <div className="flex items-center space-x-2">
                      <span className={`w-2 h-2 rounded-full ${c.is_active ? 'bg-emerald-400' : 'bg-gray-500'}`} />
                      <span className="text-gray-400">{c.is_active ? 'Activa para Consultas' : 'Inactiva'}</span>
                    </div>

                    <button
                      onClick={() => handleTestCardConnection(c)}
                      disabled={testingId === c.id}
                      className="flex items-center space-x-1 text-xs text-brand-400 hover:text-brand-300 bg-brand-500/10 hover:bg-brand-500/20 border border-brand-500/20 px-3 py-1 rounded-lg transition-colors"
                    >
                      <RefreshCw className={`w-3.5 h-3.5 ${testingId === c.id ? 'animate-spin' : ''}`} />
                      <span>{testingId === c.id ? 'Probando...' : 'Probar Red'}</span>
                    </button>
                  </div>

                  {testRes && (
                    <div
                      className={`p-2.5 rounded-xl border text-[11px] flex items-center space-x-2 animate-fadeIn ${
                        testRes.success
                          ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                          : 'bg-rose-500/10 border-rose-500/20 text-rose-400'
                      }`}
                    >
                      <CheckCircle2 className="w-3.5 h-3.5 shrink-0" />
                      <span className="truncate">{testRes.message}</span>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Tab 2: Users & Roles */}
      {activeTab === 'users' && <AdminUsersTab users={MOCK_USERS} />}

      {/* Tab 3: Semantic Catalog */}
      {activeTab === 'catalog' && (
        <AdminCatalogTab
          catalog={MOCK_CATALOG}
          aiEnriching={aiEnriching}
          aiSuccess={aiSuccess}
          onRunAiCatalog={handleRunAiCatalog}
        />
      )}

      {/* Modal for Creating & Editing Connection */}
      <ConnectorModal
        isOpen={isModalOpen}
        editingConnector={editingConnector}
        onClose={() => setIsModalOpen(false)}
        onSaveSuccess={fetchConnectors}
      />
    </div>
  );
};
