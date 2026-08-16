import React from 'react';
import { CorporateConnection } from '../../services/connector_service';

export interface FormFieldsProps {
  name: string;
  dbType: 'postgresql' | 'mssql' | 'mysql' | 'oracle';
  host: string;
  port: number;
  databaseName: string;
  username: string;
  password: string;
  isActive: boolean;
  editingConnector: CorporateConnection | null;
  onFieldChange: (field: string, value: any) => void;
  onDbTypeChange: (dbType: 'postgresql' | 'mssql' | 'mysql' | 'oracle') => void;
}

export const ConnectorFormFields: React.FC<FormFieldsProps> = ({
  name,
  dbType,
  host,
  port,
  databaseName,
  username,
  password,
  isActive,
  editingConnector,
  onFieldChange,
  onDbTypeChange,
}) => {
  return (
    <>
      <div>
        <label htmlFor="conn-name" className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-1.5">
          Nombre Identificador de la Conexión
        </label>
        <input
          id="conn-name"
          type="text"
          value={name}
          onChange={(e) => onFieldChange('name', e.target.value)}
          placeholder="ej. BD_FINANZAS_PROD"
          className="w-full bg-dark-base border border-dark-border rounded-xl px-4 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-500"
          required
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="conn-db-type" className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-1.5">
            Motor de Base de Datos
          </label>
          <select
            id="conn-db-type"
            value={dbType}
            onChange={(e: any) => onDbTypeChange(e.target.value)}
            className="w-full bg-dark-base border border-dark-border rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-brand-500"
          >
            <option value="postgresql">PostgreSQL</option>
            <option value="mssql">Microsoft SQL Server</option>
            <option value="mysql">MySQL / MariaDB</option>
            <option value="oracle">Oracle Database</option>
          </select>
        </div>

        <div>
          <label htmlFor="conn-port" className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-1.5">
            Puerto Red
          </label>
          <input
            id="conn-port"
            type="number"
            value={port || ''}
            onChange={(e) => onFieldChange('port', parseInt(e.target.value, 10) || 0)}
            className="w-full bg-dark-base border border-dark-border rounded-xl px-4 py-2.5 text-xs text-white focus:outline-none focus:border-brand-500"
            required
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="conn-host" className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-1.5">
            Host / Dirección IP Servidor
          </label>
          <input
            id="conn-host"
            type="text"
            value={host}
            onChange={(e) => onFieldChange('host', e.target.value)}
            placeholder="10.0.1.45 o localhost"
            className="w-full bg-dark-base border border-dark-border rounded-xl px-4 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-500"
            required
          />
        </div>

        <div>
          <label htmlFor="conn-dbname" className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-1.5">
            Nombre de la Base de Datos
          </label>
          <input
            id="conn-dbname"
            type="text"
            value={databaseName}
            onChange={(e) => onFieldChange('databaseName', e.target.value)}
            placeholder="ej. corp_finanzas"
            className="w-full bg-dark-base border border-dark-border rounded-xl px-4 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-500"
            required
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label htmlFor="conn-user" className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-1.5">
            Usuario Solo Lectura (READ ONLY)
          </label>
          <input
            id="conn-user"
            type="text"
            value={username}
            onChange={(e) => onFieldChange('username', e.target.value)}
            placeholder="usr_read_only"
            className="w-full bg-dark-base border border-dark-border rounded-xl px-4 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-500"
            required
          />
        </div>

        <div>
          <label htmlFor="conn-pass" className="block text-xs font-semibold text-gray-300 uppercase tracking-wider mb-1.5">
            Contraseña {editingConnector && '(Dejar vacío para no cambiar)'}
          </label>
          <input
            id="conn-pass"
            type="password"
            value={password}
            onChange={(e) => onFieldChange('password', e.target.value)}
            placeholder="••••••••"
            className="w-full bg-dark-base border border-dark-border rounded-xl px-4 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-brand-500"
            required={!editingConnector}
          />
        </div>
      </div>

      <div className="flex items-center space-x-3 pt-2">
        <input
          type="checkbox"
          id="isActiveCheck"
          checked={isActive}
          onChange={(e) => onFieldChange('isActive', e.target.checked)}
          className="w-4 h-4 text-brand-600 rounded bg-dark-base border-dark-border focus:ring-brand-500"
        />
        <label htmlFor="isActiveCheck" className="text-xs text-gray-300 font-medium cursor-pointer">
          Habilitar esta fuente de datos para consultas analíticas
        </label>
      </div>
    </>
  );
};
