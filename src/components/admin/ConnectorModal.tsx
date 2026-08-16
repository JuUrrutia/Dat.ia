import React, { useState, useEffect } from 'react';
import { CorporateConnection, ConnectionFormData, connectorService, ConnectionTestResult } from '../../services/connector_service';
import { Database, Server, Key, ShieldCheck, RefreshCw, CheckCircle2, AlertCircle, Save, X } from 'lucide-react';

interface ConnectorModalProps {
  isOpen: boolean;
  editingConnector: CorporateConnection | null;
  onClose: () => void;
  onSaveSuccess: () => void;
}

export const ConnectorModal: React.FC<ConnectorModalProps> = ({
  isOpen,
  editingConnector,
  onClose,
  onSaveSuccess,
}) => {
  const [name, setName] = useState('');
  const [dbType, setDbType] = useState<'postgresql' | 'mssql' | 'mysql' | 'oracle'>('postgresql');
  const [host, setHost] = useState('localhost');
  const [port, setPort] = useState(5432);
  const [databaseName, setDatabaseName] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isActive, setIsActive] = useState(true);

  const [isSubmitting, setIsSubmitting] = useState(false);
  const [testingConn, setTestingConn] = useState(false);
  const [testResult, setTestResult] = useState<ConnectionTestResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (editingConnector) {
      setName(editingConnector.name);
      setDbType(editingConnector.db_type);
      setHost(editingConnector.host);
      setPort(editingConnector.port);
      setDatabaseName(editingConnector.database_name);
      setUsername(editingConnector.username);
      setPassword('');
      setIsActive(editingConnector.is_active);
    } else {
      setName('');
      setDbType('postgresql');
      setHost('localhost');
      setPort(5432);
      setDatabaseName('');
      setUsername('');
      setPassword('');
      setIsActive(true);
    }
    setTestResult(null);
    setErrorMessage(null);
  }, [editingConnector, isOpen]);

  if (!isOpen) return null;

  const handleDbTypeChange = (type: 'postgresql' | 'mssql' | 'mysql' | 'oracle') => {
    setDbType(type);
    if (type === 'postgresql') setPort(5432);
    else if (type === 'mssql') setPort(1433);
    else if (type === 'mysql') setPort(3306);
    else if (type === 'oracle') setPort(1521);
  };

  const handleTestConnection = async () => {
    if (!host || !databaseName || !username) {
      setErrorMessage('Por favor completa host, base de datos y usuario antes de probar.');
      return;
    }

    setTestingConn(true);
    setTestResult(null);
    setErrorMessage(null);

    const formData: ConnectionFormData = {
      name: name || 'Test',
      db_type: dbType,
      host,
      port: Number(port),
      database_name: databaseName,
      username,
      password,
    };

    const res = await connectorService.testConnection(formData);
    setTestingConn(false);
    setTestResult(res);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !host.trim() || !databaseName.trim() || !username.trim()) {
      setErrorMessage('Por favor completa todos los campos requeridos.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    const formData: ConnectionFormData = {
      name,
      db_type: dbType,
      host,
      port: Number(port),
      database_name: databaseName,
      username,
      password: password || undefined,
      is_active: isActive,
    };

    try {
      if (editingConnector) {
        await connectorService.updateConnector(editingConnector.id, formData);
      } else {
        await connectorService.createConnector(formData);
      }
      onSaveSuccess();
      onClose();
    } catch (err: any) {
      const msg = err.response?.data?.detail || 'Error al guardar la conexión en PostgreSQL.';
      setErrorMessage(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
      <div className="glass-panel w-full max-w-xl rounded-2xl border border-white/10 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-6 py-4 border-b border-dark-border flex items-center justify-between bg-dark-surface/90">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
              <Database className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-semibold text-white">
                {editingConnector ? 'Editar Conexión BD Corporativa' : 'Registrar Nueva Conexión BD Corporativa'}
              </h3>
              <p className="text-xs text-gray-400">Modo estricto de Solo Lectura (`READ ONLY`) con cifrado AES-256</p>
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white p-2 rounded-lg hover:bg-dark-card transition-all">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto space-y-4">
          {errorMessage && (
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-1.5">
              Nombre Identificador de la Conexión
            </label>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="ej. BD_FINANZAS_PROD"
              className="w-full bg-dark-base border border-dark-border rounded-xl px-4 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-500"
              required
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-1.5">
                Motor de Base de Datos
              </label>
              <select
                value={dbType}
                onChange={(e: any) => handleDbTypeChange(e.target.value)}
                className="w-full bg-dark-base border border-dark-border rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-brand-500"
              >
                <option value="postgresql">PostgreSQL</option>
                <option value="mssql">Microsoft SQL Server</option>
                <option value="mysql">MySQL / MariaDB</option>
                <option value="oracle">Oracle Database</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-1.5">
                Puerto Red
              </label>
              <input
                type="number"
                value={port}
                onChange={(e) => setPort(Number(e.target.value))}
                className="w-full bg-dark-base border border-dark-border rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-brand-500"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-1.5">
                Host / Dirección IP Servidor
              </label>
              <input
                type="text"
                value={host}
                onChange={(e) => setHost(e.target.value)}
                placeholder="10.0.1.45 o localhost"
                className="w-full bg-dark-base border border-dark-border rounded-xl px-4 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-500"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-1.5">
                Nombre de la Base de Datos
              </label>
              <input
                type="text"
                value={databaseName}
                onChange={(e) => setDatabaseName(e.target.value)}
                placeholder="ej. corp_finanzas"
                className="w-full bg-dark-base border border-dark-border rounded-xl px-4 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-500"
                required
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-1.5">
                Usuario Solo Lectura (READ ONLY)
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="usr_read_only"
                className="w-full bg-dark-base border border-dark-border rounded-xl px-4 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-500"
                required
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-1.5">
                Contraseña {editingConnector && '(Dejar vacío para no cambiar)'}
              </label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="w-full bg-dark-base border border-dark-border rounded-xl px-4 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-500"
                required={!editingConnector}
              />
            </div>
          </div>

          {/* Active Switch */}
          <div className="flex items-center space-x-3 pt-2">
            <input
              type="checkbox"
              id="isActiveCheck"
              checked={isActive}
              onChange={(e) => setIsActive(e.target.checked)}
              className="w-4 h-4 text-brand-600 rounded bg-dark-base border-dark-border focus:ring-brand-500"
            />
            <label htmlFor="isActiveCheck" className="text-xs text-gray-300 font-medium cursor-pointer">
              Habilitar esta fuente de datos para consultas analíticas
            </label>
          </div>

          {/* Test Result Banner */}
          {testResult && (
            <div
              className={`p-3 rounded-xl border text-xs flex items-center space-x-2 animate-fadeIn ${
                testResult.success
                  ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                  : 'bg-rose-500/10 border-rose-500/20 text-rose-400'
              }`}
            >
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{testResult.message} ({testResult.latency_ms} ms)</span>
            </div>
          )}

          {/* Actions */}
          <div className="pt-4 flex items-center justify-between border-t border-dark-border">
            <button
              type="button"
              onClick={handleTestConnection}
              disabled={testingConn}
              className="flex items-center space-x-1.5 text-xs bg-dark-base hover:bg-dark-border text-brand-400 border border-brand-500/30 px-4 py-2 rounded-xl transition-all"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${testingConn ? 'animate-spin' : ''}`} />
              <span>{testingConn ? 'Probando Red...' : 'Probar Conexión BD'}</span>
            </button>

            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 rounded-xl bg-dark-card hover:bg-dark-border text-gray-300 text-xs font-medium transition-all"
              >
                Cancelar
              </button>

              <button
                type="submit"
                disabled={isSubmitting}
                className="flex items-center space-x-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-semibold px-5 py-2 rounded-xl shadow-lg shadow-purple-600/30 transition-all"
              >
                <Save className="w-4 h-4" />
                <span>{editingConnector ? 'Guardar Cambios' : 'Registrar Conexión BD'}</span>
              </button>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
};
