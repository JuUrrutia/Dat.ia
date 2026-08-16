import React from 'react';
import { Sparkles, Check } from 'lucide-react';

interface CatalogItem {
  table: string;
  column: string;
  desc: string;
  formula: string;
  is_ai: boolean;
}

interface AdminCatalogTabProps {
  catalog: CatalogItem[];
  aiEnriching: boolean;
  aiSuccess: boolean;
  onRunAiCatalog: () => void;
}

export const AdminCatalogTab: React.FC<AdminCatalogTabProps> = ({
  catalog,
  aiEnriching,
  aiSuccess,
  onRunAiCatalog,
}) => {
  return (
    <div className="glass-panel rounded-2xl p-6 border border-white/10 space-y-5">
      <div className="flex items-center justify-between border-b border-dark-border pb-4">
        <div>
          <h3 className="text-sm font-semibold text-white">Catálogo Semántico y Diccionario de Datos</h3>
          <p className="text-xs text-gray-400">Enriquece tablas y columnas con descripciones en español y fórmulas</p>
        </div>

        <button
          onClick={onRunAiCatalog}
          disabled={aiEnriching}
          className="flex items-center space-x-2 text-xs bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white font-medium px-4 py-2 rounded-xl shadow-lg shadow-purple-600/30 transition-colors"
        >
          <Sparkles className={`w-4 h-4 ${aiEnriching ? 'animate-spin' : ''}`} />
          <span>{aiEnriching ? 'Analizando Esquema...' : 'Auto-enriquecer con IA'}</span>
        </button>
      </div>

      {aiSuccess && (
        <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center space-x-2">
          <Check className="w-4 h-4" />
          <span>Catálogo semántico enriched automáticamente con descripciones generadas por la IA local.</span>
        </div>
      )}

      <div className="overflow-x-auto rounded-xl border border-dark-border">
        <table className="w-full text-left text-xs">
          <thead className="bg-dark-base border-b border-dark-border text-gray-400 uppercase">
            <tr>
              <th className="px-4 py-3">Tabla</th>
              <th className="px-4 py-3">Columna</th>
              <th className="px-4 py-3">Descripción Semántica</th>
              <th className="px-4 py-3">Fórmula / Regla</th>
              <th className="px-4 py-3">Origen</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-dark-border text-gray-200">
            {catalog.map((cat) => (
              <tr key={`${cat.table}-${cat.column}`} className="hover:bg-dark-card/50">
                <td className="px-4 py-3 font-mono text-brand-400">{cat.table}</td>
                <td className="px-4 py-3 font-mono">{cat.column}</td>
                <td className="px-4 py-3">{cat.desc}</td>
                <td className="px-4 py-3 font-mono text-gray-400">{cat.formula}</td>
                <td className="px-4 py-3">
                  {cat.is_ai ? (
                    <span className="bg-purple-500/10 text-purple-400 border border-purple-500/20 px-2 py-0.5 rounded text-[10px]">
                      IA Auto-generado
                    </span>
                  ) : (
                    <span className="bg-gray-500/10 text-gray-400 border border-gray-500/20 px-2 py-0.5 rounded text-[10px]">
                      Manual Admin
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
