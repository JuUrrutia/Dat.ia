# Docker y Despliegue

> **Documento:** 26 - Docker y despliegue
> **Estado:** Vigente. Comandos y puertos verificados contra los compose y Dockerfiles.
> **Última actualización:** 30 de octubre de 2026
> **Guía rápida para el cliente:** [`../DOCKER-RAPIDO.md`](../DOCKER-RAPIDO.md)
> **Guía on-prem completa:** [`../deploy/README.md`](../deploy/README.md)

---

## 1. Tres formas de levantar Dat.ia

| Forma | Archivo | Para quién | Construye o descarga |
|---|---|---|---|
| **Desarrollo** | `docker-compose.yml` | Equipo, pruebas locales | Construye las imágenes |
| **Partner / demo** | `docker-compose.partner.yml` | Probar sin Node ni Python | Descarga imágenes publicadas |
| **On-prem** | `deploy/docker-compose.yml` | Cliente final | Descarga imágenes del release |

> No mezclar archivos: `docker compose -f docker-compose.yml -f docker-compose.partner.yml` hace que el primero mande `build:` y compile en vez de usar las imágenes.

---

## 2. Desarrollo (`docker-compose.yml`)

### 2.1 Arranque

```bash
cp .env.example .env
# completar FERNET_KEY, POSTGRES_PASSWORD y cambiar SECRET_KEY
docker compose up -d
```

Abrir `http://127.0.0.1/`.

### 2.2 Servicios

| Servicio | Imagen / build | Puerto publicado | Notas |
|---|---|---|---|
| `postgres` | `postgres:16.15-alpine` | **ninguno** | Volumen `postgres_data`; healthcheck `pg_isready` |
| `backend` | `backend/Dockerfile` | **ninguno** | Uvicorn en 8000; solo por red interna |
| `frontend` | `Dockerfile` | `127.0.0.1:80` y `127.0.0.1:5173` | Nginx sin privilegios en 8080 |

**Variables obligatorias** (compose usa `:?` y se niega a arrancar si faltan):

- `SECRET_KEY`
- `FERNET_KEY`
- `POSTGRES_PASSWORD`

### 2.3 Variables fijas del compose

| Variable | Valor | Motivo |
|---|---|---|
| `POSTGRES_SERVER` | `postgres` | Nombre del servicio en la red de compose |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Dentro del contenedor, `localhost` es el propio contenedor |
| `VITE_API_BASE_URL` | `/api/v1` | Nginx hace proxy; una URL absoluta quedaría horneada y rota |
| `ENVIRONMENT` | `production` | Rechaza la `SECRET_KEY` de desarrollo |
| `DEMO_MODE` | `false` por defecto | Evita cuentas con claves conocidas en instalaciones cliente |

> `VITE_*` se hornea en build-time. Cambiarla exige rebuild de la imagen, no solo `restart`.

---

## 3. Partner / demo (`docker-compose.partner.yml`)

Pensado para una máquina sin Node ni Python.

```bash
# Windows: doble clic en setup.bat
cp .env.example .env
# completar FERNET_KEY, POSTGRES_PASSWORD y SECRET_KEY
docker compose -f docker-compose.partner.yml up -d
```

| Servicio | Imagen | Puerto publicado |
|---|---|---|
| `postgres` | `k1ntsu/dat.ia:postgres` | ninguno |
| `backend` | `k1ntsu/dat.ia:backend` | `127.0.0.1:8000` |
| `frontend` | `k1ntsu/dat.ia:frontend` | `127.0.0.1:80` y `127.0.0.1:5173` |

**Diferencias con desarrollo:**

- `DEMO_MODE=true`: siembra el dataset y las cuentas demo.
- No construye: descarga imágenes.
- El backend **sí** publica 8000 en loopback (para depuración local).
- `DATIA_BIND_IP` permite cambiar la IP de bind; por defecto `127.0.0.1`.

### 3.1 Credenciales demo

| Usuario | Contraseña | Rol |
|---|---|---|
| `admin` | `admin123` | Administrador de Plataforma |
| `director` | `director123` | Director Ejecutivo |
| `economista` | `economista123` | Analista Financiero |
| `bi` | `bi123` | Analista de Datos & BI |

> Estas cuentas existen **solo** con `DEMO_MODE=true`. En una instalación de cliente el seed está apagado.

---

## 4. On-prem (`deploy/`)

### 4.1 Contenido del bundle

```
docker-compose.yml          stack de producción
docker-compose.gpu.yml      override NVIDIA
Caddyfile                   TLS opcional
.env.example                plantilla
setup.sh                    instalación inicial
preflight.sh                validación previa
backup.sh / restore.sh      respaldo y restauración
upgrade.sh                  actualización de imágenes
lib.sh                      helpers
README.md                   guía operativa
VERSION                     tag del release
```

### 4.2 Instalación

```bash
tar -xzf datia-deploy-v1.0.0.tar.gz
cd datia-deploy-v1.0.0
./preflight.sh
./setup.sh
```

`setup.sh` genera `.env`, valida Docker y levanta el stack. Para GPU:

```bash
docker compose -f docker-compose.yml -f docker-compose.gpu.yml up -d
```

### 4.3 Operación

```bash
# Estado
docker compose ps

# Logs
docker compose logs -f backend

# Backup
./backup.sh

# Restore
./restore.sh <archivo>

# Upgrade
./upgrade.sh
```

### 4.4 Air-gapped

```bash
# Cargar imágenes sin registry
docker load -i datia-images.tar

# Evitar pulls
export DATIA_SKIP_PULL=true
export DATIA_SKIP_MODEL_PULL=true
```

El modelo del LLM también debe estar disponible localmente (Ollama con el modelo ya descargado, o un endpoint privado).

### 4.5 TLS

| Opción | Cuándo |
|---|---|
| **A. LB/ingress de la empresa** | Ya existe terminación TLS |
| **B. Caddy en la misma VM** | No hay proxy; `deploy/Caddyfile` lo provee |

---

## 5. Imágenes

### 5.1 Backend (`backend/Dockerfile`)

| Aspecto | Implementación |
|---|---|
| Multi-etapa | `python:3.13-slim` builder + runtime |
| Dependencias | Ruedas precompiladas; instalación offline desde `/wheels` |
| Usuario | `datia`, UID 10001, sin shell |
| Puerto | 8000 |
| Healthcheck | `GET /health/ready` cada 15 s, `start-period` 60 s |
| Volumen | `/app/data_sources` |
| Proxy | `--proxy-headers --forwarded-allow-ips=*` (seguro dentro de compose) |

### 5.2 Frontend (`Dockerfile`)

| Aspecto | Implementación |
|---|---|
| Multi-etapa | `node:24.22.1-alpine` builder + nginx |
| Runtime | `nginxinc/nginx-unprivileged:1.31.7-alpine` |
| Puerto | 8080 (sin privilegios) |
| Healthcheck | `GET /healthz` cada 15 s |
| Config | `nginx.conf` como template |
| Seguridad | CSP, `nosniff`, `DENY`, `no-referrer`, `Permissions-Policy` |

### 5.3 Release

`.github/workflows/release.yml` se dispara con tags `v*`:

- Construye y publica imágenes en GHCR para `linux/amd64` y `linux/arm64`.
- Publica el bundle `datia-deploy-<tag>.tar.gz`.
- Un tag `vX.Y.Z-rc.N` sale como prerelease y no mueve `latest`.

> El release **no vuelve a correr la suite**: el tag debe apuntar a un commit que ya pasó CI.

---

## 6. Puertos y exposición

| Servicio | Interno | Desarrollo | Partner | On-prem |
|---|---|---|---|---|
| frontend | 8080 | `127.0.0.1:80`, `127.0.0.1:5173` | `127.0.0.1:80`, `127.0.0.1:5173` | Según `DATIA_BIND_IP` + Caddy |
| backend | 8000 | **no publicado** | `127.0.0.1:8000` | Según compose de deploy |
| postgres | 5432 | **no publicado** | **no publicado** | **no publicado** |

**Regla:** nada se publica en `0.0.0.0` por defecto. Exponer la app a la LAN es una decisión explícita, no un descuido de configuración.

---

## 7. Troubleshooting

| Síntoma | Causa | Solución |
|---|---|---|
| Compose no arranca | Falta `SECRET_KEY`, `FERNET_KEY` o `POSTGRES_PASSWORD` | Completar `.env` |
| Backend reinicia en bucle | `SECRET_KEY` de desarrollo con `ENVIRONMENT=production` | Generar una clave nueva |
| Postgres: "superuser password is not specified" | Se usó el compose de desarrollo sin `.env` | Usar `docker-compose.partner.yml` o completar `.env` |
| El chat dice "IA local no disponible" | Ollama no corre o está en `localhost` dentro del contenedor | `ollama serve` en el host; `host.docker.internal` en compose |
| Puerto 80 ocupado | Otro proceso en Windows | Cambiar a `127.0.0.1:8080:8080` y abrir `:8080` |
| Se perdieron los datasets | Se borró el volumen o se corrió fuera del layout | `docker compose down` sin `-v`; restaurar backup |
| Credenciales ilegibles | Se cambió `FERNET_KEY` | Restaurar la clave o recargar credenciales |
| Mac Apple Silicon lento | Emulación de imágenes `amd64` | Usar imágenes multi-arch del release o aceptar la emulación |
| Windows bloquea `setup.bat` | Archivo descargado de internet | Propiedades → Desbloquear, o `Unblock-File` |

### Comandos de diagnóstico

```bash
docker compose ps
docker compose logs -f backend
docker compose exec backend curl -fsS http://127.0.0.1:8000/health/ready
docker compose exec postgres pg_isready -U postgres
docker volume ls | grep datia
```

---

## 8. Backup y restore

| Script | Qué hace |
|---|---|
| `deploy/backup.sh` | `pg_dump` de metadata + archivo de `data_sources` |
| `deploy/restore.sh` | Restaura ambos desde un backup |
| `deploy/upgrade.sh` | Baja imágenes nuevas sin borrar volúmenes |

**Qué respaldar:**

- `postgres_data` (usuarios, permisos, catálogo, auditoría).
- `data_sources_data` (datasets subidos).

**Qué no se respalda:** el modelo del LLM (se vuelve a descargar o se copia aparte).

---

## 9. Seguridad del despliegue

| Control | Estado |
|---|---|
| Contenedores sin root | ✅ backend UID 10001; nginx unprivileged |
| Base y backend sin exposición pública | ✅ por defecto |
| Secretos obligatorios | ✅ `:?` en compose |
| Cabeceras de seguridad | ✅ nginx |
| Rate limiting | ✅ auth 10 r/m; API 20 r/s |
| TLS | ✅ opcional con Caddy/LB |
| Escaneo de imágenes | ❌ no configurado |
| Firma de imágenes | ❌ no configurado |

> La ausencia de escaneo y firma es deuda declarada, no una garantía implícita.

---

## 10. Documentos relacionados

- [Guía rápida Docker](../DOCKER-RAPIDO.md)
- [Guía on-prem](../deploy/README.md)
- [Manual técnico](23_MANUAL_TECNICO.md)
- [Requisitos no funcionales](20_REQUISITOS_NO_FUNCIONALES.md)
- [Diagramas de despliegue](22_DIAGRAMAS_UML.md)
