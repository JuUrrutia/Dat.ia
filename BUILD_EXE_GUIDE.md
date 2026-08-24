# 🚀 Guía: Generar archivo .EXE de Datia

## Requisitos Previos

Asegúrate de tener instalado:
- **Node.js** (v16 o superior) - [Descargar](https://nodejs.org/)
- **Python 3.9+** - [Descargar](https://www.python.org/)
- **Git** (opcional, pero recomendado)

## Pasos para Generar el .EXE

### Opción 1: Usar el Script Batch (Recomendado para Windows)

1. Abre una terminal en la carpeta raíz del proyecto:
   ```bash
   cd "d:\Duoc\8vo Semestre 2025\Capston\Datia"
   ```

2. Ejecuta el script batch:
   ```bash
   .\build-exe.bat
   ```

3. Espera a que termine (puede tomar 5-15 minutos)

4. Los archivos .EXE estarán en: **`dist/`**

---

### Opción 2: Usar npm directamente

1. Asegúrate de estar en la carpeta correcta:
   ```bash
   cd "d:\Duoc\8vo Semestre 2025\Capston\Datia"
   ```

2. Ejecuta el comando de build:
   ```bash
   npm run build:exe
   ```

3. Los archivos .EXE estarán en: **`dist/`**

---

### Opción 3: Paso a Paso Manual

Si necesitas hacer todo manualmente:

```bash
# Paso 1: Compilar TypeScript
npx tsc

# Paso 2: Construir Frontend con Vite
npm run build:frontend

# Paso 3: Empaquetar con electron-builder
npx electron-builder
```

---

## 📦 Archivos Generados

Después de compilar, encontrarás en la carpeta `dist/`:

| Archivo | Descripción |
|---------|-------------|
| `Datia-1.0.0.exe` | **Instalador NSIS** - Instala Datia en el sistema (recomendado para distribución) |
| `Datia-1.0.0-portable.exe` | **Portable** - Ejecutable independiente que no requiere instalación |
| `Datia-1.0.0.exe.blockmap` | Metadatos para actualizaciones |

---

## ✨ Características del Build

✅ **Aplicación Standalone** - No requiere Node.js ni Python instalados en la máquina del usuario
✅ **Icono Personalizado** - Incluye el logo de Datia
✅ **Atajo de Escritorio** - El instalador crea un atajo automáticamente
✅ **Menú Inicio** - Se agrega a Programas (Windows)
✅ **Sin Firma Digital** - Por ser certificado de desarrollo

---

## 🐛 Solución de Problemas

### Error: "electron-builder not found"
```bash
npm install --save-dev electron-builder
```

### Error: "Command not found: npx"
- Reinstala **Node.js** desde https://nodejs.org/
- Reinicia la terminal

### El build tarda mucho / se congela
- Es normal la primera vez (puede tomar 10-20 minutos)
- Asegúrate de tener al menos 2GB de RAM libre
- No cierres la terminal hasta que veas "✓ COMPILACION EXITOSA"

### Error de permisos en Windows
- Ejecuta la terminal como **Administrador**
- O coloca el proyecto en una carpeta donde tengas permisos de escritura

---

## 📋 Checklist Antes de Compilar

- [ ] Versión actualizada en `package.json`
- [ ] Tests pasando: `npm run backend:test`
- [ ] Sin errores TypeScript: `npx tsc --noEmit`
- [ ] El logo favicon está en `public/favicon.png`
- [ ] Las conversaciones se guardan correctamente
- [ ] Backend funciona correctamente

---

## 🎯 Distribución

### Para Usuarios Finales:

1. **Instalador NSIS** (`Datia-1.0.0.exe`)
   - Proporciona la mejor experiencia
   - Se instala como una aplicación normal
   - Ocupa ~200-300MB en disco

2. **Portable** (`Datia-1.0.0-portable.exe`)
   - Ninguna instalación requerida
   - Puedes llevarlo en un USB
   - Ocupa ~150-200MB

---

## 🔧 Personalización Avanzada

Si necesitas cambiar la configuración del build, edita:
- `electron-builder.config.js` - Configuración del empaquetador
- `package.json` - Versión y metadatos

Para más información: [electron-builder docs](https://www.electron.build/)

---

**¿Problemas?** Revisa la consola para mensajes de error específicos y ejecuta con el script batch para mejor feedback.
