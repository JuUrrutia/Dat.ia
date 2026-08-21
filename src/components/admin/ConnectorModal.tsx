import React, { useReducer, useEffect } from 'react';
import { CorporateConnection, ConnectionFormData, connectorService, ConnectionTestResult } from '../../services/connector_service';
import { Database, RefreshCw, CheckCircle2, AlertCircle, Save, X } from 'lucide-react';
import { ConnectorFormFields } from './ConnectorFormFields';

interface ConnectorModalProps {
  isOpen: boolean;
  editingConnector: CorporateConnection | null;
  onClose: () => void;
  onSaveSuccess: () => void;
}

interface State {
  name: string;
  dbType: 'postgresql' | 'mssql' | 'mysql' | 'oracle' | 'sqlite';
  host: string;
  port: number;
  databaseName: string;
  username: string;
  password: string;
  isActive: boolean;
  isSubmitting: boolean;
  testingConn: boolean;
  testResult: ConnectionTestResult | null;
  errorMessage: string | null;
}

type Action =
  | { type: 'RESET_FORM'; payload: CorporateConnection | null }
  | { type: 'SET_FIELD'; field: string; value: any }
  | { type: 'CHANGE_DB_TYPE'; dbType: 'postgresql' | 'mssql' | 'mysql' | 'oracle' | 'sqlite' }
  | { type: 'SET_TESTING'; testing: boolean }
  | { type: 'SET_TEST_RESULT'; result: ConnectionTestResult | null }
  | { type: 'SET_SUBMITTING'; submitting: boolean }
  | { type: 'SET_ERROR'; message: string | null };


const initialState: State = {
  name: '',
  dbType: 'postgresql',
  host: 'localhost',
  port: 5432,
  databaseName: '',
  username: '',
  password: '',
  isActive: true,
  isSubmitting: false,
  testingConn: false,
  testResult: null,
  errorMessage: null,
};

function modalReducer(state: State, action: Action): State {
  switch (action.type) {
    case 'RESET_FORM':
      if (action.payload) {
        return {
          ...state,
          name: action.payload.name,
          dbType: action.payload.db_type,
          host: action.payload.host,
          port: action.payload.port,
          databaseName: action.payload.database_name,
          username: action.payload.username,
          password: '',
          isActive: action.payload.is_active,
          testResult: null,
          errorMessage: null,
        };
      }
      return {
        ...initialState,
      };
    case 'SET_FIELD':
      return { ...state, [action.field]: action.value };
    case 'CHANGE_DB_TYPE': {
      let defaultPort = 5432;
      if (action.dbType === 'mssql') defaultPort = 1433;
      else if (action.dbType === 'mysql') defaultPort = 3306;
      else if (action.dbType === 'oracle') defaultPort = 1521;
      return { ...state, dbType: action.dbType, port: defaultPort };
    }
    case 'SET_TESTING':
      return { ...state, testingConn: action.testing };
    case 'SET_TEST_RESULT':
      return { ...state, testResult: action.result, testingConn: false };
    case 'SET_SUBMITTING':
      return { ...state, isSubmitting: action.submitting };
    case 'SET_ERROR':
      return { ...state, errorMessage: action.message };
    default:
      return state;
  }
}

export const ConnectorModal: React.FC<ConnectorModalProps> = ({
  isOpen,
  editingConnector,
  onClose,
  onSaveSuccess,
}) => {
  const [state, dispatch] = useReducer(modalReducer, initialState);

  useEffect(() => {
    if (isOpen) {
      dispatch({ type: 'RESET_FORM', payload: editingConnector });
    }
  }, [editingConnector, isOpen]);

  if (!isOpen) return null;

  const handleTestConnection = async () => {
    if (!state.host || !state.databaseName || !state.username) {
      dispatch({ type: 'SET_ERROR', message: 'Por favor completa host, base de datos y usuario antes de probar.' });
      return;
    }

    dispatch({ type: 'SET_TESTING', testing: true });
    dispatch({ type: 'SET_TEST_RESULT', result: null });
    dispatch({ type: 'SET_ERROR', message: null });

    const formData: ConnectionFormData = {
      name: state.name || 'Test',
      db_type: state.dbType,
      host: state.host,
      port: Number(state.port),
      database_name: state.databaseName,
      username: state.username,
      password: state.password,
    };

    const res = await connectorService.testConnection(formData);
    dispatch({ type: 'SET_TEST_RESULT', result: res });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!state.name.trim() || !state.host.trim() || !state.databaseName.trim() || !state.username.trim()) {
      dispatch({ type: 'SET_ERROR', message: 'Por favor completa todos los campos requeridos.' });
      return;
    }

    dispatch({ type: 'SET_SUBMITTING', submitting: true });
    dispatch({ type: 'SET_ERROR', message: null });

    const formData: ConnectionFormData = {
      name: state.name,
      db_type: state.dbType,
      host: state.host,
      port: Number(state.port),
      database_name: state.databaseName,
      username: state.username,
      password: state.password || undefined,
      is_active: state.isActive,
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
      dispatch({ type: 'SET_ERROR', message: msg });
    } finally {
      dispatch({ type: 'SET_SUBMITTING', submitting: false });
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
          <button
            onClick={onClose}
            aria-label="Cerrar modal"
            className="text-gray-400 hover:text-white p-2 rounded-lg hover:bg-dark-card transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} className="p-6 overflow-y-auto space-y-4">
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

          {/* Actions */}
          <div className="pt-4 flex items-center justify-between border-t border-dark-border">
            <button
              type="button"
              onClick={handleTestConnection}
              disabled={state.testingConn}
              className="flex items-center space-x-1.5 text-xs bg-dark-base hover:bg-dark-border text-brand-400 border border-brand-500/30 px-4 py-2 rounded-xl transition-colors"
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
                type="submit"
                disabled={state.isSubmitting}
                className="flex items-center space-x-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-semibold px-5 py-2 rounded-xl shadow-lg shadow-purple-600/30 transition-colors"
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
