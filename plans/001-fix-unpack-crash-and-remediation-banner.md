# Plan 001: Corrección de Caída por Desempaquetado en Consultas Vacías y Banner de Remediación

**Commit de referencia:** `c5f1af4`  
**Prioridad:** Inmediata (Fase 0 - Estabilización de Línea Base)  
**Complejidad:** S (Bajo esfuerzo, cambios puntuales y seguros)  
**Riesgo:** BAJO  

> **Estado: ✅ IMPLEMENTADO.** Verificado contra el árbol actual: el retorno de
> `build_dynamic_visualization` es de 5 elementos en la rama vacía
> (`kpi_calculator.py:155-168`), `engine.py:25` importa `logger`, y el banner se
> antepone con `if is_remediation:` sin depender de `conversational`
> (`engine.py:530-532`). Documento conservado como registro.

---

## 🎯 Contexto y Problema

1. En [`backend/app/modules/chat_engine/kpi_calculator.py#L46-L60`](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/backend/app/modules/chat_engine/kpi_calculator.py#L46-L60), la función `build_dynamic_visualization` retorna 6 elementos cuando `rows` o `columns` está vacío:
   ```python
   return kpis, "bar", chart_option, summary, exec_rep, []
   ```
   En todos los demás retornos de la misma función se retornan 5 elementos (`kpis, chart_type, chart_option, summary, exec_rep`).
   En [`backend/app/modules/chat_engine/engine.py#L675`](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/backend/app/modules/chat_engine/engine.py#L675), el llamador desempaqueta 5 variables. Si una consulta devuelve cero registros, la aplicación sufre una caída fatal con `ValueError: too many values to unpack (expected 5, got 6)`.

2. En [`backend/app/modules/chat_engine/engine.py#L401`](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/backend/app/modules/chat_engine/engine.py#L401), se invoca `logger.warning(...)` sin haber importado `logger`, lo que causa `NameError` ante cualquier fallo de remediación.

3. En [`backend/app/modules/chat_engine/engine.py#L720-L725`](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/backend/app/modules/chat_engine/engine.py#L720-L725), la adición del banner de remediación solo se realiza si `conversational` es verdadero (`if conversational:`). Cuando el LLM local está desconectado, `conversational` es `None`, por lo que el banner nunca se concatena y `conversational_response` queda como `None`, haciendo fallar la prueba [`backend/tests/test_null_policy_and_visualizations.py#L280`](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/backend/tests/test_null_policy_and_visualizations.py#L280).

---

## 📁 Archivos en Alcance
- [`backend/app/modules/chat_engine/kpi_calculator.py`](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/backend/app/modules/chat_engine/kpi_calculator.py)
- [`backend/app/modules/chat_engine/engine.py`](file:///c:/Users/Felipe/Desktop/Proyectos/democratizacion%20de%20datos/backend/app/modules/chat_engine/engine.py)

**Archivos fuera de alcance:** Cualquier otro archivo de backend o frontend.

---

## 🛠️ Pasos de Implementación

### Paso 1: Corregir firma y retorno en `kpi_calculator.py`
1. En la línea 46, ajustar el tipo de retorno:
   ```python
   def build_dynamic_visualization(
       cls,
       question: str,
       columns: List[str],
       rows: List[Dict[str, Any]],
       user_role: str = "Economista"
   ) -> Tuple[List[KPICard], str, Dict[str, Any], str, Optional[ExecutiveReport]]:
   ```
2. En la línea 59, remover la lista residual `[]`:
   ```python
   return kpis, "bar", chart_option, summary, exec_rep
   ```

### Paso 2: Importar `logger` en `engine.py`
En el encabezado de `backend/app/modules/chat_engine/engine.py`, añadir:
```python
from app.core.logging import logger
```

### Paso 3: Asegurar la inyección del banner de remediación en `engine.py`
En las líneas 720-725 de `engine.py`, reemplazar:
```python
if is_remediation:
    action_labels = {
        "delete_rows": "Eliminación de registros con nulos",
        "mode": "Adaptación a la moda estadística",
        "nearest": "Adaptación al valor más cercano"
    }
    lbl = action_labels.get(remediation_action, remediation_action)
    banner = f"✅ **Tratamiento de nulos ({lbl}) aplicado para responder a:** *\"{effective_question}\"*\n\n"
    if conversational:
        conversational = banner + conversational
    else:
        conversational = banner + (fallback_summary or "")
    if fallback_summary:
        fallback_summary = banner + fallback_summary
```

---

## ✅ Criterios de Aceptación y Verificación

1. **Prueba unitaria de retorno vacío sin caída:**
   Ejecutar una prueba que invoque `QueryEngine.execute_query` con un SQL como `SELECT * FROM dim_categorias WHERE 1=0` y validar que el resultado tenga `status_code 200` y `kpis` válidos sin lanzar `ValueError`.
2. **Suite de pruebas de nulos pasando al 100%:**
   Comando de verificación:
   ```bash
   cd backend
   py -m pytest tests/test_null_policy_and_visualizations.py -v
   ```
   **Resultado esperado:** Las 8 pruebas deben pasar en verde (`8 passed in ...s`).
3. **TypeScript compilando:**
   ```bash
   npx tsc --noEmit
   ```
   **Resultado esperado:** Salida limpia sin errores de compilación.
