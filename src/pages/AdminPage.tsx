import React, { useState, useEffect } from 'react';
import { ShieldAlert, Users, Database, BookOpen, Server, Key, FileText, Sparkles } from 'lucide-react';
import { CorporateConnection, connectorService, DEFAULT_CONNECTORS } from '../features/admin/services/connector_service';
import { AdminAuditTab } from '../components/admin/AdminAuditTab';
import { AdminCatalogTab } from '../components/admin/AdminCatalogTab';
import { AdminConnectorsTab } from '../components/admin/AdminConnectorsTab';
import { AdminUsersTab } from '../components/admin/AdminUsersTab';
import { ConnectorModal } from '../components/admin/ConnectorModal';
import { authService } from '../features/auth/services/auth_service';
import { User } from '../types';

export const AdminPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'connectors' | 'users' | 'catalog' | 'audit'>('connectors');

  // Connectors State
  const [connectors, setConnectors] = useState<CorporateConnection[]>(DEFAULT_CONNECTORS);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingConnector, setEditingConnector] = useState<CorporateConnection | null>(null);

  // Users State
  const [dbUsers, setDbUsers] = useState<Array<{ id: number; name: string; username?: string; email: string; role: string; is_admin: boolean }>>([]);

  const fetchUsers = async () => {
    try {
      const usersData: User[] = await authService.getUsers();
      if (usersData && usersData.length > 0) {
        setDbUsers(
          usersData.map((u) => ({
            id: u.id,
            name: u.username,
            username: u.username,
            email: u.email || `${u.username}@empresa.com`,
            role: u.role_name || (u.is_admin ? 'Administrador' : 'Usuario'),
            is_admin: u.is_admin,
          }))
        );
      }
    } catch {
      // Use fallback
    }
  };

  const fetchConnectors = async () => {
    try {
      const data = await connectorService.getConnectors();
      setConnectors(data && data.length > 0 ? data : DEFAULT_CONNECTORS);
    } catch {
      setConnectors(DEFAULT_CONNECTORS);
    }
  };

  useEffect(() => {
    fetchConnectors();
    fetchUsers();
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
    if (!window.confirm(`¿Estás seguro de eliminar la fuente de datos BD '${name}'?`)) return;
    try {
      await connectorService.deleteConnector(id);
    } catch {
      // Ignore API errors and fallback to local state removal
    }
    setConnectors((prev) => prev.filter((c) => c.id !== id));
  };

  const handleToggleActive = async (id: number) => {
    const updated = await connectorService.toggleActive(id);
    setConnectors(updated);
  };

  const handleResetDemoConnectors = () => {
    const reset = connectorService.resetConnectors();
    setConnectors(reset);
  };

  const activeCount = connectors.filter((c) => c.is_active).length;

  return (
    <div className="w-full h-full flex-1 bg-dark-base overflow-y-auto p-4 sm:p-6 space-y-6 custom-scrollbar pb-28 font-sans">
      {/* Header Banner */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 glass-panel p-5 rounded-2xl border border-white/10 shadow-2xl">
        <div className="flex items-center space-x-3.5">
          <div className="w-11 h-11 rounded-2xl bg-gradient-to-tr from-purple-600 via-indigo-600 to-cyan-500 flex items-center justify-center text-white shadow-lg shadow-purple-500/25 shrink-0">
            <ShieldAlert className="w-6 h-6 text-white" />
          </div>
          <div>
            <h1 className="text-lg sm:text-xl font-extrabold text-white tracking-tight flex items-center gap-2">
              <span>Panel de Gobernanza & Fuentes BD Corporativas</span>
            </h1>
            <p className="text-xs text-gray-400">
              Administración centralizada de conexiones a SQLite, PostgreSQL, SQL Server y MySQL con cifrado AES-256
            </p>
          </div>
        </div>

        {/* Quick Stats Badges */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
          <div className="bg-dark-base/80 border border-dark-border/80 px-4 py-2.5 rounded-xl flex items-center space-x-3 shadow-inner">
            <Server className="w-4 h-4 text-purple-400 shrink-0" />
            <div className="truncate">
              <div className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">Fuentes BD</div>
              <div className="text-white font-bold text-xs">{connectors.length} ({activeCount} activas)</div>
            </div>
          </div>

          <div className="bg-dark-base/80 border border-dark-border/80 px-4 py-2.5 rounded-xl flex items-center space-x-3 shadow-inner">
            <Users className="w-4 h-4 text-emerald-400 shrink-0" />
            <div className="truncate">
              <div className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">Usuarios RBAC</div>
              <div className="text-white font-bold text-xs">{dbUsers.length} Perfiles</div>
            </div>
          </div>

          <div className="bg-dark-base/80 border border-dark-border/80 px-4 py-2.5 rounded-xl flex items-center space-x-3 shadow-inner">
            <Key className="w-4 h-4 text-cyan-400 shrink-0" />
            <div className="truncate">
              <div className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">Seguridad</div>
              <div className="text-emerald-400 font-bold text-xs">AES-256 + CLS</div>
            </div>
          </div>
        </div>
      </div>

      {/* Executive Navigation Tabs */}
      <div className="flex items-center space-x-2 border-b border-dark-border/80 pb-1 overflow-x-auto custom-scrollbar">
        <button
          type="button"
          onClick={() => setActiveTab('connectors')}
          className={`flex items-center space-x-2 px-4 py-2.5 text-xs font-bold transition-all whitespace-nowrap rounded-t-xl ${
            activeTab === 'connectors'
              ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30 glow-brand'
              : 'text-gray-400 hover:text-white hover:bg-dark-card/60'
          }`}
        >
          <Database className="w-4 h-4" />
          <span>Fuentes BD Corporativas ({connectors.length})</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('users')}
          className={`flex items-center space-x-2 px-4 py-2.5 text-xs font-bold transition-all whitespace-nowrap rounded-t-xl ${
            activeTab === 'users'
              ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30 glow-brand'
              : 'text-gray-400 hover:text-white hover:bg-dark-card/60'
          }`}
        >
          <Users className="w-4 h-4" />
          <span>Usuarios & Roles RBAC ({dbUsers.length})</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('catalog')}
          className={`flex items-center space-x-2 px-4 py-2.5 text-xs font-bold transition-all whitespace-nowrap rounded-t-xl ${
            activeTab === 'catalog'
              ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30 glow-brand'
              : 'text-gray-400 hover:text-white hover:bg-dark-card/60'
          }`}
        >
          <BookOpen className="w-4 h-4" />
          <span>Catálogo & Diccionario (IA)</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('audit')}
          className={`flex items-center space-x-2 px-4 py-2.5 text-xs font-bold transition-all whitespace-nowrap rounded-t-xl ${
            activeTab === 'audit'
              ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30 glow-brand'
              : 'text-gray-400 hover:text-white hover:bg-dark-card/60'
          }`}
        >
          <FileText className="w-4 h-4" />
          <span>Auditoría & Logs</span>
        </button>
      </div>

      {/* Tab 1: Corporate DB Connectors */}
      {activeTab === 'connectors' && (
        <AdminConnectorsTab
          connectors={connectors}
          onOpenCreateModal={handleOpenCreateModal}
          onOpenEditModal={handleOpenEditModal}
          onDeleteConnector={handleDeleteConnector}
          onToggleActive={handleToggleActive}
          onResetDemoConnectors={handleResetDemoConnectors}
          onRefreshConnectors={fetchConnectors}
        />
      )}

      {/* Tab 2: Users & Roles */}
      {activeTab === 'users' && <AdminUsersTab users={dbUsers} onRefreshUsers={fetchUsers} />}

      {/* Tab 3: Semantic Catalog & Dynamic Data Dictionary */}
      {activeTab === 'catalog' && <AdminCatalogTab />}

      {/* Tab 4: Audit & Compliance Logs */}
      {activeTab === 'audit' && <AdminAuditTab />}

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
