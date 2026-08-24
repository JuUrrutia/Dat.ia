import React, { useState } from 'react';
import { Search, RefreshCw, Database, Table as TableIcon, Eye, Key } from 'lucide-react';
import { DataDictionaryResponse, DataDictionaryTable } from '../../../services/catalog_service';

interface DataDictionarySectionProps {
  dataDictionary: DataDictionaryResponse | null;
  isLoadingDictionary: boolean;
  expandedTables: Record<string, boolean>;
  onToggleTableExpansion: (tableName: string) => void;
}

export const DataDictionarySection: React.FC<DataDictionarySectionProps> = ({
  dataDictionary,
  isLoadingDictionary,
  expandedTables,
  onToggleTableExpansion,
}) => {
  const [dictSearchQuery, setDictSearchQuery] = useState('');

  // Filter Dictionary Tables
  const filteredDictTables = (dataDictionary?.tables || []).filter((tbl) => {
    if (!dictSearchQuery.trim()) return true;
    const q = dictSearchQuery.toLowerCase();
    const matchesTableName = tbl.table_name.toLowerCase().includes(q);
    const matchesColumn = tbl.columns.some(
      (c) =>
        c.name.toLowerCase().includes(q) ||
        c.data_type.toLowerCase().includes(q) ||
        (c.description && c.description.toLowerCase().includes(q))
    );
    return matchesTableName || matchesColumn;
  });

  return (
    <div className="space-y-4 animate-fadeIn">
      {/* Search bar and metadata overview */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
          <input
            type="text"
            value={dictSearchQuery}
            onChange={(e) => setDictSearchQuery(e.target.value)}
            placeholder="Buscar tabla, columna o tipo de dato..."
            aria-label="Buscar en diccionario de datos"
            className="w-full bg-dark-base border border-dark-border rounded-xl pl-9 pr-3 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 transition-colors"
          />
        </div>

        <div className="flex items-center space-x-3 text-xs text-gray-400">
          <span className="bg-dark-base px-3 py-1.5 rounded-xl border border-dark-border">
            Base: <strong className="text-white">{dataDictionary?.connection_name || 'BD Activa'}</strong>
          </span>
          <span className="bg-dark-base px-3 py-1.5 rounded-xl border border-dark-border">
            Total: <strong className="text-purple-400">{dataDictionary?.total_tables || 0} Tablas</strong> •{' '}
            <strong className="text-cyan-400">{dataDictionary?.total_columns || 0} Columnas</strong>
          </span>
        </div>
      </div>

      {isLoadingDictionary ? (
        <div className="py-12 text-center text-gray-400 border border-dark-border rounded-2xl">
          <RefreshCw className="w-6 h-6 animate-spin mx-auto mb-2 text-purple-400" />
          Introspeccionando esquema físico de la base de datos...
        </div>
      ) : filteredDictTables.length === 0 ? (
        <div className="text-center py-12 border border-dashed border-dark-border rounded-2xl p-8 space-y-2">
          <Database className="w-8 h-8 text-gray-500 mx-auto" />
          <h4 className="text-sm font-semibold text-white">No se encontraron tablas físicas</h4>
          <p className="text-xs text-gray-400">
            Asegúrate de que haya una base de datos conectada o importa un archivo SQLite en la pestaña de Conexiones.
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {filteredDictTables.map((tbl: DataDictionaryTable) => {
            const isExpanded = Boolean(expandedTables[tbl.table_name]);
            return (
              <div
                key={tbl.table_name}
                className="glass-card rounded-2xl border border-white/10 overflow-hidden transition-colors"
              >
                {/* Table Summary Header */}
                <button
                  type="button"
                  onClick={() => onToggleTableExpansion(tbl.table_name)}
                  aria-expanded={isExpanded}
                  className="w-full p-4 bg-dark-surface/80 hover:bg-dark-card/60 flex items-center justify-between text-left cursor-pointer transition-colors border-b border-dark-border/60 focus:outline-none"
                >
                  <div className="flex items-center space-x-3">
                    <div className="w-8 h-8 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center border border-purple-500/20">
                      <TableIcon className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="flex items-center space-x-2">
                        <span className="font-bold text-white text-sm font-mono">{tbl.table_name}</span>
                        <span className="text-[10px] bg-purple-500/10 text-purple-400 border border-purple-500/20 px-2 py-0.5 rounded-full font-semibold">
                          {tbl.column_count} Columnas
                        </span>
                        <span className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 px-2 py-0.5 rounded-full font-semibold">
                          {tbl.row_count.toLocaleString()} Filas
                        </span>
                      </div>
                      {tbl.description && (
                        <p className="text-xs text-gray-400 mt-0.5">{tbl.description}</p>
                      )}
                    </div>
                  </div>

                  <div className="flex items-center space-x-2 text-xs text-gray-400">
                    <span>{isExpanded ? 'Ocultar Columnas' : 'Ver Columnas'}</span>
                    <Eye className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`} />
                  </div>
                </button>

                {/* Columns Detail Table */}
                {isExpanded && (
                  <div className="overflow-x-auto p-2 bg-dark-base/40">
                    <table className="w-full text-left text-xs min-w-[700px]">
                      <thead className="text-[10px] text-gray-400 uppercase tracking-wider border-b border-dark-border">
                        <tr>
                          <th className="px-3 py-2">Columna</th>
                          <th className="px-3 py-2">Tipo SQL</th>
                          <th className="px-3 py-2">Restricciones</th>
                          <th className="px-3 py-2">Muestra de Datos Reales</th>
                          <th className="px-3 py-2">Definición de Negocio (IA)</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-dark-border/50 text-gray-300">
                        {tbl.columns.map((col) => (
                          <tr key={col.name} className="hover:bg-dark-card/30 transition-colors">
                            <td className="px-3 py-2.5 font-mono font-medium text-white flex items-center space-x-1.5">
                              {col.is_pk && <Key className="w-3 h-3 text-amber-400 shrink-0" />}
                              <span>{col.name}</span>
                            </td>
                            <td className="px-3 py-2.5">
                              <span className="bg-dark-card border border-dark-border text-cyan-400 font-mono px-2 py-0.5 rounded text-[10px] font-semibold">
                                {col.data_type}
                              </span>
                            </td>
                            <td className="px-3 py-2.5">
                              <div className="flex items-center space-x-1 text-[10px]">
                                {col.is_pk && (
                                  <span className="bg-amber-500/10 text-amber-400 border border-amber-500/20 px-1.5 py-0.5 rounded font-bold">
                                    PK
                                  </span>
                                )}
                                {!col.is_nullable && (
                                  <span className="bg-rose-500/10 text-rose-400 border border-rose-500/20 px-1.5 py-0.5 rounded">
                                    NOT NULL
                                  </span>
                                )}
                                {col.is_nullable && !col.is_pk && (
                                  <span className="text-gray-500">NULL</span>
                                )}
                              </div>
                            </td>
                            <td className="px-3 py-2.5 max-w-xs">
                              {col.sample_values && col.sample_values.length > 0 ? (
                                <div className="flex flex-wrap gap-1">
                                  {col.sample_values.map((v, i) => (
                                    <span
                                      key={`${col.name}-sample-${v}-${i}`}
                                      className="bg-dark-card/80 text-gray-300 font-mono text-[10px] px-1.5 py-0.5 rounded border border-dark-border/60 truncate max-w-[140px]"
                                      title={String(v)}
                                    >
                                      {v}
                                    </span>
                                  ))}
                                </div>
                              ) : (
                                <span className="text-gray-600 text-[10px] italic">Sin datos</span>
                              )}
                            </td>
                            <td className="px-3 py-2.5 text-gray-300">
                              {col.description ? (
                                <div>
                                  <span className="text-white font-medium text-[11px] block">
                                    {col.friendly_name || col.name}
                                  </span>
                                  <span className="text-gray-400 text-[11px]">{col.description}</span>
                                </div>
                              ) : (
                                <span className="text-gray-500 italic text-[11px]">
                                  Sin descripción semántica
                                </span>
                              )}
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
