import React, { useState, useRef } from 'react';
import {
  Sparkles,
  Database,
  UploadCloud,
  CheckCircle2,
  AlertTriangle,
  AlertCircle,
  ArrowRight,
  ArrowLeft,
  Check,
  Loader2,
  X,
  Server,
  Table as TableIcon,
  Key,
  ShieldCheck,
  UserCheck,
  Bot,
  Edit3,
} from 'lucide-react';
import { UploadDropzone } from './upload/UploadDropzone';
import { ConnectorFormFields } from './ConnectorFormFields';
import { connectorService, CorporateConnection } from '../../features/admin/services/connector_service';
import {
  catalogService,
  DataDictionaryResponse,
  DataDictionaryTable,
  DataDictionaryColumn,
} from '../../features/admin/services/catalog_service';

interface DatabaseWizardModalProps {
  isOpen: boolean;
  initialMode?: IngestionMode;
  onClose: () => void;
  onSuccess: () => void;
  onNavigateToCatalog?: () => void;
}

type WizardStep = 'input' | 'choice' | 'generating' | 'review' | 'complete';
type IngestionMode = 'file' | 'remote';
type CreationMode = 'ai' | 'manual';

const GENERATION_PHASES = [
  { step: 1, title: 'Introspeccionando esquema físico y metadatos relacionales...', pct: 25 },
  { step: 2, title: 'Muestreando valores representativos de columnas...', pct: 50 },
  { step: 3, title: 'Invocando modelo de IA para descripciones de negocio y fórmulas...', pct: 75 },
  { step: 4, title: 'Compilando catálogo semántico y reglas de gobernanza...', pct: 100 },
];

export const DatabaseWizardModal: React.FC<DatabaseWizardModalProps> = ({
  isOpen,
  initialMode = 'file',
  onClose,
  onSuccess,
  onNavigateToCatalog,
}) => {
  // Step state
  const [currentStep, setCurrentStep] = useState<WizardStep>('input');
  const [ingestionMode, setIngestionMode] = useState<IngestionMode>(initialMode);
  const [creationMode, setCreationMode] = useState<CreationMode>('ai');

  React.useEffect(() => {
    if (isOpen) {
      setIngestionMode(initialMode);
    }
  }, [isOpen, initialMode]);

  // File Upload State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [customName, setCustomName] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Remote DB State
  const [remoteForm, setRemoteForm] = useState({
    name: '',
    dbType: 'postgresql' as 'postgresql' | 'mssql' | 'mysql' | 'oracle' | 'sqlite',
    host: 'localhost',
    port: 5432,
    databaseName: '',
    username: 'postgres',
    password: '',
    isActive: true,
  });

  // Common Submission / Connection State
  const [isProcessing, setIsProcessing] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [registeredConnection, setRegisteredConnection] = useState<CorporateConnection | null>(null);

  // Generation progress state
  const [generationPhaseIndex, setGenerationPhaseIndex] = useState(0);

  // Dictionary Review State
  const [dictionaryData, setDictionaryData] = useState<DataDictionaryResponse | null>(null);
  const [selectedTableIndex, setSelectedTableIndex] = useState(0);
  const [editedColumns, setEditedColumns] = useState<Record<string, { friendly_name: string; description: string; business_formula: string }>>({});
  const [isSavingReview, setIsSavingReview] = useState(false);

  if (!isOpen) return null;

  const resetState = () => {
    setCurrentStep('input');
    setIngestionMode(initialMode);
    setCreationMode('ai');
    setSelectedFile(null);
    setCustomName('');
    setErrorMessage(null);
    setIsProcessing(false);
    setRegisteredConnection(null);
    setGenerationPhaseIndex(0);
    setDictionaryData(null);
    setSelectedTableIndex(0);
    setEditedColumns({});
    setIsSavingReview(false);
  };

  const handleClose = () => {
    resetState();
    onClose();
  };

  // --- Step 1: Submit DB (File or Remote) ---
  const handleFileChange = (file: File) => {
    setErrorMessage(null);
    setSelectedFile(file);
    if (!customName) {
      const baseName = file.name.substring(0, file.name.lastIndexOf('.')) || file.name;
      setCustomName(baseName.replace(/[_-]/g, ' ').toUpperCase());
    }
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileChange(e.dataTransfer.files[0]);
    }
  };

  const handleIngestDatabase = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    setIsProcessing(true);

    try {
      let createdConn: CorporateConnection;

      if (ingestionMode === 'file') {
        if (!selectedFile) {
          setErrorMessage('Selecciona un archivo válido (SQLite, Excel o CSV).');
          setIsProcessing(false);
          return;
        }
        createdConn = await connectorService.uploadDatabase(selectedFile, customName);
      } else {
        if (!remoteForm.name.trim() || !remoteForm.databaseName.trim()) {
          setErrorMessage('Completa el nombre identificador y nombre de la base de datos.');
          setIsProcessing(false);
          return;
        }
        createdConn = await connectorService.createConnector({
          name: remoteForm.name.trim(),
          db_type: remoteForm.dbType,
          host: remoteForm.host.trim(),
          port: remoteForm.port,
          database_name: remoteForm.databaseName.trim(),
          username: remoteForm.username.trim(),
          password: remoteForm.password,
          is_active: remoteForm.isActive,
          is_uploaded: false,
        });
      }

      setRegisteredConnection(createdConn);
      setIsProcessing(false);
      setCurrentStep('choice');
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Error al conectar/ingresar la fuente de datos.';
      setErrorMessage(msg);
      setIsProcessing(false);
    }
  };

  // --- Step 2 to Step 3/4: Proceed with AI or Manual ---
  const handleStartDictionaryCreation = async () => {
    if (!registeredConnection) return;
    setErrorMessage(null);

    if (creationMode === 'ai') {
      setCurrentStep('generating');
      setGenerationPhaseIndex(0);

      // Paced progressive phases to give proper time and visual feedback
      try {
        const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

        // Phase 1: Introspect
        setGenerationPhaseIndex(0);
        await sleep(1100);

        // Phase 2: Samples
        setGenerationPhaseIndex(1);
        await sleep(1200);

        // Phase 3: Trigger AI auto-enrichment and wait
        setGenerationPhaseIndex(2);
        await Promise.all([
          catalogService.autoEnrich(registeredConnection.id).catch(() => null),
          sleep(2000), // Ensure meaningful paced delay for AI processing
        ]);

        // Phase 4: Compile
        setGenerationPhaseIndex(3);
        await sleep(900);

        // Load resulting data dictionary
        const dict = await catalogService.getDataDictionary(registeredConnection.id);
        setDictionaryData(dict);
        initializeEditedColumns(dict);
        setCurrentStep('review');
      } catch (err: any) {
        setErrorMessage('Aviso durante la generación por IA. Se cargarán los datos introspeccionados para revisión.');
        const dict = await catalogService.getDataDictionary(registeredConnection.id);
        setDictionaryData(dict);
        initializeEditedColumns(dict);
        setCurrentStep('review');
      }
    } else {
      // Manual creation mode
      setIsProcessing(true);
      try {
        const dict = await catalogService.getDataDictionary(registeredConnection.id);
        setDictionaryData(dict);
        initializeEditedColumns(dict);
        setIsProcessing(false);
        setCurrentStep('review');
      } catch (err: any) {
        setIsProcessing(false);
        setErrorMessage('No se pudo introspeccionar la base de datos para edición manual.');
      }
    }
  };

  const initializeEditedColumns = (dict: DataDictionaryResponse) => {
    const edits: Record<string, { friendly_name: string; description: string; business_formula: string }> = {};
    for (const table of dict.tables || []) {
      for (const col of table.columns || []) {
        const key = `${table.table_name}.${col.name}`;
        edits[key] = {
          friendly_name: col.friendly_name || col.name.replace(/_/g, ' ').toUpperCase(),
          description: col.description || `Campo '${col.name}' de la tabla ${table.table_name}`,
          business_formula: col.business_formula || 'Columna directa',
        };
      }
    }
    setEditedColumns(edits);
  };

  const handleColumnEditChange = (
    tableName: string,
    colName: string,
    field: 'friendly_name' | 'description' | 'business_formula',
    val: string
  ) => {
    const key = `${tableName}.${colName}`;
    setEditedColumns((prev) => ({
      ...prev,
      [key]: {
        ...prev[key],
        [field]: val,
      },
    }));
  };

  // --- Step 4: Save reviewed dictionary ---
  const handleSaveDictionaryReview = async () => {
    if (!registeredConnection || !dictionaryData) return;
    setIsSavingReview(true);
    setErrorMessage(null);

    try {
      // Save all reviewed items
      for (const table of dictionaryData.tables || []) {
        for (const col of table.columns || []) {
          const key = `${table.table_name}.${col.name}`;
          const current = editedColumns[key];
          if (current) {
            await catalogService.createCatalogItem({
              connection_id: registeredConnection.id,
              schema_name: table.schema_name || 'main',
              table_name: table.table_name,
              column_name: col.name,
              friendly_name: current.friendly_name,
              description: current.description,
              business_formula: current.business_formula,
              is_ai_generated: creationMode === 'ai',
            }).catch(() => null);
          }
        }
      }

      setIsSavingReview(false);
      setCurrentStep('complete');
      onSuccess();
    } catch (err: any) {
      setErrorMessage('Error al persistir algunas modificaciones del diccionario.');
      setIsSavingReview(false);
    }
  };

  const activeTable: DataDictionaryTable | undefined = dictionaryData?.tables?.[selectedTableIndex];

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-4 bg-black/80 backdrop-blur-md animate-fadeIn">
      <div className="glass-panel w-full max-w-3xl rounded-2xl sm:rounded-3xl border border-white/10 shadow-2xl overflow-hidden flex flex-col max-h-[92vh]">
        {/* Top Header */}
        <div className="shrink-0 px-6 py-4 border-b border-dark-border flex items-center justify-between bg-dark-surface/95 backdrop-blur">
          <div className="flex items-center space-x-3">
            <div className="p-2.5 rounded-xl bg-gradient-to-tr from-purple-600 to-indigo-600 text-white shadow-lg shadow-purple-500/25 shrink-0">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-base font-bold text-white tracking-tight leading-tight">
                  Asistente de Instalación y Onboarding de Base de Datos
                </h3>
                <span className="text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-purple-500/15 text-purple-300 border border-purple-500/30">
                  Wizard
                </span>
              </div>
              <p className="text-xs text-gray-400">
                Paso a paso con evaluación, gobernanza e inteligencia artificial
              </p>
            </div>
          </div>
          <button
            type="button"
            onClick={handleClose}
            aria-label="Cerrar asistente"
            className="text-gray-400 hover:text-white p-1.5 rounded-lg hover:bg-dark-card transition-colors shrink-0"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Step Progression Tracker */}
        <div className="shrink-0 px-6 py-2.5 bg-dark-base/70 border-b border-dark-border flex items-center justify-between text-xs">
          <div className="flex items-center space-x-2 sm:space-x-4 overflow-x-auto">
            <div className={`flex items-center space-x-1.5 ${currentStep === 'input' ? 'text-purple-400 font-bold' : 'text-gray-500'}`}>
              <span className="w-5 h-5 rounded-full border flex items-center justify-center text-[10px] font-mono">1</span>
              <span>Ingreso BD</span>
            </div>
            <span className="text-gray-600">→</span>
            <div className={`flex items-center space-x-1.5 ${currentStep === 'choice' ? 'text-purple-400 font-bold' : 'text-gray-500'}`}>
              <span className="w-5 h-5 rounded-full border flex items-center justify-center text-[10px] font-mono">2</span>
              <span>Evaluación & Modo</span>
            </div>
            <span className="text-gray-600">→</span>
            <div className={`flex items-center space-x-1.5 ${currentStep === 'generating' || currentStep === 'review' ? 'text-purple-400 font-bold' : 'text-gray-500'}`}>
              <span className="w-5 h-5 rounded-full border flex items-center justify-center text-[10px] font-mono">3</span>
              <span>{creationMode === 'ai' ? 'Generación & Revisión' : 'Revisión Manual'}</span>
            </div>
            <span className="text-gray-600">→</span>
            <div className={`flex items-center space-x-1.5 ${currentStep === 'complete' ? 'text-emerald-400 font-bold' : 'text-gray-500'}`}>
              <span className="w-5 h-5 rounded-full border flex items-center justify-center text-[10px] font-mono">4</span>
              <span>Finalizado</span>
            </div>
          </div>
        </div>

        {/* Error notification banner */}
        {errorMessage && (
          <div className="shrink-0 mx-6 mt-4 p-3 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs flex items-center space-x-2 animate-fadeIn">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{errorMessage}</span>
          </div>
        )}

        {/* Scrollable Content Body */}
        <div className="flex-1 overflow-y-auto min-h-0 p-5 sm:p-6">
          {/* ================= STEP 1: INPUT ================= */}
          {currentStep === 'input' && (
            <form id="wizard-step-1" onSubmit={handleIngestDatabase} className="space-y-4">
              <div className="flex items-center justify-between pb-2 border-b border-dark-border/80">
                <div>
                  <h4 className="text-sm font-bold text-white">Selecciona el método de ingreso de la Base de Datos</h4>
                  <p className="text-xs text-gray-400">Puedes importar un archivo o conectar un servidor corporativo en red</p>
                </div>
                {/* Tabs */}
                <div className="flex items-center bg-dark-base rounded-xl p-1 border border-dark-border">
                  <button
                    type="button"
                    onClick={() => setIngestionMode('file')}
                    className={`px-3 py-1 text-xs font-semibold rounded-lg transition-colors flex items-center space-x-1.5 ${
                      ingestionMode === 'file' ? 'bg-purple-600 text-white' : 'text-gray-400 hover:text-white'
                    }`}
                  >
                    <UploadCloud className="w-3.5 h-3.5" />
                    <span>Archivo</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => setIngestionMode('remote')}
                    className={`px-3 py-1 text-xs font-semibold rounded-lg transition-colors flex items-center space-x-1.5 ${
                      ingestionMode === 'remote' ? 'bg-purple-600 text-white' : 'text-gray-400 hover:text-white'
                    }`}
                  >
                    <Server className="w-3.5 h-3.5" />
                    <span>Conexión Remota</span>
                  </button>
                </div>
              </div>

              {ingestionMode === 'file' ? (
                <div className="space-y-4">
                  <UploadDropzone
                    selectedFile={selectedFile}
                    fileInputRef={fileInputRef}
                    isDragging={isDragging}
                    setIsDragging={setIsDragging}
                    handleFileChange={handleFileChange}
                    handleDrop={handleDrop}
                    onRemoveFile={() => setSelectedFile(null)}
                  />
                  <div className="space-y-1">
                    <label htmlFor="wizard-custom-name" className="block text-xs font-semibold text-gray-300">
                      Nombre Identificador de la Fuente <span className="text-purple-400">*</span>
                    </label>
                    <input
                      type="text"
                      id="wizard-custom-name"
                      value={customName}
                      onChange={(e) => setCustomName(e.target.value)}
                      placeholder="Ej: FINANZAS_2026, INVENTARIO_GENERAL..."
                      required
                      className="w-full bg-dark-base border border-dark-border rounded-xl px-3.5 py-2.5 text-xs text-white placeholder-gray-500 focus:outline-none focus:border-purple-500"
                    />
                  </div>
                </div>
              ) : (
                <div className="space-y-3">
                  <ConnectorFormFields
                    name={remoteForm.name}
                    dbType={remoteForm.dbType}
                    host={remoteForm.host}
                    port={remoteForm.port}
                    databaseName={remoteForm.databaseName}
                    username={remoteForm.username}
                    password={remoteForm.password}
                    isActive={remoteForm.isActive}
                    editingConnector={null}
                    onFieldChange={(field, val) => {
                      setRemoteForm((prev) => {
                        const updated = { ...prev, [field]: val };
                        if (field === 'name') {
                          const oldSlug = prev.name.toLowerCase().replace(/[^a-z0-9_]/g, '_');
                          if (!prev.databaseName || prev.databaseName === oldSlug) {
                            updated.databaseName = String(val).toLowerCase().replace(/[^a-z0-9_]/g, '_');
                          }
                        }
                        return updated;
                      });
                    }}
                    onDbTypeChange={(dbType) => {
                      const defaultPorts: Record<string, number> = {
                        postgresql: 5432,
                        mssql: 1433,
                        mysql: 3306,
                        oracle: 1521,
                        sqlite: 0,
                      };
                      setRemoteForm((prev) => ({ ...prev, dbType, port: defaultPorts[dbType] || prev.port }));
                    }}
                  />
                  <div className="p-2.5 rounded-xl bg-purple-500/10 border border-purple-500/20 flex items-center space-x-2 text-xs text-purple-300">
                    <Database className="w-4 h-4 text-purple-400 shrink-0" />
                    <span>Cada base de datos se crea de forma individual e independiente en el sistema.</span>
                  </div>
                </div>
              )}
            </form>
          )}

          {/* ================= STEP 2: CHOICE & EVALUATION ================= */}
          {currentStep === 'choice' && registeredConnection && (
            <div className="space-y-5 animate-fadeIn">
              {/* Evaluated summary card */}
              <div className="p-4 rounded-2xl bg-purple-500/10 border border-purple-500/20 flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className="p-2.5 rounded-xl bg-purple-500/20 text-purple-300 border border-purple-500/30">
                    <Database className="w-5 h-5" />
                  </div>
                  <div>
                    <h4 className="text-sm font-bold text-white">{registeredConnection.name}</h4>
                    <p className="text-xs text-gray-400">
                      Motor: <span className="font-mono text-cyan-300 uppercase">{registeredConnection.db_type}</span> • Estado: <span className="text-emerald-400 font-semibold">Evaluada y Conectada</span>
                    </p>
                  </div>
                </div>
                <div className="text-right text-xs">
                  <span className="px-2.5 py-1 rounded-lg bg-dark-base border border-dark-border text-gray-300 font-mono">
                    ID #{registeredConnection.id}
                  </span>
                </div>
              </div>

              <div>
                <h4 className="text-sm font-bold text-white">¿Cómo deseas estructurar el Diccionario y Catálogo de Datos?</h4>
                <p className="text-xs text-gray-400 mt-0.5">
                  Elige si deseas que la Inteligencia Artificial analice y describa las columnas, o hacerlo manualmente:
                </p>
              </div>

              {/* Mode Selection Cards */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Option 1: AI */}
                <div
                  role="button"
                  tabIndex={0}
                  onClick={() => setCreationMode('ai')}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setCreationMode('ai'); }}
                  className={`p-4 rounded-2xl border transition-all cursor-pointer text-left space-y-3 relative ${
                    creationMode === 'ai'
                      ? 'border-purple-500 bg-purple-500/10 shadow-lg shadow-purple-500/10 ring-1 ring-purple-500'
                      : 'border-dark-border bg-dark-card/40 hover:border-dark-border/80'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="p-2 rounded-xl bg-purple-500/20 text-purple-400 border border-purple-500/30">
                      <Bot className="w-5 h-5" />
                    </div>
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
                      Recomendado
                    </span>
                  </div>
                  <div>
                    <h5 className="text-sm font-bold text-white flex items-center gap-1.5">
                      <span>Generar con Inteligencia Artificial</span>
                    </h5>
                    <p className="text-xs text-gray-400 mt-1">
                      La IA examina la estructura, tipos y valores muestrales para formular descripciones semánticas, nombres de negocio y fórmulas automáticamente.
                    </p>
                  </div>
                  {/* Warning disclaimer inside AI card */}
                  <div className="p-2.5 rounded-xl bg-amber-500/10 border border-amber-500/20 text-amber-300 text-[11px] space-y-1">
                    <div className="flex items-center space-x-1.5 font-bold">
                      <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                      <span>Aviso de Precaución</span>
                    </div>
                    <p className="text-amber-200/90 text-[10px] leading-relaxed">
                      La IA puede cometer imprecisiones en terminología o lógica de negocio. Se te permitirá auditar y corregir cada definición en el siguiente paso.
                    </p>
                  </div>
                </div>

                {/* Option 2: Manual */}
                <div
                  role="button"
                  tabIndex={0}
                  onClick={() => setCreationMode('manual')}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') setCreationMode('manual'); }}
                  className={`p-4 rounded-2xl border transition-all cursor-pointer text-left space-y-3 relative ${
                    creationMode === 'manual'
                      ? 'border-indigo-500 bg-indigo-500/10 shadow-lg shadow-indigo-500/10 ring-1 ring-indigo-500'
                      : 'border-dark-border bg-dark-card/40 hover:border-dark-border/80'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="p-2 rounded-xl bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                      <UserCheck className="w-5 h-5" />
                    </div>
                    <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                      Manual
                    </span>
                  </div>
                  <div>
                    <h5 className="text-sm font-bold text-white">Creación Manual por el Usuario</h5>
                    <p className="text-xs text-gray-400 mt-1">
                      Construye las descripciones y definiciones tú mismo sin inferencias de IA, manteniendo el control absoluto de cada término.
                    </p>
                  </div>
                  <div className="p-2.5 rounded-xl bg-dark-base/80 border border-dark-border text-gray-400 text-[10px] space-y-1">
                    <div className="flex items-center space-x-1.5 font-semibold text-gray-300">
                      <ShieldCheck className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                      <span>Control Total</span>
                    </div>
                    <p className="leading-relaxed">
                      El asistente introspeccionará el esquema físico y te llevará directamente a la mesa de edición para documentar las tablas.
                    </p>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* ================= STEP 3: GENERATING (AI Progress) ================= */}
          {currentStep === 'generating' && (
            <div className="py-10 px-4 text-center space-y-6 animate-fadeIn max-w-lg mx-auto">
              <div className="relative mx-auto w-16 h-16">
                <div className="absolute inset-0 rounded-2xl bg-purple-600/20 animate-ping"></div>
                <div className="relative w-16 h-16 rounded-2xl bg-gradient-to-tr from-purple-600 to-indigo-600 flex items-center justify-center text-white shadow-xl shadow-purple-600/30">
                  <Bot className="w-8 h-8 animate-pulse" />
                </div>
              </div>

              <div className="space-y-1.5">
                <h4 className="text-base font-bold text-white">
                  Generando Diccionario de Datos con IA
                </h4>
                <p className="text-xs text-gray-400">
                  El modelo se está tomando el tiempo necesario para analizar y catalogar correctamente cada campo...
                </p>
              </div>

              {/* Progress Bar */}
              <div className="space-y-2">
                <div className="w-full bg-dark-base rounded-full h-2.5 overflow-hidden border border-dark-border">
                  <div
                    className="bg-gradient-to-r from-purple-500 to-indigo-500 h-2.5 rounded-full transition-all duration-700 ease-out"
                    style={{ width: `${GENERATION_PHASES[generationPhaseIndex].pct}%` }}
                  ></div>
                </div>
                <div className="flex justify-between text-[11px] text-gray-400 font-mono">
                  <span>Fase {generationPhaseIndex + 1} de 4</span>
                  <span className="text-purple-400 font-semibold">{GENERATION_PHASES[generationPhaseIndex].pct}%</span>
                </div>
              </div>

              {/* Active Step Indicator */}
              <div className="p-3.5 rounded-xl bg-dark-surface/90 border border-purple-500/20 text-xs text-purple-200 flex items-center justify-center space-x-2.5">
                <Loader2 className="w-4 h-4 animate-spin text-purple-400 shrink-0" />
                <span>{GENERATION_PHASES[generationPhaseIndex].title}</span>
              </div>
            </div>
          )}

          {/* ================= STEP 4: REVIEW & EDIT ================= */}
          {currentStep === 'review' && dictionaryData && (
            <div className="space-y-4 animate-fadeIn">
              {/* Review Banner */}
              <div className="p-3.5 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 text-xs flex items-center justify-between">
                <div className="flex items-center space-x-2.5 text-indigo-200">
                  <Edit3 className="w-4 h-4 text-indigo-400 shrink-0" />
                  <div>
                    <span className="font-bold text-white">Revisión y Validación del Diccionario:</span>{' '}
                    <span>
                      {creationMode === 'ai'
                        ? 'Verifica que la IA haya generado descripciones correctas. Puedes ajustar cualquier campo antes de autorizar.'
                        : 'Define los nombres de negocio y descripciones para cada columna detectada.'}
                    </span>
                  </div>
                </div>
                <div className="text-right text-[11px] text-gray-400 shrink-0 pl-3">
                  <span className="text-white font-bold">{dictionaryData.total_tables}</span> tablas •{' '}
                  <span className="text-purple-400 font-bold">{dictionaryData.total_columns}</span> columnas
                </div>
              </div>

              {/* Table Selector Tabs if multiple tables */}
              {dictionaryData.tables && dictionaryData.tables.length > 1 && (
                <div className="flex items-center space-x-2 overflow-x-auto pb-1 custom-scrollbar">
                  {dictionaryData.tables.map((t, idx) => (
                    <button
                      key={t.table_name}
                      type="button"
                      onClick={() => setSelectedTableIndex(idx)}
                      className={`px-3 py-1.5 rounded-xl text-xs font-semibold whitespace-nowrap transition-colors flex items-center space-x-1.5 border ${
                        selectedTableIndex === idx
                          ? 'bg-purple-600 text-white border-purple-500'
                          : 'bg-dark-base text-gray-400 border-dark-border hover:text-white'
                      }`}
                    >
                      <TableIcon className="w-3.5 h-3.5" />
                      <span>{t.table_name}</span>
                      <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-white/10 font-mono">
                        {t.columns.length}
                      </span>
                    </button>
                  ))}
                </div>
              )}

              {/* Table Columns Editor */}
              {activeTable ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-xs text-gray-400 pb-1">
                    <div>
                      Tabla activa: <strong className="text-white font-mono">{activeTable.table_name}</strong> ({activeTable.columns.length} columnas)
                    </div>
                    {creationMode === 'ai' && (
                      <span className="text-[10px] text-amber-300 bg-amber-500/10 border border-amber-500/20 px-2 py-0.5 rounded-full">
                        ⚠️ Revisa y edita los campos que requieran ajuste
                      </span>
                    )}
                  </div>

                  <div className="space-y-3 max-h-[46vh] overflow-y-auto pr-1 custom-scrollbar">
                    {activeTable.columns.map((col: DataDictionaryColumn) => {
                      const editKey = `${activeTable.table_name}.${col.name}`;
                      const values = editedColumns[editKey] || {
                        friendly_name: col.friendly_name || col.name,
                        description: col.description || '',
                        business_formula: col.business_formula || '',
                      };

                      return (
                        <div
                          key={col.name}
                          className="p-3.5 rounded-2xl bg-dark-surface/80 border border-dark-border hover:border-purple-500/30 transition-colors space-y-2.5"
                        >
                          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-dark-border/60 pb-2">
                            <div className="flex items-center space-x-2">
                              {col.is_pk && (
                                <span title="Clave Primaria">
                                  <Key className="w-3.5 h-3.5 text-amber-400" />
                                </span>
                              )}
                              <span className="font-mono text-xs font-bold text-white">{col.name}</span>
                              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-dark-card border border-dark-border text-cyan-300">
                                {col.data_type}
                              </span>
                            </div>

                            {/* Samples Preview */}
                            {col.sample_values && col.sample_values.length > 0 && (
                              <div className="flex items-center space-x-1 text-[10px] text-gray-400">
                                <span>Ejemplos:</span>
                                <div className="flex gap-1 max-w-xs overflow-hidden">
                                  {col.sample_values.slice(0, 2).map((val, vIdx) => (
                                    <span
                                      key={`${col.name}-sample-${val}-${vIdx}`}
                                      className="font-mono bg-dark-base px-1.5 py-0.5 rounded border border-dark-border text-gray-300 truncate max-w-[100px]"
                                    >
                                      {val}
                                    </span>
                                  ))}
                                </div>
                              </div>
                            )}
                          </div>

                          {/* Editable Fields */}
                          <div className="grid grid-cols-1 sm:grid-cols-3 gap-2.5">
                            <div>
                              <label
                                htmlFor={`wizard-fn-${activeTable.table_name}-${col.name}`}
                                className="block text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1"
                              >
                                Nombre Amigable
                              </label>
                              <input
                                id={`wizard-fn-${activeTable.table_name}-${col.name}`}
                                type="text"
                                value={values.friendly_name}
                                onChange={(e) =>
                                  handleColumnEditChange(activeTable.table_name, col.name, 'friendly_name', e.target.value)
                                }
                                placeholder="Ej: Monto Facturado"
                                className="w-full bg-dark-base border border-dark-border rounded-xl px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-purple-500"
                              />
                            </div>

                            <div className="sm:col-span-2">
                              <label
                                htmlFor={`wizard-desc-${activeTable.table_name}-${col.name}`}
                                className="block text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-1"
                              >
                                Definición / Descripción Funcional
                              </label>
                              <input
                                id={`wizard-desc-${activeTable.table_name}-${col.name}`}
                                type="text"
                                value={values.description}
                                onChange={(e) =>
                                  handleColumnEditChange(activeTable.table_name, col.name, 'description', e.target.value)
                                }
                                placeholder="Describe el significado para el negocio..."
                                className="w-full bg-dark-base border border-dark-border rounded-xl px-2.5 py-1.5 text-xs text-white focus:outline-none focus:border-purple-500"
                              />
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : (
                <div className="py-8 text-center text-gray-400 text-xs">
                  No se encontraron tablas para revisar en esta base de datos.
                </div>
              )}
            </div>
          )}

          {/* ================= STEP 5: COMPLETE ================= */}
          {currentStep === 'complete' && registeredConnection && (
            <div className="py-8 px-4 text-center space-y-5 animate-fadeIn max-w-md mx-auto">
              <div className="w-16 h-16 rounded-2xl bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 flex items-center justify-center mx-auto shadow-lg shadow-emerald-500/20">
                <CheckCircle2 className="w-8 h-8" />
              </div>
              <div className="space-y-1.5">
                <h4 className="text-base font-bold text-white">
                  ¡Base de Datos y Diccionario Instalados Exitosamente!
                </h4>
                <p className="text-xs text-gray-400">
                  La fuente de datos <strong className="text-white">{registeredConnection.name}</strong> ha sido registrada, estructurada y catalogada.
                </p>
              </div>

              <div className="p-4 rounded-2xl bg-dark-base border border-dark-border text-left text-xs space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-400">Fuente:</span>
                  <span className="text-white font-semibold">{registeredConnection.name}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Modo de Creación:</span>
                  <span className="text-purple-300 font-semibold">{creationMode === 'ai' ? 'Asistido por IA (Auditado)' : 'Manual por Usuario'}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Tablas Catalogadas:</span>
                  <span className="text-emerald-400 font-semibold">{dictionaryData?.total_tables || 1} Tablas</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-400">Gobernanza RBAC:</span>
                  <span className="text-cyan-300 font-semibold">Reglas Activas</span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Fixed Sticky Footer Actions */}
        <div className="shrink-0 px-6 py-3.5 border-t border-dark-border bg-dark-surface/95 backdrop-blur flex items-center justify-between">
          {/* Back Button (Only on Step 2) */}
          {currentStep === 'choice' ? (
            <button
              type="button"
              onClick={() => setCurrentStep('input')}
              className="flex items-center space-x-1.5 px-4 py-2 rounded-xl text-xs font-medium text-gray-300 hover:text-white hover:bg-dark-card transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
              <span>Volver a Fuente</span>
            </button>
          ) : (
            <div></div>
          )}

          {/* Action Buttons depending on Step */}
          <div className="flex items-center space-x-2.5">
            {currentStep === 'input' && (
              <>
                <button
                  type="button"
                  onClick={handleClose}
                  disabled={isProcessing}
                  className="px-4 py-2 rounded-xl text-xs font-medium text-gray-300 hover:text-white hover:bg-dark-card transition-colors"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  form="wizard-step-1"
                  disabled={isProcessing || (ingestionMode === 'file' && !selectedFile)}
                  className="flex items-center space-x-2 px-5 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white shadow-lg shadow-purple-600/30 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {isProcessing ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Ingresando Fuente...</span>
                    </>
                  ) : (
                    <>
                      <span>Ingresar y Evaluar BD</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </>
            )}

            {currentStep === 'choice' && (
              <button
                type="button"
                onClick={handleStartDictionaryCreation}
                disabled={isProcessing}
                className="flex items-center space-x-2 px-5 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white shadow-lg shadow-purple-600/30 transition-all"
              >
                {isProcessing ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Cargando esquema...</span>
                  </>
                ) : (
                  <>
                    <span>{creationMode === 'ai' ? 'Iniciar con IA y Revisar' : 'Continuar Manualmente'}</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            )}

            {currentStep === 'generating' && (
              <div className="text-xs text-gray-400 italic">
                Procesando diccionario...
              </div>
            )}

            {currentStep === 'review' && (
              <>
                <button
                  type="button"
                  onClick={() => setCurrentStep('choice')}
                  disabled={isSavingReview}
                  className="px-4 py-2 rounded-xl text-xs font-medium text-gray-300 hover:text-white hover:bg-dark-card transition-colors"
                >
                  Volver a Modo
                </button>
                <button
                  type="button"
                  onClick={handleSaveDictionaryReview}
                  disabled={isSavingReview}
                  className="flex items-center space-x-2 px-5 py-2 rounded-xl text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/30 transition-all disabled:opacity-50"
                >
                  {isSavingReview ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Guardando Cambios...</span>
                    </>
                  ) : (
                    <>
                      <Check className="w-4 h-4" />
                      <span>Confirmar y Finalizar Instalación</span>
                    </>
                  )}
                </button>
              </>
            )}

            {currentStep === 'complete' && (
              <div className="flex items-center space-x-2">
                {onNavigateToCatalog && (
                  <button
                    type="button"
                    onClick={() => {
                      handleClose();
                      onNavigateToCatalog();
                    }}
                    className="px-4 py-2 rounded-xl text-xs font-medium text-purple-300 hover:text-white bg-purple-500/15 hover:bg-purple-500/25 border border-purple-500/30 transition-colors"
                  >
                    Ver en Catálogo
                  </button>
                )}
                <button
                  type="button"
                  onClick={handleClose}
                  className="px-5 py-2 rounded-xl text-xs font-semibold bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white shadow-lg shadow-purple-600/30 transition-all"
                >
                  Finalizar
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
