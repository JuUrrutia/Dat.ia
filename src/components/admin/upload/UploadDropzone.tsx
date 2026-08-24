import React from 'react';
import { Database, FileSpreadsheet, FileText, UploadCloud } from 'lucide-react';

interface UploadDropzoneProps {
  selectedFile: File | null;
  fileInputRef: React.RefObject<HTMLInputElement>;
  isDragging: boolean;
  setIsDragging: (val: boolean) => void;
  handleFileChange: (file: File) => void;
  handleDrop: (e: React.DragEvent<HTMLDivElement>) => void;
  onRemoveFile: () => void;
}

export const UploadDropzone: React.FC<UploadDropzoneProps> = ({
  selectedFile,
  fileInputRef,
  isDragging,
  setIsDragging,
  handleFileChange,
  handleDrop,
  onRemoveFile,
}) => {
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

  if (selectedFile && fileBadge) {
    return (
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
              onClick={onRemoveFile}
              className="text-[11px] text-rose-400 hover:text-rose-300 underline font-medium"
            >
              Eliminar archivo
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
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
      <div className="space-y-2 flex flex-col items-center">
        <div className="w-10 h-10 rounded-xl bg-purple-500/10 text-purple-400 flex items-center justify-center border border-purple-500/20">
          <UploadCloud className="w-5 h-5" />
        </div>
        <div className="space-y-0.5">
          <p className="text-xs font-semibold text-white">
            Arrastra tu archivo aquí o haz clic para examinar
          </p>
          <p className="text-[11px] text-gray-400">
            Soporta SQLite (.sqlite, .db), Excel (.xlsx, .xls) y CSV (.csv, .tsv)
          </p>
        </div>
      </div>
    </div>
  );
};
