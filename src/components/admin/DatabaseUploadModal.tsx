import React, { useState, useRef } from 'react';
import { UploadCloud, Database, CheckCircle2, AlertCircle, X, Loader2, FileSpreadsheet, FileText, Check } from 'lucide-react';
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
    const validExts = ['sqlite', 'db', 'sqlite3', 'sql', 'csv', 'xlsx', 'xls', 'tsv', 'txt'];
    if (!validExts.includes(ext || '')) {
      setErrorMessage('Formato no soportado. Selecciona SQLite (.sqlite, .db), Excel (.xlsx, .xls), CSV (.csv) o SQL (.sql).');
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
      setErrorMessage('Por favor selecciona un archivo (SQLite, Excel o CSV) para importar.');
      return;
    }

    setIsUploading(true);
    setErrorMessage(null);
    setSuccessMessage(null);

    try {
      const res = await connectorService.uploadDatabase(selectedFile, customName);
      setSuccessMessage(
        res.requires_permission_review
          ? '¡Base de datos importada! Ningún rol no-administrador tiene acceso todavía — configura los permisos en la pestaña Catálogo para habilitarla a los analistas.'
          : '¡Fuente de datos importada, estructurada e indexada exitosamente!'
      );
      setTimeout(() => {
        onUploadSuccess();
        handleClose();
      }, 2200);
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Error al importar la fuente de datos al servidor.';
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

  const getFileBadge = () => {
    if (!selectedFile) return null;
    const ext = selectedFile.name.split('.').pop()?.toLowerCase();
    if (['xlsx', 'xls'].includes(ext || '')) {
      return { icon: <FileSpreadsheet className="w-5 h-5 text-emerald-400" />, label: 'Excel', color: 'border-emerald-500/30 bg-emerald-500/10' };
    }
    if (['csv', 'tsv', 'txt'].includes(ext || '')) {
      return { icon: <FileText className="w-5 h-5 text-cyan-400" />, label: 'CSV', color: 'border-cyan-500/30 bg-cyan-500/10' };
    }
    return { icon: <Database className="w-5 h-5 text-purple-400" />, label: 'SQLite', color: 'border-purple-500/30 bg-purple-500/10' };
  };

  const fileBadge = getFileBadge();

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-sm animate-fadeIn">
      <div className="glass-panel w-full max-w-lg rounded-2xl sm:rounded-3xl border border-white/10 shadow-2xl overflow-hidden flex flex-col max-h-[88vh] sm:max-h-[90vh]">
        {/* Fixed Header */}
        <div className="shrink-0 px-5 sm:px-6 py-4 border-b border-dark-border flex items-center justify-between bg-dark-surface/95 backdrop-blur">
          <div className="flex items-center space-x-3">
            <div className="p-2 rounded-xl bg-purple-500/10 text-purple-400 border border-purple-500/20 shrink-0">
              <UploadCloud className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm sm:text-base font-semibold text-white leading-tight">
                Importar Fuente de Datos (SQLite / Excel / CSV)
              </h3>
              <p className="text-[11px] text-gray-400">
                Estructuración relacional automática con permisos y catálogo
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleClose}
            aria-label="Cerrar modal"
            className="text-gray-400 hover:text-white p-1.5 rounded-lg hover:bg-dark-card transition-colors shrink-0"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Scrollable Form Body */}
        <form
          id="db-upload-modal-form"
          onSubmit={handleSubmit}
          className="flex-1 overflow-y-auto min-h-0 p-4 sm:p-5 space-y-3.5"
        >
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

          {/* Drag & Drop Area / Selected File Preview */}
          {selectedFile && fileBadge ? (
            <div className="border-2 border-emerald-500/40 bg-emerald-500/5 rounded-2xl p-4 sm:p-5 text-center transition-colors">
              <input
                type="file"
                ref={fileInputRef}
                onChange={(e) => {
                  if (e.target.files && e.target.files.length > 0) {
                    handleFileChange(e.target.files[0]);
                  }
                }}
                accept=".sqlite,.db,.sqlite3,.sql,.csv,.xlsx,.xls,.tsv,.txt"
                className="hidden"
              />
              <div className="space-y-2 flex flex-col items-center">
                <div className={`p-2.5 rounded-xl border flex items-center justify-center ${fileBadge.color}`}>
                  {fileBadge.icon}
                </div>
                <div className="space-y-0.5">
                  <div className="text-xs font-bold text-white truncate max-w-xs">{selectedFile.name}</div>
                  <div className="text-[10px] text-gray-400 font-mono">
                    {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB • Tipo: {fileBadge.label}
                  </div>
                </div>
                <div className="flex items-center space-x-3 pt-1">
                  <button
                    type="button"
                    onClick={() => fileInputRef.current?.click()}
                    className="text-[11px] text-purple-400 hover:text-purple-300 underline font-medium"
                  >
                    Cambiar archivo
                  </button>
                  <span className="text-gray-600 text-xs">•</span>
                  <button
                    type="button"
                    onClick={() => setSelectedFile(null)}
                    className="text-[11px] text-rose-400 hover:text-rose-300 underline font-medium"
                  >
                    Eliminar archivo
                  </button>
                </div>
              </div>
            </div>
          ) : (
            <div
              role="button"
              tabIndex={0}
              aria-label="Seleccionar o arrastrar archivo de base de datos"
              onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
              onDragLeave={() => setIsDragging(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  fileInputRef.current?.click();
                }
              }}
              className={`border-2 border-dashed rounded-2xl p-4 sm:p-5 text-center cursor-pointer transition-colors ${
                isDragging
                  ? 'border-purple-500 bg-purple-500/10'
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
                accept=".sqlite,.db,.sqlite3,.sql,.csv,.xlsx,.xls,.tsv,.txt"
                className="hidden"
              />
              <div className="space-y-1.5 flex flex-col items-center py-2">
                <div className="w-10 h-10 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center border border-purple-500/20">
                  <UploadCloud className="w-5 h-5" />
                </div>
                <div>
                  <div className="text-xs font-semibold text-gray-200">
                    Haz clic para seleccionar o arrastra tu archivo aquí
                  </div>
                  <p className="text-[10px] text-gray-400 mt-0.5">
                    Soporta SQLite (.sqlite, .db), Excel (.xlsx, .xls), CSV (.csv) y SQL (.sql)
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Database Name Field */}
          <div className="space-y-1.5">
            <label htmlFor="upload-custom-name" className="block text-xs font-semibold text-gray-300">
              Nombre de la Fuente BD (Visualización)
            </label>
            <input
              id="upload-custom-name"
              type="text"
              value={customName}
              onChange={(e) => setCustomName(e.target.value)}
              placeholder="ej. REPORTE_SUBVENCIONES_2026, BD_FINANZAS"
              className="w-full bg-dark-base border border-dark-border rounded-xl px-3.5 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 transition-colors"
            />
            <p className="text-[10px] text-gray-400">
              Se creará un conector SQLite local con permisos y catalogación semántica automática.
            </p>
          </div>
        </form>

        {/* Fixed Sticky Footer Actions (ALWAYS 100% VISIBLE) */}
        <div className="shrink-0 px-5 sm:px-6 py-3.5 border-t border-dark-border bg-dark-surface/95 backdrop-blur flex items-center justify-end space-x-2.5 z-10">
          <button
            type="button"
            onClick={handleClose}
            disabled={isUploading}
            className="px-4 py-2 rounded-xl bg-dark-card hover:bg-dark-border text-gray-300 text-xs font-medium transition-colors"
          >
            Cancelar
          </button>

          <button
            form="db-upload-modal-form"
            type="submit"
            disabled={!selectedFile || isUploading}
            className="flex items-center space-x-2 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-semibold px-5 py-2 rounded-xl shadow-lg shadow-purple-600/30 transition-colors disabled:opacity-50 disabled:pointer-events-none"
          >
            {isUploading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Procesando e Indexando...</span>
              </>
            ) : (
              <>
                <Check className="w-4 h-4" />
                <span>Importar a la Base de Datos</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
