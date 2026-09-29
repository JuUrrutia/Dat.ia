# Plan 003: Gestión de Ciclo de Vida y Descarte de Motores SQLAlchemy (`Engine Registry`)

**Commit de referencia:** `c5f1af4`  
**Prioridad:** Alta (Fase 1 - Blindaje de Seguridad, Rendimiento y Fugas de Conexiones)  
**Complejidad:** M (Patrón Registry y descarte controlado de pools)  
**Riesgo:** MEDIO

---

## 🎯 Contexto y Problema

En [`backend/app/modules/chat_engine/sql_executor.py#L38-L60`](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/backend/app/modules/chat_engine/sql_executor.py#L38-L60), la ejecución de consultas relacionales contra PostgreSQL invoca:
```python
eng = build_engine_for_connector(target_db)
with eng.connect() as conn:
    ...
    return [cls._clean_row(dict(r._mapping)) for r in res.fetchall()]
```
O bien:
```python
eng = create_engine(target_db)
with eng.connect() as conn:
    ...
```
Cada llamada crea una nueva instancia de `sqlalchemy.Engine` con un pool de conexiones (`QueuePool` de 5 a 10 conexiones activas).
Al finalizar la consulta, la conexión específica se devuelve al pool, pero **el motor nunca se destruye (`eng.dispose()` jamás es llamado)**. En un servidor con decenas o cientos de interacciones de analítica, esto satura los límites de sockets abiertos y conexiones permitidas en PostgreSQL (`FATAL: remaining connection slots are reserved for non-replication superuser connections`).

---

## 📁 Archivos en Alcance
- [`backend/app/core/database.py`](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/backend/app/core/database.py)
- [`backend/app/modules/chat_engine/sql_executor.py`](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/backend/app/modules/chat_engine/sql_executor.py)

---

## 🛠️ Pasos de Implementación

### Paso 1: Crear un registro centralizado de motores en `database.py`
En `backend/app/core/database.py`:
1. Implementar la clase `ConnectorEngineRegistry` con almacenamiento de motores en caché indexados por `(connection_id, credentials_hash)`.
2. Incluir métodos `get_or_create_engine(conn)` y `dispose_connector_engine(connection_id)`.
3. Si se solicita un motor para un conector modificado o eliminado, liberar el anterior invocando `old_engine.dispose()`.

### Paso 2: Usar el registro en `sql_executor.py`
En `backend/app/modules/chat_engine/sql_executor.py`:
1. Reemplazar la creación ad-hoc de `create_engine` por la obtención del motor a través del registro gestionado.
2. Si se trata de una conexión efímera de cadena de conexión directa, asegurar un bloque `try...finally` donde se ejecute `eng.dispose()`.

### Paso 3: Conectar el descarte en el servicio de conectores
En `backend/app/modules/catalog/services/connector_service.py`:
Al actualizar credenciales o eliminar una conexión corporativa (`delete_connector`), invocar `ConnectorEngineRegistry.dispose_connector_engine(conn_id)` para cerrar proactivamente los sockets TCP remotos.

---

## ✅ Criterios de Aceptación y Verificación

1. **Prueba de contención de conexiones en PostgreSQL:**
   Ejecutar un script de prueba que dispare 50 consultas consecutivas sobre una conexión PostgreSQL registrada y verificar que el número de conexiones en `pg_stat_activity` se mantiene estable dentro del tamaño del pool configurado (sin crecimiento lineal de conexiones inactivas).
2. **Suite de pruebas pasando:**
   ```bash
   cd backend
   py -m pytest tests/test_catalog_and_connectors.py tests/test_postgres_compatibility.py -v
   ```
   **Resultado esperado:** Todas las pruebas pasan sin errores de desconexión.
