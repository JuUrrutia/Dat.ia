# Plan 002: Confinamiento Estricto de Remediación de Nulos en Memoria (Zero Mutation Guardrail)

**Commit de referencia:** `c5f1af4`  
**Prioridad:** Crítica (Fase 1 - Blindaje de Seguridad y Gobernanza)  
**Complejidad:** M (Manejo de estado en memoria y desacoplamiento de mutación física)  
**Riesgo:** MEDIO (debe mantener intacta la experiencia conversacional)  

> **Estado: ⛔ NO IMPLEMENTADO — sigue siendo el plan pendiente.** El código actual
> conserva la mutación física: `engine.py:230` sigue llamando
> `apply_null_policy(...)`, que ejecuta `DELETE`/`UPDATE` sobre la base
> corporativa y hace `commit` (`null_manager.py:218-333`). La vía en memoria
> (`apply_in_memory_remediation`) existe y se usa en `engine.py:448`, pero
> convive con la escritura física. El hallazgo de la auditoría sigue vigente.

---

## 🎯 Contexto y Problema

Uno de los pilares esenciales de **Datia** es la **Gobernanza de Solo Lectura Estricta (`READ ONLY`)** y el aislamiento de datos (Cero Alteración de Bases de Datos Corporativas).

Sin embargo, en [`backend/app/modules/chat_engine/engine.py#L395-L402`](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/backend/app/modules/chat_engine/engine.py#L395-L402):
```python
if remediation_action and conn_record and db:
    try:
        NullManagerService.apply_null_policy(conn_record, remediation_action, db)
        conn_record.null_policy = 'open'
        db.commit()
    except Exception as ex:
        ...
```
Cuando un usuario en el chat elige una sugerencia de remediación (como "Tratar nulos en test_sales (eliminar registros con nulos)..."), el motor invoca `NullManagerService.apply_null_policy`, la cual ejecuta sentencias destructivas directas en la base de datos de origen:
```python
DELETE FROM "{schema_name}"."{tbl_name}" WHERE ...
UPDATE "{schema_name}"."{tbl_name}" SET "{c_name}" = ...
```
Esto borra o sobreescribe permanentemente datos corporativos reales del cliente en disco sin respaldo ni confirmación de superadministrador.

---

## 📁 Archivos en Alcance
- [`backend/app/modules/chat_engine/engine.py`](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/backend/app/modules/chat_engine/engine.py)
- [`backend/app/modules/catalog/services/null_manager.py`](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/backend/app/modules/catalog/services/null_manager.py)
- [`backend/tests/test_null_policy_and_visualizations.py`](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/backend/tests/test_null_policy_and_visualizations.py)

---

## 🛠️ Pasos de Implementación

### Paso 1: Desvincular `apply_null_policy` del flujo del motor de chat
En `backend/app/modules/chat_engine/engine.py`:
1. Remover la invocación a `NullManagerService.apply_null_policy(conn_record, remediation_action, db)` en las líneas 395-402.
2. La remediación para la consulta del chat ya se ejecuta limpiamente en memoria en las líneas 580-584:
   ```python
   if remediation_action and null_cols_in_rows:
       rows = NullManagerService.apply_in_memory_remediation(rows, columns, remediation_action)
       null_cols_in_rows = set()
       null_rows_count = 0
   ```
   Asegurar que esta transformación en memoria sea el único mecanismo aplicado durante el flujo interactivo de consulta.

### Paso 2: Proteger `apply_null_policy` para uso exclusivo administrativo
En `backend/app/modules/catalog/services/null_manager.py`:
1. Documentar explícitamente que `apply_null_policy` es una operación de mantenimiento físico reservada a administradores con confirmación previa.
2. Mantener `apply_in_memory_remediation` como la función canónica para la experiencia de usuario final en tiempo real.

### Paso 3: Agregar prueba de no-mutación en la suite de pruebas
En `backend/tests/test_null_policy_and_visualizations.py`:
1. Añadir una aserción en `test_prompt2_remediation_answers_original_question` que verifique que el número de registros en la tabla física de SQLite permanece inalterado (5 filas originales), mientras que `response.data_rows` contiene únicamente las filas limpias resultantes de la remediación en memoria.

---

## ✅ Criterios de Aceptación y Verificación

1. **Prueba de inmutabilidad de base de datos:**
   Al enviar una solicitud de remediación por chat:
   - Los datos retornados en el API (`response.data_rows`) reflejan el filtrado o imputación elegida.
   - Una consulta directa a la tabla física `SELECT COUNT(*) FROM test_sales` verifica que las filas originales con nulos **no fueron eliminadas** del archivo `.db` o servidor PostgreSQL.
2. **Ejecución de pruebas:**
   ```bash
   cd backend
   py -m pytest tests/test_null_policy_and_visualizations.py -v
   ```
   **Resultado esperado:** Todas las pruebas pasan satisfactoriamente.
