import React from 'react';
import { CorporateConnection } from '../../services/connector_service';
import { Database, RefreshCw, CheckCircle2, AlertCircle, Save, X } from 'lucide-react';
import { ConnectorFormFields } from './ConnectorFormFields';
import { useConnectorForm } from '../../features/admin/hooks/useConnectorForm';

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
  const { state, dispatch, handleTestConnection, handleSubmit } = useConnectorForm(
    isOpen,
    editingConnector,
    onSaveSuccess,
    onClose
  );

  if (!isOpen) return null;

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
          <button
            onClick={onClose}
            aria-label="Cerrar modal"
            className="text-gray-400 hover:text-white p-2 rounded-lg hover:bg-dark-card transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <form id="connector-modal-form" onSubmit={handleSubmit} className="flex-1 overflow-y-auto min-h-0 p-5 sm:p-6 space-y-4">
          {state.errorMessage && (
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center space-x-2">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{state.errorMessage}</span>
            </div>
          )}

          <ConnectorFormFields
            name={state.name}
            dbType={state.dbType}
            host={state.host}
            port={state.port}
            databaseName={state.databaseName}
            username={state.username}
            password={state.password}
            isActive={state.isActive}
            editingConnector={editingConnector}
            onFieldChange={(field, value) => dispatch({ type: 'SET_FIELD', field, value })}
            onDbTypeChange={(dbType) => dispatch({ type: 'CHANGE_DB_TYPE', dbType })}
          />

          {/* Test Result Banner */}
          {state.testResult && (
            <div
              className={`p-3 rounded-xl border text-xs flex items-center space-x-2 animate-fadeIn ${
                state.testResult.success
                  ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400'
                  : 'bg-rose-500/10 border-rose-500/20 text-rose-400'
              }`}
            >
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{state.testResult.message} ({state.testResult.latency_ms} ms)</span>
            </div>
          )}
        </form>

        {/* Fixed Sticky Footer Actions */}
        <div className="shrink-0 px-5 sm:px-6 py-3.5 border-t border-dark-border bg-dark-surface/95 backdrop-blur flex items-center justify-between z-10">
          <button
            type="button"
            onClick={handleTestConnection}
            disabled={state.testingConn}
            className="flex items-center space-x-1.5 text-xs bg-dark-base hover:bg-dark-border text-brand-400 border border-brand-500/30 px-3.5 py-2 rounded-xl transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${state.testingConn ? 'animate-spin' : ''}`} />
            <span>{state.testingConn ? 'Probando Red...' : 'Probar Conexión BD'}</span>
          </button>

          <div className="flex items-center space-x-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl bg-dark-card hover:bg-dark-border text-gray-300 text-xs font-medium transition-colors"
            >
              Cancelar
            </button>

            <button
              form="connector-modal-form"
              type="submit"
              disabled={state.isSubmitting}
              className="flex items-center space-x-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-semibold px-5 py-2 rounded-xl shadow-lg shadow-purple-600/30 transition-colors"
            >
              <Save className="w-4 h-4" />
              <span>{editingConnector ? 'Guardar Cambios' : 'Registrar Conexión BD'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
