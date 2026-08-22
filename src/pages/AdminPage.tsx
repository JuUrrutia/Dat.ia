import React, { useState, useEffect, useRef } from 'react';
import { ShieldAlert, Users, Database, BookOpen, Server, Key, FileText } from 'lucide-react';
import { CorporateConnection, connectorService, DEFAULT_CONNECTORS } from '../services/connector_service';
import { ConnectorModal } from '../components/admin/ConnectorModal';
import { AdminConnectorsTab } from '../components/admin/AdminConnectorsTab';
import { AdminUsersTab } from '../components/admin/AdminUsersTab';
import { AdminCatalogTab } from '../components/admin/AdminCatalogTab';
import { AdminAuditTab } from '../components/admin/AdminAuditTab';
import { authService } from '../services/auth_service';
import { User } from '../types';

const INITIAL_USERS: Array<{ id: number; name: string; username?: string; email: string; role: string; is_admin: boolean }> = [];

export const AdminPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'connectors' | 'users' | 'catalog' | 'audit'>('connectors');

  // Connectors State
  const [connectors, setConnectors] = useState<CorporateConnection[]>(DEFAULT_CONNECTORS);
  const isLoadingConnectorsRef = useRef(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingConnector, setEditingConnector] = useState<CorporateConnection | null>(null);

  // Users State
  const [dbUsers, setDbUsers] = useState<Array<{ id: number; name: string; username?: string; email: string; role: string; is_admin: boolean }>>(INITIAL_USERS);

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
    isLoadingConnectorsRef.current = true;
    try {
      const data = await connectorService.getConnectors();
      if (data && data.length > 0) {
        setConnectors(data);
      } else {
        setConnectors(DEFAULT_CONNECTORS);
      }
    } catch {
      setConnectors(DEFAULT_CONNECTORS);
    } finally {
      isLoadingConnectorsRef.current = false;
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
    <div className="flex-1 bg-dark-base overflow-y-auto p-4 sm:p-6 space-y-6">
      {/* Header Banner */}
      <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 glass-panel p-4 sm:p-5 rounded-2xl sm:rounded-3xl border border-white/10">
        <div className="space-y-1">
          <h1 className="text-lg sm:text-xl font-bold text-white flex items-center gap-2.5">
            <ShieldAlert className="w-5 h-5 text-purple-400 shrink-0" />
            <span>Panel de Gobernanza & Fuentes BD Corporativas</span>
          </h1>
          <p className="text-xs text-gray-400">
            Administración centralizada de conexiones a SQLite, PostgreSQL, SQL Server y MySQL con cifrado AES-256
          </p>
        </div>

        {/* Quick Stats Badges */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5 text-xs">
          <div className="bg-dark-base/80 border border-dark-border px-3.5 py-2 rounded-xl flex items-center space-x-2">
            <Server className="w-4 h-4 text-purple-400 shrink-0" />
            <div className="truncate">
              <div className="text-[10px] text-gray-400 uppercase font-semibold">Fuentes BD</div>
              <div className="text-white font-bold">{connectors.length} ({activeCount} activas)</div>
            </div>
          </div>

          <div className="bg-dark-base/80 border border-dark-border px-3.5 py-2 rounded-xl flex items-center space-x-2">
            <Users className="w-4 h-4 text-emerald-400 shrink-0" />
            <div className="truncate">
              <div className="text-[10px] text-gray-400 uppercase font-semibold">Usuarios RBAC</div>
              <div className="text-white font-bold">{dbUsers.length} Perfiles</div>
            </div>
          </div>

          <div className="bg-dark-base/80 border border-dark-border px-3.5 py-2 rounded-xl flex items-center space-x-2">
            <Key className="w-4 h-4 text-cyan-400 shrink-0" />
            <div className="truncate">
              <div className="text-[10px] text-gray-400 uppercase font-semibold">Seguridad</div>
              <div className="text-emerald-400 font-bold">AES-256 + CLS</div>
            </div>
          </div>
        </div>
      </div>

      {/* Navigation Tabs (Smooth Responsive Horizontal Scroll) */}
      <div className="flex items-center space-x-2 border-b border-dark-border pb-1 overflow-x-auto custom-scrollbar">
        <button
          type="button"
          onClick={() => setActiveTab('connectors')}
          className={`flex items-center space-x-2 px-3.5 sm:px-4 py-2.5 text-xs font-medium border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'connectors'
              ? 'border-purple-500 text-purple-400 font-bold bg-purple-500/10 rounded-t-xl'
              : 'border-transparent text-gray-400 hover:text-white hover:bg-dark-card/50 rounded-t-xl'
          }`}
        >
          <Database className="w-4 h-4" />
          <span>Fuentes BD Corporativas ({connectors.length})</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('users')}
          className={`flex items-center space-x-2 px-3.5 sm:px-4 py-2.5 text-xs font-medium border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'users'
              ? 'border-purple-500 text-purple-400 font-bold bg-purple-500/10 rounded-t-xl'
              : 'border-transparent text-gray-400 hover:text-white hover:bg-dark-card/50 rounded-t-xl'
          }`}
        >
          <Users className="w-4 h-4" />
          <span>Usuarios & Roles ({dbUsers.length})</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('catalog')}
          className={`flex items-center space-x-2 px-3.5 sm:px-4 py-2.5 text-xs font-medium border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'catalog'
              ? 'border-purple-500 text-purple-400 font-bold bg-purple-500/10 rounded-t-xl'
              : 'border-transparent text-gray-400 hover:text-white hover:bg-dark-card/50 rounded-t-xl'
          }`}
        >
          <BookOpen className="w-4 h-4" />
          <span>Catálogo & Diccionario (IA)</span>
        </button>

        <button
          type="button"
          onClick={() => setActiveTab('audit')}
          className={`flex items-center space-x-2 px-3.5 sm:px-4 py-2.5 text-xs font-medium border-b-2 transition-colors whitespace-nowrap ${
            activeTab === 'audit'
              ? 'border-purple-500 text-purple-400 font-bold bg-purple-500/10 rounded-t-xl'
              : 'border-transparent text-gray-400 hover:text-white hover:bg-dark-card/50 rounded-t-xl'
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
