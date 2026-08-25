import React from 'react';
import { UploadCloud, CheckCircle2, AlertCircle, X, Loader2, Database, Check } from 'lucide-react';
import { useDatabaseUpload } from '../../features/admin/hooks/useDatabaseUpload';
import { UploadDropzone } from './upload/UploadDropzone';

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
  const {
    selectedFile,
    setSelectedFile,
    customName,
    setCustomName,
    isUploading,
    errorMessage,
    successMessage,
    isDragging,
    setIsDragging,
    fileInputRef,
    handleFileChange,
    handleDrop,
    handleSubmit,
    handleClose,
  } = useDatabaseUpload(onUploadSuccess, onClose);

  if (!isOpen) return null;

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
          <UploadDropzone
            selectedFile={selectedFile}
            fileInputRef={fileInputRef}
            isDragging={isDragging}
            setIsDragging={setIsDragging}
            handleFileChange={handleFileChange}
            handleDrop={handleDrop}
            onRemoveFile={() => setSelectedFile(null)}
          />

          {/* Name Field */}
          <div className="space-y-1">
            <label htmlFor="db-upload-custom-name" className="block text-xs font-semibold text-gray-300">
              Nombre de la Fuente de Datos <span className="text-purple-400">*</span>
            </label>
            <input
              type="text"
              id="db-upload-custom-name"
              value={customName}
              onChange={(e) => setCustomName(e.target.value)}
              placeholder="Ej: Base de Ventas 2026, Nómina Enero..."
              required
              className="w-full bg-dark-base border border-dark-border rounded-xl px-3.5 py-2 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-purple-500 transition-colors"
            />
          </div>

          {/* Processing Info Notice */}
          <div className="p-3 rounded-xl bg-purple-500/5 border border-purple-500/20 text-[11px] text-purple-300/90 space-y-1">
            <div className="font-semibold text-purple-300 flex items-center gap-1.5">
              <Database className="w-3.5 h-3.5" /> Procesamiento Automático
            </div>
            <ul className="list-disc list-inside space-y-0.5 text-gray-400 text-[10px] pl-1">
              <li>Convierte hojas Excel / CSV a tablas relacionales SQLite.</li>
              <li>Genera permisos RBAC de consulta para roles autorizados.</li>
              <li>Inicializa el catálogo semántico y reglas de negocio.</li>
            </ul>
          </div>
        </form>

        {/* Fixed Footer with Action Buttons */}
        <div className="shrink-0 px-5 sm:px-6 py-3 border-t border-dark-border bg-dark-surface/95 backdrop-blur flex justify-end space-x-2.5">
          <button
            type="button"
            onClick={handleClose}
            disabled={isUploading}
            className="px-4 py-2 rounded-xl text-xs font-medium text-gray-300 hover:text-white hover:bg-dark-card transition-colors disabled:opacity-50"
          >
            Cancelar
          </button>
          <button
            type="submit"
            form="db-upload-modal-form"
            disabled={isUploading || !selectedFile || !customName.trim()}
            className="flex items-center space-x-2 px-5 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white shadow-lg shadow-purple-600/30 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {isUploading ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Importando...</span>
              </>
            ) : (
              <>
                <Check className="w-3.5 h-3.5" />
                <span>Registrar Base de Datos</span>
              </>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
