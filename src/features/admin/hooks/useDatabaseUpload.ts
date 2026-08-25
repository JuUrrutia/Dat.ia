import { useState, useRef } from 'react';
import { connectorService } from '../../../services/connector_service';

export function useDatabaseUpload(onUploadSuccess: () => void, onClose: () => void) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [customName, setCustomName] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleClose = () => {
    setSelectedFile(null);
    setCustomName('');
    setErrorMessage(null);
    setSuccessMessage(null);
    setIsUploading(false);
    onClose();
  };

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

  return {
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
  };
}
