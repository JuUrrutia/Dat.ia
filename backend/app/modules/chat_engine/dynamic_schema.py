import os
import time
import re
import sqlite3
from typing import List, Dict, Set, Any, Optional, Tuple
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import discard_failed_transaction
from app.modules.admin_catalog.models import RoleTablePermission, RoleColumnPermission, ColumnPermissionType, SemanticCatalog, CorporateConnection, DatabaseType
from app.modules.auth.models import Role

class DynamicSchemaPruningService:
    """
    Filters database catalog definitions according to user role permissions
    and physically available tables in the active database engine.
    Ensures LLM context ONLY receives authorized & active physical tables.
    """

    _schema_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
    _SCHEMA_CACHE_TTL: float = 600.0  # 10 minutes cache to avoid constant disk/DB introspection

    # Introspeccion FISICA (que tablas existen, que columnas tienen). Es distinta de
    # `_schema_cache` a proposito: `_schema_cache` guarda el prompt ya armado y su
    # key incluye el texto de la pregunta, asi que entre dos preguntas distintas
    # nunca hay hit. Lo caro no es el armado, es la introscpeccion: `get_physical_*`
    # abre una conexion nueva (o un `create_engine` + `dispose()` contra el
    # Postgres del cliente) EN CADA llamada. Medido en un `POST /chat/query` con 10
    # tablas permitidas: ~30 aperturas, porque el cache del prompt se llenaba dos
    # veces (los guards de `governance_guard` llaman sin `query`, `sql_generator`
    # con `query=question` -> dos keys) y `engine.py` volca las columnas otra vez
    # por su cuenta. Ademas todo eso corre dentro de un `async def`, o sea
    # bloqueando el event loop entero.
    #
    # Cachear la INTROSPECCION y no el prompt es lo que baja de verdad el numero
    # de conexiones. La key se arma con los datos de la conexion (db_type, host,
    # port, database_name) y NO con `id(target)`: `target` es un objeto ORM
    # detached distinto en cada request, y una identidad que cambia haria que el
    # cache nunca acierte.
    _physical_cache: Dict[str, Tuple[float, Any]] = {}
    _PHYSICAL_CACHE_MAX: int = 512

    @classmethod
    def _physical_key(cls, target: Any) -> str:
        """Identidad estable de la base fisica a la que apunta `target`.

        `target` es un `CorporateConnection` (Postgres) o una ruta de fichero
        SQLite, y ambos determinan por completo que se va a leer.
        """
        if hasattr(target, "db_type"):
            return "pg|{}|{}|{}|{}".format(
                getattr(target, "db_type", ""),
                getattr(target, "host", "") or "",
                getattr(target, "port", "") or "",
                getattr(target, "database_name", "") or "",
            )
        path = target if (isinstance(target, str) and target) else settings.SQLITE_DB_PATH
        return f"sqlite|{path}"

    @classmethod
    def invalidate_schema_cache(cls, connection_id: Optional[int] = None) -> None:
        """Clears cached schema prompt representations (e.g. after table/column permissions or catalog changes)."""
        # La introscpeccion fisica se purga SIEMPRE, tambien cuando se filtra por
        # conexion: no se puede mapear `connection_id` a la key del cache fisico
        # sin volver a consultar la BD, y un DDL o una subida nueva tienen que
        # verse ya. Purgar de mas solo cuesta una re-introspeccion; purgarse de
        # menos seria servir columnas de una base que ya no existe.
        cls._physical_cache.clear()
        if connection_id is not None:
            cls._schema_cache = {k: v for k, v in cls._schema_cache.items() if not k.startswith(f"{connection_id}:")}
        else:
            cls._schema_cache.clear()

    @classmethod
    def resolve_db_path(cls, db: Optional[Session] = None, connection_id: Optional[int] = None) -> str:
        """Resolves target physical SQLite database path for active connection."""
        if db is not None:
            try:
                conn = None
                if connection_id:
                    conn = db.query(CorporateConnection).filter(CorporateConnection.id == connection_id).first()
                if not conn:
                    conn = db.query(CorporateConnection).filter(CorporateConnection.is_active == True).order_by(CorporateConnection.id.desc()).first()
                    if not conn:
                        conn = db.query(CorporateConnection).order_by(CorporateConnection.id.desc()).first()
                if conn and conn.db_type == DatabaseType.SQLITE:
                    if conn.host and os.path.exists(conn.host):
                        return conn.host
                    if conn.database_name and os.path.exists(conn.database_name):
                        return conn.database_name
            except Exception as ex:
                # Fallar aqui significa que NO sabemos a que base del cliente
                # apuntan los permisos ya calculados. Devolver `SQLITE_DB_PATH`
                # (la BD demo interna de Datia) ejecutaba la consulta del cliente
                # contra la base interna de la plataforma, con los permisos de otra
                # conexion: un fallo de resolucion se.convertia en una lectura de
                # otra base. Se falla cerrado y se propaga; el rollback deja la
                # sesion usable para el handler que lo reciba.
                discard_failed_transaction(db)
                raise RuntimeError(
                    f"No se pudo resolver la base de datos de la conexion {connection_id}: {ex}"
                ) from ex
        return settings.SQLITE_DB_PATH

    @classmethod
    def get_physical_cache(cls, key: str, compute):
        """Devuelve el valor cacheado de `key` o lo calcula con `compute()` y lo guarda.

        `compute` devuelve el valor crudo; la copia la hace el caller segun el
        tipo, porque un `set` y una `list` comparten el problema opuesto (el set
        mutable se puede mutar en el sitio, la list se puede appendear).

        Un resultado VACIO nunca se cachea, y esa es la parte que importa: los dos
        introspectores de abajo tragan su excepcion y devuelven `set()` / `[]`.
        Cachear eso convertiria un Postgres caido durante 30 s en diez minutos de
        "esta base no tiene tablas" para todo el mundo que consulta ahi. Es el
        mismo criterio que ya aplica `SchemaInspector` con
        `SchemaIntrospectionError` ("no se pudo leer" no es "base vacia"): el
        fallo se vuelve a intentar en la proxima llamada, que es lo que pasaba
        antes de este cache.
        """
        now = time.time()
        hit = cls._physical_cache.get(key)
        if hit is not None and now - hit[0] < cls._SCHEMA_CACHE_TTL:
            return hit[1]
        value = compute()
        if not value:
            return value
        # Se purga lo vencido ANTES de insertar y con un tope duro: la key
        # fisica no lleva el texto de la pregunta, pero si es una ruta de
        # fichero o una conexion que se reimporta, el dict no debe crecer sin
        # limite en un proceso de larga vida. `_schema_cache` tenia el mismo
        # problema (una entrada por pregunta, con el prompt entero adentro) y
        # por eso ahora se poda en el mismo paso.
        if len(cls._physical_cache) >= cls._PHYSICAL_CACHE_MAX:
            cls._physical_cache = {
                k: v for k, v in cls._physical_cache.items() if now - v[0] < cls._SCHEMA_CACHE_TTL
            }
            if len(cls._physical_cache) >= cls._PHYSICAL_CACHE_MAX:
                cls._physical_cache.clear()
        cls._physical_cache[key] = (now, value)
        return value

    @classmethod
    def get_physical_db_tables(cls, target: Any = None) -> Set[str]:
        """Inspects active PostgreSQL connection or SQLite database to retrieve physically existing data tables."""
        return set(cls.get_physical_cache(
            f"tables|{cls._physical_key(target)}", lambda: cls._introspect_tables(target)
        ))

    @classmethod
    def _introspect_tables(cls, target: Any) -> Set[str]:
        ignored_metadata = {
            "sqlite_sequence", "roles", "domains", "corporate_connections",
            "users", "role_domain_links", "role_table_permissions",
            "role_column_permissions", "semantic_catalog", "audit_logs",
            "user_sessions", "alembic_version"
        }

        # Case 1: PostgreSQL CorporateConnection object
        if hasattr(target, "db_type") and (target.db_type == DatabaseType.POSTGRESQL or str(target.db_type).lower() == "postgresql"):
            try:
                from sqlalchemy import inspect as sa_inspect
                from app.core.database import connector_engine
                with connector_engine(target) as eng:
                    inspector = sa_inspect(eng)
                    raw_tables = [t.lower() for t in inspector.get_table_names(schema="public")]
                    return {t for t in raw_tables if t not in ignored_metadata}
            except Exception:
                return set()

        # Case 2: SQLite database file path
        try:
            target_path = target if (isinstance(target, str) and target) else settings.SQLITE_DB_PATH
            if not target_path or not os.path.exists(target_path):
                return set()
            conn = sqlite3.connect(target_path)
            try:
                cursor = conn.cursor()
                raw_tables = [r[0].lower() for r in cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
            finally:
                conn.close()
            return {t for t in raw_tables if t not in ignored_metadata}
        except Exception:
            return set()

    @classmethod
    def _inspect_columns_with_engine(cls, eng, clean_table: str, include_samples: bool, sa_inspect) -> List[Dict[str, Any]]:
        """Inspecciona columnas con un engine ya abierto; el que lo llama lo dispone.

        Vive aparte para que el `dispose()` del engine cubra TODOS los caminos de
        salida, incluidos los `return` tempranos.
        """
        from sqlalchemy import text
        inspector = sa_inspect(eng)
        cols_info = inspector.get_columns(clean_table, schema="public")
        pk_info = inspector.get_pk_constraint(clean_table, schema="public")
        pk_cols = set(pk_info.get("constrained_columns", [])) if pk_info else set()

        col_samples_map: Dict[str, List[str]] = {}
        if include_samples:
            try:
                with eng.connect() as connection:
                    res = connection.execute(text(f'SELECT * FROM "{clean_table}" LIMIT 20'))
                    for row in res.mappings():
                        for k, val in row.items():
                            if val is not None and str(val).strip():
                                s_list = col_samples_map.setdefault(k, [])
                                val_str = str(val)[:35]
                                if val_str not in s_list and len(s_list) < 3:
                                    s_list.append(val_str)
            except Exception:
                pass

        result = []
        for col in cols_info:
            col_name = col["name"]
            result.append({
                "name": col_name,
                "type": str(col["type"]),
                "is_pk": col_name in pk_cols,
                "samples": col_samples_map.get(col_name, []),
            })
        return result

    @classmethod
    def get_physical_table_columns(cls, table_name: str, db_path: Any = None, include_samples: bool = True) -> List[Dict[str, Any]]:
        """
        Inspects active PostgreSQL connection or SQLite database file to retrieve real physical columns, data types,
        and representative sample values for automatic profiling of tables.
        """
        clean_table = "".join(c for c in table_name if c.isalnum() or c == "_")
        if not clean_table:
            return []
        # `include_samples` va EN la key, no como detalle del compute: el prompt
        # del LLM pide muestras y el ranking de tablas (`include_samples=False`)
        # no. Compartir la entrada devolveria en el prompt valores que el caller
        # pidio no leer.
        return [dict(c) for c in cls.get_physical_cache(
            f"cols|{cls._physical_key(db_path)}|{clean_table}|{int(include_samples)}",
            lambda: cls._introspect_columns(clean_table, db_path, include_samples),
        )]

    @classmethod
    def _introspect_columns(cls, clean_table: str, db_path: Any, include_samples: bool) -> List[Dict[str, Any]]:
        # Case 1: PostgreSQL CorporateConnection object
        if hasattr(db_path, "db_type") and (db_path.db_type == DatabaseType.POSTGRESQL or str(db_path.db_type).lower() == "postgresql"):
            try:
                from sqlalchemy import inspect as sa_inspect
                from app.core.database import connector_engine
                with connector_engine(db_path) as eng:
                    return cls._inspect_columns_with_engine(eng, clean_table, include_samples, sa_inspect)
            except Exception:
                return []

        # Case 2: SQLite database file
        try:
            target_path = db_path if (isinstance(db_path, str) and db_path) else settings.SQLITE_DB_PATH
            if not target_path or not os.path.exists(target_path):
                return []
            conn = sqlite3.connect(target_path)
            try:
                cursor = conn.cursor()
                rows = cursor.execute(
                    "SELECT cid, name, type, [notnull], dflt_value, pk FROM pragma_table_info(?)",
                    (clean_table,)
                ).fetchall()

                col_samples_map: Dict[str, List[str]] = {}
                if include_samples:
                    try:
                        conn.row_factory = sqlite3.Row
                        s_cursor = conn.cursor()
                        s_cursor.execute("SELECT * FROM " + clean_table + " LIMIT 20")
                        for row in s_cursor.fetchall():
                            for k in row.keys():
                                val = row[k]
                                if val is not None and str(val).strip():
                                    s_list = col_samples_map.setdefault(k, [])
                                    val_str = str(val)[:35]
                                    if val_str not in s_list and len(s_list) < 3:
                                        s_list.append(val_str)
                    except Exception:
                        pass

                result = []
                for r in rows:
                    col_name = r[1]
                    col_type = r[2] or "TEXT"
                    is_pk = bool(r[5])
                    samples = col_samples_map.get(col_name, [])

                    result.append({
                        "name": col_name,
                        "type": col_type,
                        "is_pk": is_pk,
                        "samples": samples
                    })

                return result
            finally:
                conn.close()
        except Exception:
            return []

    STOPWORDS = {
        "los", "las", "del", "por", "para", "con", "sin", "dime", "cuales", "cuáles",
        "que", "qué", "sobre", "entre", "una", "uno", "unos", "unas", "como", "cómo",
        "este", "esta", "estos", "estas", "todos", "todas", "tienen", "tiene", "dame",
        "mostrar", "muestra", "traer", "trae", "ver", "cada", "contra", "desde", "hasta",
        "pero", "the", "and", "for", "with", "from", "show", "get", "give"
    }

    GENERIC_WORDS = {
        "estado", "status", "fecha", "date", "nombre", "name", "id", "tipo",
        "type", "valor", "registro", "tabla", "descripcion", "description"
    }

    # El DDL se arma aparte del resto de metodos porque lo necesitan DOS
    # consumidores con formatos distintos: el prompt del LLM y el extractor de
    # sugerencias de `suggestions_service.py`, que hace regex sobre el prompt.
    # Antes cada uno parseaba el formato con vinetas por su cuenta y cambiar uno
    # obligaba a cambiar el otro sin que el error se notara en ninguno.

    @classmethod
    def _render_table_as_ddl(cls, table: str, table_synonyms: str, col_lines: List[str]) -> str:
        """Vuelca las lineas de columna de una tabla como `CREATE TABLE`.

        Por que DDL y no la lista con viñetas
        -------------------------------------
        El modelo base es un **Coder** (Qwen2.5-Coder): su preentrenamiento es
        mayoritariamente codigo, y dentro de el el esquema de una base aparece
        como `CREATE TABLE t (col TYPE, ...)`. Entregarle el mismo esquema en
        forma de lista con vinetas desperdicia la familiaridad que el modelo ya
        tiene: es la senal de que el prompt quiere que escriba SQL.

        `col_lines` sigue siendo la MISMA lista con vinetas que se usaba antes
        (`nombre (TIPO, ej: 'x') - descripcion`), y se parsea acá. Se preserva
        el formato de entrada a proposito: el resto de la construccion del prompt
        —filtrado de columnas bloqueadas, `[ENMASCARADO]`, sinonimos, limpieza de
        descripciones redundantes— no cambia, y el test que verifica que una
        formula de negocio llega al prompt sigue绿茶 pasando.
        """
        body: List[str] = []
        for raw in col_lines:
            name, _, rest = raw.partition(" ")
            name = name.strip()
            if not name:
                continue
            rest = rest.strip()

            # `rest` arranca con `(TIPO, ej: 'x')` y detras puede venir la
            # descripcion, los sinonimos y la marca de enmascarado.
            col_type = ""
            comment_parts: List[str] = []
            if rest.startswith("("):
                depth = 0
                close = -1
                for i, ch in enumerate(rest):
                    if ch == "(":
                        depth += 1
                    elif ch == ")":
                        depth -= 1
                        if depth == 0:
                            close = i
                            break
                if close > 0:
                    inner = rest[1:close]
                    # Solo el tipo: los ejemplos de valor van al comentario.
                    col_type = inner.split(", ej:")[0].strip()
                    tail = rest[close + 1:].strip()
                    if tail:
                        comment_parts.append(tail)
                else:
                    comment_parts.append(rest)
            elif rest:
                comment_parts.append(rest)

            # `rest` ya venia con el guion del formato viejo (` - descripcion`):
            # se saca para no dejar un `-- - descripcion` en el comentario del DDL.
            comment_parts = [
                c[1:].strip() if c.startswith("- ") else c.strip()
                for c in comment_parts
            ]
            comment_parts = [c for c in comment_parts if c]

            # Los ejemplos de valor se recuperan del parentesis original: son la
            # unica senal que tiene el modelo de COMO se ven los datos (fechas en
            # ISO, montos con puntos, estados en mayusculas) y sin eso inventa
            # literales que despues no matchean nada.
            samples = re.search(r", ej: ([^)]*)\)", rest)
            if samples and samples.group(1).strip():
                comment_parts.insert(0, f"ej: {samples.group(1).strip()}")

            line = f"  {name}"
            if col_type:
                line += f" {col_type}"
            if comment_parts:
                line += "  -- " + " ".join(comment_parts).strip()
            body.append(line)

        if not body:
            # Sin columnas no hay `CREATE TABLE` que valga: un bloque vacio le
            # dice al modelo que la tabla existe pero no tiene nada consultable,
            # que no es lo que dice "solo lectura".
            syn = f" (Sinónimos: {table_synonyms})" if table_synonyms else ""
            return f'Tabla "{table}"{syn} (Columnas de solo lectura)'

        header = f'CREATE TABLE "{table}" ('
        if table_synonyms:
            header += f"  -- Sinónimos: {table_synonyms}\n"
        return header + "\n" + ",\n".join(body) + "\n);"

    NON_FORMULAS = {
        "columna directa", "directa", "direct column", "direct", "none", "n/a",
        "texto literal", "clave primaria (pk)", "clave primaria", "pk",
        "dimensión de agrupación", "dimension de agrupacion",
        "identificador de transacción", "identificador de transaccion",
        "identificador de orden", "dimensión de centro", "dimension de centro",
        "dimensión de controlling", "dimension de controlling",
        "dimensión de almacén", "dimension de almacen",
        "número de ítem", "numero de item", "unidad de medida",
        "código iso de moneda", "codigo iso de moneda",
        "clasificación tributaria", "clasificacion tributaria",
        "clave de documento comercial", "filtro contable s/h",
        "clave foránea (mara)", "clave foránea (kna1)", "clave foránea (lfa1)",
        "clave foranea (mara)", "clave foranea (kna1)", "clave foranea (lfa1)",
        "identificador único", "identificador unico", "campo", "registro"
    }

    @classmethod
    def rank_relevant_tables(
        cls,
        allowed_tables: Set[str],
        query: Optional[str],
        catalog_entries: List[Any],
        target_db_target: Any
    ) -> Set[str]:
        """
        Heuristically ranks and selects a compact subset of tables (2 to 4) relevant
        to the user's natural language query, pruning out unrelated tables to fit local LLM context limits.
        """
        if not query or len(allowed_tables) <= 3:
            return allowed_tables

        import re
        raw_tokens = re.findall(r'[a-zA-ZáéíóúÁÉÍÓÚñÑ_]+', query.lower())
        query_words = {w for w in raw_tokens if len(w) >= 3 and w not in cls.STOPWORDS}

        if not query_words:
            return allowed_tables

        table_scores: Dict[str, int] = {t: 0 for t in allowed_tables}
        table_cols_map: Dict[str, List[str]] = {}

        for tbl in allowed_tables:
            cols = cls.get_physical_table_columns(tbl, target_db_target, include_samples=False)
            col_names = [c["name"].lower() for c in cols]
            table_cols_map[tbl] = col_names

            # Score table name parts
            parts = tbl.lower().split('_')
            for part in parts:
                if len(part) >= 3 and part not in ("dim", "fact", "tbl", "cat"):
                    if part in query_words or any(part in qw or qw in part for qw in query_words):
                        table_scores[tbl] += 12

            # Score columns
            for c in col_names:
                c_subwords = c.split('_')
                for qw in query_words:
                    if qw in cls.GENERIC_WORDS:
                        continue
                    if qw == c or qw in c_subwords:
                        table_scores[tbl] += 6
                    elif len(qw) >= 4 and (qw in c or c in qw):
                        table_scores[tbl] += 4

        # Score catalog descriptions / synonyms
        for entry in catalog_entries:
            tbl = (entry.table_name or "").lower()
            if tbl in table_scores:
                syns = (entry.synonyms or "").lower()
                desc = (entry.description or "").lower()
                for qw in query_words:
                    if qw in syns:
                        table_scores[tbl] += 5
                    elif qw in desc:
                        table_scores[tbl] += 2

        scored_tables = [(t, s) for t, s in table_scores.items() if s > 0]
        scored_tables.sort(key=lambda x: x[1], reverse=True)

        if not scored_tables:
            return allowed_tables

        # Pick top candidate tables (up to 3)
        selected: Set[str] = {scored_tables[0][0]}
        for t, s in scored_tables[1:4]:
            if s >= 4:
                selected.add(t)

        # Link directly connected foreign key dimensions/facts (up to max 4 tables)
        for t_sel in list(selected):
            sel_cols = {c for c in table_cols_map.get(t_sel, []) if c.startswith("id_") or c.endswith("_id") or c == "id" or "key" in c}
            for other_tbl in sorted(list(allowed_tables)):
                if other_tbl not in selected and len(selected) < 4:
                    other_cols = set(table_cols_map.get(other_tbl, []))
                    common_fks = sel_cols.intersection(other_cols)
                    if common_fks:
                        selected.add(other_tbl)

        return selected

    @classmethod
    def get_authorized_schema_prompt(
        cls,
        db: Session,
        role_id: Optional[int] = None,
        connection_id: Optional[int] = None,
        is_admin: bool = False,
        user_role: Optional[str] = None,
        query: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Returns compact prompt text containing schema definition for allowed tables/columns
        plus semantic descriptions, and sets of allowed_tables & blocked_columns for AST validation.
        Prunes tables that do not exist physically in the currently active database and prunes
        tables irrelevant to the query to maintain high-speed inference within 4k local context limits.
        """
        q_norm = query.strip().lower() if query else ""
        cache_key = f"{connection_id}:{role_id}:{user_role}:{is_admin}:{q_norm}"
        now = time.time()
        is_mock_db = hasattr(db, "_mock_return_value") or hasattr(db, "_mock_methods") or (db is not None and "mock" in type(db).__name__.lower())
        if not is_mock_db and cache_key in cls._schema_cache:
            ts, cached_result = cls._schema_cache[cache_key]
            if now - ts < cls._SCHEMA_CACHE_TTL:
                return cached_result

        conn_record = None
        if db is not None:
            try:
                if connection_id:
                    conn_record = db.query(CorporateConnection).filter(CorporateConnection.id == connection_id).first()
                    if not conn_record:
                        conn_record = db.query(CorporateConnection).filter(CorporateConnection.is_uploaded == False).first()
                if not conn_record:
                    conn_record = db.query(CorporateConnection).filter(CorporateConnection.is_active == True).order_by(CorporateConnection.id.desc()).first()
                if not conn_record:
                    conn_record = db.query(CorporateConnection).order_by(CorporateConnection.id.desc()).first()
            except Exception:
                # Sin esto la sesion queda abortada y los `db.query(...)` de mas
                # abajo de esta misma funcion mueren con `InFailedSqlTransaction`.
                discard_failed_transaction(db)

        effective_conn_id = conn_record.id if conn_record else (connection_id or 1)

        is_pg = conn_record is not None and (conn_record.db_type == DatabaseType.POSTGRESQL or str(conn_record.db_type).lower() == "postgresql")
        target_db_target = conn_record if is_pg else cls.resolve_db_path(db, effective_conn_id)
        physical_tables = cls.get_physical_db_tables(target_db_target)

        # Determine effective role_id and permissions
        effective_role_id = role_id
        if effective_role_id is None and user_role:
            role_obj = db.query(Role).filter(Role.name == user_role).first()
            if role_obj:
                effective_role_id = role_obj.id

        blocked_columns: Set[str] = set()
        masked_columns: Set[str] = set()
        column_perm_map: Dict[str, str] = {}

        if is_admin:
            catalog_entries = db.query(SemanticCatalog).filter(
                SemanticCatalog.connection_id == effective_conn_id
            ).all()

            raw_catalog_tables = {e.table_name.lower() for e in catalog_entries if e.table_name}
            if physical_tables:
                allowed_tables = set(physical_tables).union(raw_catalog_tables)
            elif raw_catalog_tables:
                allowed_tables = raw_catalog_tables
            else:
                table_perms = db.query(RoleTablePermission).filter(
                    RoleTablePermission.connection_id == effective_conn_id,
                    RoleTablePermission.is_allowed == True
                ).all()
                allowed_tables = {tp.table_name.lower() for tp in table_perms}
        else:
            table_perms = db.query(RoleTablePermission).filter(
                RoleTablePermission.role_id == effective_role_id,
                RoleTablePermission.connection_id == effective_conn_id,
                RoleTablePermission.is_allowed == True
            ).all() if effective_role_id is not None else []

            raw_allowed = {tp.table_name.lower() for tp in table_perms}
            if physical_tables:
                overlap = {t for t in raw_allowed if t in physical_tables}
                allowed_tables = overlap if overlap else raw_allowed
            else:
                allowed_tables = raw_allowed

            col_perms = db.query(RoleColumnPermission).filter(
                RoleColumnPermission.role_id == effective_role_id,
                RoleColumnPermission.connection_id == effective_conn_id
            ).all() if effective_role_id is not None else []

            for cp in col_perms:
                key = f"{cp.table_name.lower()}.{cp.column_name.lower()}"
                column_perm_map[key] = cp.permission_type.value
                if cp.permission_type == ColumnPermissionType.BLOCKED:
                    blocked_columns.add(cp.column_name.lower())
                elif cp.permission_type == ColumnPermissionType.MASKED:
                    # MASKED NO va a blocked_columns a proposito: la columna debe
                    # seguir consultable para que el LLM pueda usarla en joins y
                    # agregaciones. Lo que se tapa es el valor, no el acceso.
                    masked_columns.add(cp.column_name.lower())

            catalog_entries = db.query(SemanticCatalog).filter(
                SemanticCatalog.connection_id == effective_conn_id
            ).all()

        catalog_desc_map: Dict[str, str] = {}
        catalog_synonyms_map: Dict[str, str] = {}
        for entry in catalog_entries:
            key = f"{entry.table_name.lower()}.{entry.column_name.lower() if entry.column_name else '*'}"
            catalog_desc_map[key] = entry.description or ""
            if entry.synonyms and entry.synonyms.strip():
                catalog_synonyms_map[key] = entry.synonyms.strip()

        # Relevance pruning: determine active subset of tables for schema prompt rendering
        active_tables = cls.rank_relevant_tables(allowed_tables, query, catalog_entries, target_db_target)

        # Build schema definition lines from physical database inspection
        schema_text_lines = []
        table_columns_map: Dict[str, List[str]] = {}

        for tbl in sorted(list(active_tables)):
            phys_cols = cls.get_physical_table_columns(tbl, target_db_target)
            table_columns_map[tbl] = []

            col_lines = []
            if phys_cols:
                for pc in phys_cols:
                    c_name = pc["name"]
                    c_lower = c_name.lower()
                    if c_lower in blocked_columns or column_perm_map.get(f"{tbl}.{c_lower}") == "BLOCKED":
                        continue

                    table_columns_map[tbl].append(c_name)
                    desc = catalog_desc_map.get(f"{tbl}.{c_lower}", "").strip()
                    syns = catalog_synonyms_map.get(f"{tbl}.{c_lower}", "")
                    is_masked = column_perm_map.get(f"{tbl}.{c_lower}") == "MASKED"

                    # Compact samples (max 2 items, max 25 chars each)
                    samples = pc.get("samples", [])[:2]
                    clean_samples = []
                    for s in samples:
                        s_str = str(s).strip()
                        if len(s_str) > 25:
                            s_str = s_str[:22] + "..."
                        if not s_str.replace('.', '', 1).isdigit():
                            clean_samples.append(repr(s_str))
                        else:
                            clean_samples.append(s_str)
                    sample_str = f", ej: {', '.join(clean_samples)}" if clean_samples else ""
                    
                    details = f"{c_name} ({pc['type']}{sample_str})"

                    # Clean redundant descriptions
                    if desc:
                        desc_lower = desc.lower()
                        if not (desc_lower.startswith("registro de datos tipo") or desc_lower in cls.NON_FORMULAS):
                            if len(desc) > 60:
                                desc = desc[:57] + "..."
                            details += f" - {desc}"

                    if syns:
                        details += f" (Sinónimos: {syns})"
                    if is_masked:
                        details += " [ENMASCARADO]"
                    col_lines.append(details)
            else:
                for entry in catalog_entries:
                    if entry.table_name.lower() == tbl and entry.column_name:
                        c_name = entry.column_name
                        c_lower = c_name.lower()
                        if c_lower not in blocked_columns and column_perm_map.get(f"{tbl}.{c_lower}") != "BLOCKED":
                            desc = (entry.description or "").strip()
                            if desc.lower().startswith("registro de datos tipo") or desc.lower() in cls.NON_FORMULAS:
                                desc = ""
                            line = f"{c_name}" + (f" - {desc[:57]}..." if len(desc) > 60 else (f" - {desc}" if desc else ""))
                            if entry.synonyms:
                                line += f" (Sinónimos: {entry.synonyms})"
                            col_lines.append(line)
                            table_columns_map[tbl].append(c_name)

            tbl_syns = catalog_synonyms_map.get(f"{tbl}.*", "")
            tbl_header = f"Tabla `{tbl}`" + (f" (Sinónimos: {tbl_syns})" if tbl_syns else "")
            if col_lines:
                schema_text_lines.append(cls._render_table_as_ddl(tbl, tbl_syns, col_lines))
            else:
                schema_text_lines.append(f"{tbl_header} (Columnas de solo lectura)")

        # Auto-detect foreign key / join relationships between active tables
        relationships = []
        tables_list = list(table_columns_map.keys())
        for i in range(len(tables_list)):
            for j in range(i + 1, len(tables_list)):
                t1, t2 = tables_list[i], tables_list[j]
                cols1 = {c.lower(): c for c in table_columns_map[t1]}
                cols2 = {c.lower(): c for c in table_columns_map[t2]}
                common = set(cols1.keys()).intersection(set(cols2.keys()))
                for c in common:
                    if c.startswith("id_") or c.endswith("_id") or c == "id" or "key" in c or c in {"belnr", "vbeln", "ebeln", "matnr", "kunnr", "lifnr", "bukrs", "posnr"}:
                        relationships.append(f"{t1}.{cols1[c]} = {t2}.{cols2[c]}")

        if relationships:
            schema_text_lines.append("Relaciones (JOIN) detectadas:\n  - " + "\n  - ".join(relationships))

        # Collect explicit business formulas (genuine mathematical/SQL calculation formulas only)
        formula_lines = []
        seen_formulas = set()
        for entry in catalog_entries:
            if not entry.business_formula:
                continue
            form_clean = entry.business_formula.strip()
            form_lower = form_clean.lower()
            if form_lower in cls.NON_FORMULAS:
                continue
            if entry.column_name and form_lower == entry.column_name.strip().lower():
                continue
            # Must contain mathematical operators or SQL functions
            has_calc_char = any(c in form_clean for c in ["(", "+", "-", "*", "/", ">", "<", "="])
            has_calc_word = any(w in form_lower for w in ["sum", "avg", "count", "min", "max", "round", "date", "coalesce", "case", "when"])
            if not (has_calc_char or has_calc_word):
                continue

            # Only include formula if its table is in active_tables
            if entry.table_name and entry.table_name.lower() not in active_tables:
                continue

            lbl = entry.friendly_name or entry.column_name or entry.table_name
            f_key = f"{lbl.lower()}:{form_clean.lower()}"
            if f_key in seen_formulas:
                continue
            seen_formulas.add(f_key)
            formula_lines.append(f"Métrica '{lbl}': {form_clean}")

        if formula_lines:
            schema_text_lines.append("Fórmulas de Negocio Oficiales:\n  - " + "\n  - ".join(formula_lines))

        result = {
            "schema_prompt": "\n\n".join(schema_text_lines) if schema_text_lines else "Esquema de la base de datos activa.",
            "allowed_tables": allowed_tables,
            "blocked_columns": blocked_columns,
            "masked_columns": masked_columns,
        }
        if not is_mock_db:
            # La key lleva `q_norm` (el texto de la pregunta), o sea que hay una
            # entrada DISTINTA por cada pregunta que se ha hecho. Con solo TTL y
            # sin poda, el dict crecia para siempre guardando el `schema_prompt`
            # completo de cada una. Se purga lo vencido antes de insertar y, si
            # aun asi se pasa, se cae el cache entero: reconstruuirlo es una
            # introspeccion, no una perdida de datos.
            if len(cls._schema_cache) >= cls._PHYSICAL_CACHE_MAX:
                cls._schema_cache = {
                    k: v for k, v in cls._schema_cache.items() if now - v[0] < cls._SCHEMA_CACHE_TTL
                }
                if len(cls._schema_cache) >= cls._PHYSICAL_CACHE_MAX:
                    cls._schema_cache.clear()
            cls._schema_cache[cache_key] = (now, result)
        return result


