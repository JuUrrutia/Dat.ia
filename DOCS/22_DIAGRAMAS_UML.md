# Diagramas UML

> **Documento:** 22 - Diagramas UML y de despliegue
> **Estado:** Vigente. Diagramas generados desde el código, no desde un diseño previo.
> **Última actualización:** 30 de octubre de 2026
> **Herramienta:** Mermaid (renderiza en GitHub, GitLab y VS Code). Los PNG de `DOCS/imagenes/` son históricos y no se referencian.

---

## 1. Casos de uso

```mermaid
flowchart LR
    U(["Usuario<br/>consultor / analista"])
    D(["Directivo"])
    A(["Administrador"])
    C(["Oficial de<br/>cumplimiento"])
    O(["Operador"])

    subgraph Datia["Plataforma Dat.ia"]
        UC1["Iniciar sesión"]
        UC2["Consultar en<br/>lenguaje natural"]
        UC3["Ver dashboard<br/>y trazabilidad"]
        UC4["Proyectar<br/>serie temporal"]
        UC5["Exportar informe<br/>PDF / Excel"]
        UC6["Gestionar hilos<br/>y widgets"]
        UC7["Administrar usuarios,<br/>roles y dominios"]
        UC8["Administrar conexiones<br/>y catálogo"]
        UC9["Definir permisos<br/>de tabla y columna"]
        UC10["Auditar y exportar<br/>registros"]
        UC11["Desplegar, respaldar<br/>y actualizar"]
    end

    U --> UC1
    U --> UC2
    U --> UC3
    U --> UC6
    D --> UC1
    D --> UC3
    D --> UC5
    D --> UC4
    A --> UC1
    A --> UC7
    A --> UC8
    A --> UC9
    C --> UC10
    O --> UC11

    UC2 -.->|"incluye"| UC3
    UC4 -.->|"incluye"| UC3
    UC5 -.->|"extiende"| UC3
    UC2 -.->|"requiere"| UC1
    UC7 -.->|"requiere"| UC1
```

### Actores y alcance

| Actor | Casos que puede ejecutar |
|---|---|
| Usuario consultor | Login, consulta, dashboard, hilos, widgets |
| Analista / directivo | Además: proyecciones e informes |
| Administrador | Todo lo anterior + administración y permisos |
| Oficial de cumplimiento | Auditoría y exportación de logs |
| Operador | Fuera de la aplicación: despliegue y respaldo |

> El administrador **no** pasa por la matriz RBAC: `is_admin` devuelve todas las tablas y deja `blocked_columns` y `masked_columns` vacíos (`governance_guard.py:221-222,238-239,257-258`). Es una decisión de operación de la plataforma —quien administra conexiones necesita ver el esquema— y no un camino disponible para usuarios de negocio. Si se requiere que ni el admin vea una columna, hoy no está implementado.

---

## 2. Componentes

```mermaid
flowchart TB
    subgraph Frontend["Frontend React + Vite"]
        UI["Páginas y componentes"]
        CTX["AuthContext / ChatEngineProvider"]
        API["api_client.ts"]
    end

    subgraph Backend["Backend FastAPI"]
        R1["auth/router"]
        R2["admin_catalog/router"]
        R3["chat_engine/router"]
        R4["ml_forecast/router"]
        R5["telemetry_audit/router"]
        R6["system/router"]

        subgraph Engine["chat_engine"]
            E1["QueryEngine<br/>engine.py"]
            E2["IntentClassifier"]
            E3["SQLGenerator"]
            E4["ASTValidator"]
            E5["SQLExecutor"]
            E6["GovernanceGuard"]
            E7["DynamicSchemaPruning"]
            E8["NullHandler /<br/>NullManagerService"]
            E9["KpiCalculator"]
            E10["ResponseBuilder"]
            E11["LLMService"]
        end

        subgraph ML["ml_forecast"]
            M1["MLService"]
            M2["ForecastService"]
            M3["ml_models<br/>naive / mean / ols_trend"]
        end

        subgraph Reports["reports"]
            P1["ReportGenerator"]
            P2["PDFExporter"]
            P3["ExcelExporter"]
        end

        subgraph Catalog["admin_catalog + catalog"]
            K1["CatalogService"]
            K2["Importers<br/>CSV / Excel / SQLite / SQL"]
            K3["NullManagerService"]
        end

        SEC["core/security<br/>JWT + Fernet"]
        AUD["audit_logs"]
    end

    subgraph Data["Datos"]
        PG[("PostgreSQL<br/>metadata")]
        CORP[("PostgreSQL<br/>corporativo / demo")]
    end

    LLM[["LLM local<br/>Ollama / OpenAI-compatible"]]

    UI --> CTX --> API
    API -->|"/api/v1"| R1
    API --> R2
    API --> R3
    API --> R4
    API --> R5
    API --> R6

    R3 --> E1
    E1 --> E2
    E1 --> E6
    E1 --> E7
    E1 --> E3
    E3 --> E11
    E1 --> E4
    E1 --> E5
    E5 --> E4
    E1 --> E8
    E1 --> E9
    E1 --> E10

    E11 --> LLM
    E5 --> CORP
    E7 --> CORP

    R4 --> M1 --> M2 --> M3
    M1 --> E4
    M1 --> E5
    M1 --> E6

    R2 --> K1
    R2 --> K2
    R2 --> K3
    K2 --> CORP
    K3 --> CORP

    R1 --> SEC
    R1 --> PG
    E1 --> PG
    E6 --> PG
    M1 --> PG
    R5 --> AUD
    AUD --> PG
```

> El frontend nunca habla con el LLM ni con la base corporativa: solo con `/api/v1` a través de nginx. El backend es el único que ve credenciales y datos.

---

## 3. Clases del motor

```mermaid
classDiagram
    class QueryEngine {
        +execute_query(question, user_role, is_admin, db, role_id, connection_id, history, narrative_sink) QueryResponse
        +get_allowed_tables_for_role() Set~str~
        +get_blocked_columns_for_role() Set~str~
        +get_masked_columns_for_role() Set~str~
        +check_domain_governance() Optional~str~
        -_execute_conversational_branch(...) QueryResponse
        -_diagnose_empty_visibility(...) Tuple
        -_resolve_remediation_context(...) Tuple
    }

    class IntentClassifier {
        +classify_intent(question) str
        +detect_ambiguity_and_options(question, tables) List
        +generate_conversational_response(...) str
    }

    class SQLGenerator {
        +generate_candidate_sql(question, user_role, allowed_tables, db, ...) Tuple
    }

    class ASTValidator {
        +validate_and_secure_sql(sql, dialect, allowed_tables, blocked_columns, table_columns, is_admin) Tuple
        +extract_tables_from_query(sql, dialect) List~str~
        +generate_sql_explanation(sql, dialect) str
    }

    class SQLExecutor {
        +execute_raw_sql(target, sql, dialect) List~dict~
        +execute_with_self_healing(target, question, sql, allowed_tables, blocked_columns, table_columns_map, schema_context, is_llm_active, dialect, is_admin) Tuple
    }

    class GovernanceGuard {
        +get_allowed_tables_for_role(role, is_admin, db, role_id, connection_id) Set~str~
        +get_blocked_columns_for_role() Set~str~
        +get_masked_columns_for_role() Set~str~
    }

    class DynamicSchemaPruningService {
        +get_physical_db_tables(target) Set~str~
        +get_physical_table_columns(table, target, include_samples) List
        +prune_schema_for_question(...) str
    }

    class NullHandler {
        +inspect_nulls(rows) Tuple
        +build_null_alert_payload(rows, cols, count, table, question) Tuple
    }

    class NullManagerService {
        +audit_connection_nulls(conn) dict
        +apply_in_memory_remediation(rows, columns, action) List
        +apply_null_policy(conn, policy, db, confirm) dict
    }

    class KpiCalculator {
        +calculate_kpis(rows, columns, question) List
    }

    class ResponseBuilder {
        +build_analytics_response() QueryResponse
        +build_rbac_denied_response(question, reason) QueryResponse
        +build_execution_error_response(question, error, ms) QueryResponse
        +build_llm_offline_response(question, ms) QueryResponse
    }

    class LLMService {
        +generate_completion(prompt, system_prompt, temperature, max_tokens, base_url, model_name) str
        +stream_completion() AsyncIterator
        +resolve_model_for(base_url, model) str
    }

    class MLService {
        +projection_context(...) dict
        +analyze_question(...) dict
        +run_projection(...) dict
    }

    class ForecastService {
        +build_series(...) dict
    }

    class ml_models {
        +METHODS
        +build_projection(series, horizon, method) dict
    }

    class ReportGenerator {
        +generate_pdf(req) bytes
        +generate_excel(req) bytes
        -_prepare_export(db, user, req, include_chart_image) Tuple
    }

    QueryEngine --> IntentClassifier
    QueryEngine --> SQLGenerator
    QueryEngine --> ASTValidator
    QueryEngine --> SQLExecutor
    QueryEngine --> GovernanceGuard
    QueryEngine --> DynamicSchemaPruningService
    QueryEngine --> NullHandler
    QueryEngine --> NullManagerService
    QueryEngine --> KpiCalculator
    QueryEngine --> ResponseBuilder
    SQLGenerator --> LLMService
    SQLExecutor --> ASTValidator
    SQLExecutor --> LLMService
    MLService --> ForecastService
    ForecastService --> ml_models
    MLService --> ASTValidator
    MLService --> SQLExecutor
    MLService --> GovernanceGuard
    ReportGenerator --> PDFExporter
    ReportGenerator --> ExcelExporter
```

---

## 4. Secuencia — Inicio de sesión

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuario
    participant F as Frontend
    participant A as auth/router
    participant DB as PostgreSQL (metadata)
    participant S as security

    U->>F: usuario + contraseña
    F->>A: POST /api/v1/auth/login
    A->>DB: buscar usuario por username
    alt usuario inexistente o inactivo
        A-->>F: 401 credenciales inválidas
    else cuenta bloqueada
        A->>DB: leer locked_until
        A-->>F: 423 con minutos restantes
    else contraseña incorrecta
        A->>DB: incrementar failed_login_attempts
        alt llegó a 5
            A->>DB: locked_until = now + 15 min
        end
        A-->>F: 401 credenciales inválidas
    else credenciales válidas
        A->>DB: resetear intentos y locked_until
        A->>S: crear JWT con jti y expiración 24 h
        A->>DB: crear user_sessions(jti, ip, user_agent)
        A-->>F: access_token + perfil + must_change_password
        alt must_change_password
            F-->>U: modal obligatorio de cambio
        else
            F-->>U: dashboard
        end
    end
```

---

## 5. Secuencia — Consulta en lenguaje natural

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuario
    participant F as Frontend
    participant R as chat_engine/router
    participant E as QueryEngine
    participant G as GovernanceGuard
    participant P as DynamicSchemaPruning
    participant L as LLMService
    participant V as ASTValidator
    participant X as SQLExecutor
    participant DB as PostgreSQL (corporativo)
    participant AU as audit_logs

    U->>F: pregunta en español
    F->>R: POST /api/v1/chat/query
    R->>E: execute_query(question, rol, conexión)
    E->>G: allowed_tables / blocked / masked
    alt error de permisos
        G-->>E: set() vacío (fail-closed)
    end
    E->>E: clasificar intención
    alt saludo o fuera de alcance
        E->>L: respuesta conversacional
        E-->>R: respuesta sin SQL
        R-->>F: mensaje
    else análisis de datos
        E->>P: esquema físico y columnas
        E->>L: prompt con esquema podado
        L-->>E: SQL candidato
        E->>V: validar y asegurar SQL
        alt SELECT inválido, tabla o columna prohibida
            V-->>E: ASTValidationError
            E-->>R: respuesta RBAC denegada
        else SQL válido
            E->>X: execute_with_self_healing
            X->>DB: ejecutar SELECT
            alt error no estructural
                X->>L: reparar SQL
                L-->>X: SQL corregido
                X->>V: revalidar
                X->>DB: reintentar una vez
            end
            DB-->>X: filas
            X-->>E: rows + SQL final + meta
            E->>E: mask_rows (MASKED)
            E->>E: detectar nulos / remediar en memoria
            E->>E: KPIs + gráfico + narrativa
            E->>AU: registrar consulta y snapshot
            E-->>R: QueryResponse
            R-->>F: dashboard + trazabilidad
        end
    end
```

> El orden importa: el enmascarado ocurre **antes** de que las filas alimenten KPIs, narrativa, snapshot de auditoría o exportación. Si se invierte, el dato sensible se filtra por un camino lateral.

---

## 6. Secuencia — Proyección ML

```mermaid
sequenceDiagram
    autonumber
    actor U as Usuario
    participant F as Frontend
    participant R as ml_forecast/router
    participant M as MLService
    participant G as GovernanceGuard
    participant FS as ForecastService
    participant V as ASTValidator
    participant X as SQLExecutor
    participant DB as PostgreSQL
    participant ML as ml_models

    U->>F: "proyecta ventas 6 meses"
    F->>R: POST /api/v1/ml/projections/run
    R->>M: run_projection(...)
    M->>G: tablas y columnas del rol
    M->>FS: construir serie histórica
    FS->>V: validar SQL de la serie
    FS->>X: ejecutar consulta
    X->>DB: SELECT serie
    DB-->>X: filas
    X-->>FS: serie
    FS-->>M: puntos históricos
    M->>ML: build_projection(serie, horizonte)
    ML->>ML: backtest walk-forward
    ML-->>M: método, banda, MAPE, beats_naive
    alt historia insuficiente
        M-->>R: disponible=false + motivo
    else proyección válida
        M-->>R: serie + banda + veredicto
    end
    R-->>F: tarjeta de proyección
    F-->>U: gráfico con banda y advertencia de honestidad
```

---

## 7. Secuencia — Política de nulos (escritura física)

```mermaid
sequenceDiagram
    autonumber
    actor A as Administrador
    participant F as Frontend
    participant R as admin_catalog/router
    participant N as NullManagerService
    participant DB as PostgreSQL (corporativo)
    participant AU as audit_logs

    A->>F: elegir política y confirmar
    F->>R: POST /catalog/connections/{id}/nulls-policy
    R->>R: get_current_admin
    alt no es admin
        R-->>F: 403
    else sin confirm=true
        R-->>F: 400 "requiere confirm=true"
    else autorizado
        R->>N: apply_null_policy(conn, policy, db, confirm)
        N->>DB: auditar nulos
        alt no hay nulos o auditoría incompleta
            N-->>R: no-op con motivo
        else hay nulos
            N->>DB: DELETE / UPDATE según política
            N->>AU: registrar acción
        end
        R-->>F: resultado
    end
```

> Este es el **único** camino que escribe en la base del cliente. El chat remedia en memoria (`apply_in_memory_remediation`) y nunca ejecuta `DELETE`/`UPDATE`.

---

## 8. Estados — Sesión

```mermaid
stateDiagram-v2
    [*] --> SinSesion
    SinSesion --> Autenticando: POST /auth/login
    Autenticando --> SinSesion: credenciales inválidas
    Autenticando --> Bloqueada: 5 intentos fallidos
    Bloqueada --> SinSesion: pasan 15 min
    Bloqueada --> SinSesion: admin restablece
    Autenticando --> ClaveTemporal: must_change_password
    ClaveTemporal --> Activa: cambio exitoso
    ClaveTemporal --> ClaveTemporal: intento inválido
    Autenticando --> Activa: credenciales válidas
    Activa --> Activa: request con token válido
    Activa --> Expirada: 24 h
    Activa --> Revocada: logout o revocación admin
    Expirada --> SinSesion
    Revocada --> SinSesion
    SinSesion --> [*]
```

---

## 9. Estados — Consulta

```mermaid
stateDiagram-v2
    [*] --> Recibida
    Recibida --> Denegada: sin rol o dominio prohibido
    Recibida --> Conversacional: saludo / fuera de alcance
    Recibida --> GenerandoSQL: análisis de datos
    GenerandoSQL --> Denegada: LLM no disponible
    GenerandoSQL --> Validando: SQL candidato
    Validando --> Denegada: tabla/columna prohibida o no-SELECT
    Validando --> Ejecutando: SQL aprobado
    Ejecutando --> Reparando: error no estructural
    Reparando --> Ejecutando: SQL reparado y revalidado
    Reparando --> Error: reparación fallida
    Ejecutando --> Error: error de base
    Ejecutando --> Enmascarando: filas obtenidas
    Enmascarando --> Respondiendo
    Conversacional --> Respondiendo
    Respondiendo --> Auditada
    Auditada --> [*]
    Denegada --> Auditada
    Error --> Auditada
```

---

## 10. Despliegue

```mermaid
flowchart TB
    subgraph Host["Host del cliente"]
        B["Navegador<br/>http://127.0.0.1"]
        subgraph Compose["docker compose"]
            FE["frontend<br/>nginx unprivileged<br/>:8080 interno<br/>publicado 127.0.0.1:80"]
            BE["backend<br/>uvicorn :8000<br/>sin puerto publicado"]
            PG[("postgres:16.15<br/>:5432 interno<br/>sin puerto publicado")]
            V1[("volume<br/>postgres_data")]
            V2[("volume<br/>data_sources_data")]
        end
        OLL["Ollama / llama.cpp<br/>:11434 en el host"]
        CADDY["Caddy / LB<br/>TLS opcional"]
    end

    B -->|"HTTP/HTTPS"| CADDY
    CADDY --> FE
    FE -->|"proxy /api/"| BE
    BE --> PG
    PG --- V1
    BE --- V2
    BE -->|"host.docker.internal:11434"| OLL
```

### Puertos reales

| Servicio | Puerto interno | Publicado (dev) | Publicado (partner) | Motivo |
|---|---|---|---|---|
| frontend | 8080 | `127.0.0.1:80` y `127.0.0.1:5173` | `127.0.0.1:80` y `127.0.0.1:5173` | Único punto de entrada; solo loopback |
| backend | 8000 | **ninguno** | `127.0.0.1:8000` | En dev se evita saltar nginx; en partner queda para depuración local |
| postgres | 5432 | **ninguno** | **ninguno** | La base no se expone al host |

> En Docker Desktop/Windows, publicar en `0.0.0.0` expone la app a la LAN. Ambos compose publican solo en loopback; para acceso desde otras máquinas se usa Caddy/LB con TLS (`deploy/README.md`). El partner compose permite cambiar la IP con `DATIA_BIND_IP`, que es una decisión explícita.

---

## 11. Notas de mantenimiento

- Los diagramas se escriben en Mermaid dentro del Markdown: no hay binarios que regenerar.
- Si cambia el pipeline del motor, se actualiza §5; si cambia el compose, §10.
- Los diagramas de `DOCS/imagenes/` están desactualizados (muestran puertos y fallback que ya no existen) y no deben citarse.
- Los diagramas no reemplazan al código: si hay contradicción, gana el código y el diagrama se corrige.

---

## 12. Documentos relacionados

- [Arquitectura técnica](02_ARQUITECTURA_TECNICA.md)
- [Modelo de datos](21_MODELO_DE_DATOS.md)
- [SRS](19_SRS.md)
- [Manual técnico](23_MANUAL_TECNICO.md)
- [Docker](26_DOCKER.md)
