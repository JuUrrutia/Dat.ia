import React, { useState, useRef } from 'react';
import { UploadCloud, Database, CheckCircle2, AlertCircle, X, Loader2 } from 'lucide-react';
import { connectorService } from '../../services/connector_service';

interface DatabaseUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  onUploadSuccess: () => void;
}

export const DatabaseUploadModal: React.FC<DatabaseUploadModalProps> = ({
  isOpen,
  onClose,
  onUploadSuccess,
}) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [customName, setCustomName] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!isOpen) return null;

  const handleFileChange = (file: File) => {
    setErrorMessage(null);
    setSuccessMessage(null);
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!['sqlite', 'db', 'sqlite3', 'sql'].includes(ext || '')) {
      setErrorMessage('Formato de archivo no soportado. Selecciona un archivo .sqlite, .db o .sql.');
      setSelectedFile(null);
      return;
    }
    setSelectedFile(file);
    if (!customName) {
      const baseName = file.name.substring(0, file.name.lastIndexOf('.')) || file.name;
      setCustomName(baseName.replace(/[_-]/g, ' ').toUpperCase());
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileChange(e.dataTransfer.files[0]);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) {
      setErrorMessage('Por favor selecciona un archivo de base de datos para importar.');
      return;
    }

    setIsUploading(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      await connectorService.uploadDatabase(selectedFile, customName);
      setSuccessMessage('¡Base de datos importada, registrada e indexada en el catálogo exitosamente!');
      setTimeout(() => {
        onUploadSuccess();
        handleClose();
      }, 1200);
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Error al importar la base de datos al servidor.';
      setErrorMessage(msg);
    } finally {
      setIsUploading(false);
    }
  };

  const handleClose = () => {
    setSelectedFile(null);
    setCustomName('');
    setErrorMessage(null);
    setSuccessMessage(null);
    setIsUploading(false);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/75 backdrop-blur-sm animate-fadeIn">
      <div className="glass-panel w-full max-w-lg rounded-2xl sm:rounded-3xl border border-white/10 shadow-2xl overflow-hidden flex flex-col max-h-[90vh]">
        {/* Header */}
        <div className="px-5 sm:px-6 py-4 border-b border-dark-border flex items-center justify-between bg-dark-surface/90">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20">
              <UploadCloud className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm sm:text-base font-semibold text-white">Importar Base de Datos (SQLite / SQL)</h3>
              <p className="text-[11px] text-gray-400">Incorpora nuevas fuentes de datos corporativas con persistencia real</p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleClose}
            aria-label="Cerrar modal"
            className="text-gray-400 hover:text-white p-1.5 rounded-lg hover:bg-dark-card transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Content Body */}
        <form onSubmit={handleSubmit} className="p-5 sm:p-6 space-y-4 overflow-y-auto">
          {errorMessage && (
            <div className="p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center space-x-2 animate-fadeIn">
              <AlertCircle className="w-4 h-4 shrink-0" />
              <span>{errorMessage}</span>
            </div>
          )}

          {successMessage && (
            <div className="p-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs flex items-center space-x-2 animate-fadeIn">
              <CheckCircle2 className="w-4 h-4 shrink-0" />
              <span>{successMessage}</span>
            </div>
          )}

          {/* Drag & Drop Area */}
          <div
            onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
            onDragLeave={() => setIsDragging(false)}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition-all ${
              isDragging
                ? 'border-purple-500 bg-purple-500/10 scale-[1.01]'
                : selectedFile
                ? 'border-emerald-500/40 bg-emerald-500/5'
                : 'border-dark-border hover:border-purple-500/40 hover:bg-dark-card/40'
            }`}
          >
            <input
              type="file"
              ref={fileInputRef}
              onChange={(e) => {
                if (e.target.files && e.target.files.length > 0) {
                  handleFileChange(e.target.files[0]);
                }
              }}
              accept=".sqlite,.db,.sqlite3,.sql"
              className="hidden"
            />

            {selectedFile ? (
              <div className="space-y-2 flex flex-col items-center">
                <div className="w-12 h-12 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center border border-emerald-500/20">
                  <Database className="w-6 h-6" />
                </div>
                <div>
                  <div className="text-xs font-bold text-white truncate max-w-xs">{selectedFile.name}</div>
                  <div className="text-[10px] text-gray-400 font-mono">
                    {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • Archivo listo para importar
                  </div>
                </div>
                <button
                  type="button"
                  onClick={(e) => { e.stopPropagation(); setSelectedFile(null); }}
                  className="text-[11px] text-rose-400 hover:underline pt-1"
                >
                  Cambiar archivo
                </button>
              </div>
            ) : (
              <div className="space-y-2 flex flex-col items-center">
                <div className="w-12 h-12 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center border border-purple-500/20">
                  <UploadCloud className="w-6 h-6" />
                </div>
                <div className="space-y-0.5">
                  <div className="text-xs font-semibold text-gray-200">
                    Haz clic para seleccionar o arrastra tu archivo aquí
                  </div>
                  <p className="text-[11px] text-gray-400">
                    Soporta SQLite (.sqlite, .db, .sqlite3) y scripts SQL (.sql)
                  </p>
                </div>
              </div>
            )}
          </div>

          {/* Database Name Field */}
          <div className="space-y-1.5">
            <label className="block text-xs font-semibold text-gray-300">
              Nombre de la Fuente BD (Visualización)
            </label>
            <input
              type="text"
              value={customName}
              onChange={(e) => setCustomName(e.target.value)}
              placeholder="ej. BD_SALUD_MENTAL, BD_VENTAS_2026"
              className="w-full bg-dark-base border border-dark-border rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 transition-colors"
            />
            <p className="text-[10px] text-gray-500">
              Se creará un conector registrado con permisos automáticos y catalogación semántica.
            </p>
          </div>

          {/* Actions */}
          <div className="pt-3 flex items-center justify-end space-x-2.5 border-t border-dark-border">
            <button
              type="button"
              onClick={handleClose}
              disabled={isUploading}
              className="px-4 py-2 rounded-xl bg-dark-card hover:bg-dark-border text-gray-300 text-xs font-medium transition-colors"
            >
              Cancelar
            </button>

            <button
              type="submit"
              disabled={!selectedFile || isUploading}
              className="flex items-center space-x-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-semibold px-5 py-2 rounded-xl shadow-lg shadow-purple-600/30 transition-colors disabled:opacity-50"
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Importando e Indexando...</span>
                </>
              ) : (
                <>
                  <UploadCloud className="w-4 h-4" />
                  <span>Importar a la Base de Datos</span>
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
