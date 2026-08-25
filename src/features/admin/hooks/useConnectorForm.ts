import { useReducer, useEffect } from 'react';
import { CorporateConnection, ConnectionFormData, connectorService, ConnectionTestResult } from '../../../services/connector_service';

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

export function useConnectorForm(
  isOpen: boolean,
  editingConnector: CorporateConnection | null,
  onSaveSuccess: () => void,
  onClose: () => void
) {
  const [state, dispatch] = useReducer(modalReducer, initialState);

  useEffect(() => {
    if (isOpen) {
      dispatch({ type: 'RESET_FORM', payload: editingConnector });
    }
  }, [editingConnector, isOpen]);

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

  return {
    state,
    dispatch,
    handleTestConnection,
    handleSubmit,
  };
}
