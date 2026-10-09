"""Aislamiento de la suite y estado conocido: las cuentas demo no dependen del orden.

Aislamiento: una base propia
----------------------------
La suite no debe escribir en la metadata de DESARROLLO. Lo hacia, y se notaba:
una corrida deja usuarios `test_*`, conexiones subidas y sesiones; si la corrida
se interrumpe (Ctrl+C, timeout), su `tearDown` no corre y la segunda pasada
choca contra lo que dejo la primera -- no con un bug del codigo, sino con su
propio rastro. Medido: 18 tests de `test_user_role_update.py` caian por
`UniqueViolation` de `ix_users_username` sobre un `test_roleupd_admin` que ya
existia.

El aislamiento es por NOMBRE DE BASE, no por motor: `POSTGRES_DB` ya es un
setting de entorno (`app/core/config.py:41`), asi que apuntar la suite a
`democratizacion_metadatos_test` conserva la semantica de PostgreSQL -- los tests
de tipo Postgres siguen siendo tests de Postgres, y el conector de la demo sigue
leyendo `democratizacion_empresa` de verdad. Forzar SQLite seria mas barato de
escribir y probaria otra cosa: `test_postgres_compatibility.py` y la migracion de
esquema de `database.py` existen justamente para el motor que produccion usa.

El override vive SOLO en este archivo. `.env` y `config.py` no se tocan, asi que
arrancar la app como siempre no cambia de base.

Por que este archivo existe
---------------------------
Una suite cuyo resultado depende de que test corrio antes no es una suite: es
ruido con formato de numero. Y el caso de este proyecto es concreto, no teorico:
varios tests mutan cuentas demo compartidas (`economista`, `ti`, `admin`) para
poder verificar el lockout o el cambio de contrasena, y antes no devolvian nada
a su estado original. Con `init_db` ya NO reescribiendo cuentas existentes (que
fue un bug arreglado justamente para que un cambio del admin no se perdiera al
reiniciar), esa pollution dejo de autocurarse sola.

El sintoma era que la suite recien desbloqueada daba verde y la segunda corrida
en el mismo arbol ya no: `unlock_users.py` existe como red de seguridad manual,
y depender de acordarse de correrlo no es un estado conocido, es un rito.

Que garantiza este fixture
--------------------------
Antes y despues de CADA test, las cuentas demo quedan en un estado conocido y
reproducible: activas, sin lockout, sin `must_change_password`, y con la
contrasena del README. Un test que bloquea `ti` puede seguir verificando el
lockout porque su `tearDown` restaura el estado: el fixture actua en los
extremos, no durante. Lo que este fixture NO hace es falsificar las aserciones
de nadie -- solo fija el punto de partida, que es lo que hace determinista el
orden.

Que NO hace, a proposito
------------------------
- No borra filas de `audit_logs` ni de `user_sessions`. Los tests que dependen
  de "la ultima fila" ya filtran por su propio marcador, y borrar filas ajenas
  seria capaz de tapar un bug real de aislamiento.
- No toca `is_active` mas alla del reset. Desactivar cuentas es un caso de
  negocio legitimo (`test_init_db_does_not_mutate_existing_users` lo verifica).
"""

import os
import re
import warnings

import pytest

# --- Aislamiento: la suite usa una base propia --------------------------------
#
# Tiene que fijarse ANTES de que se importe `app.core.database`: ese modulo arma
# el engine en tiempo de import (lineas 22-38) y, si despues se repunta con
# `update_database_engine`, cada modulo que hizo `from app.core.database import
# SessionLocal` queda con el enlace viejo. Un `os.environ` en el tope de conftest
# alcanza: pytest importa conftest antes de cualquier test, y no hace falta un
# hook ni un plugin.
#
# `DATIA_TEST_DB` existe por si alguien necesita otro nombre; el default es el
# de la metadata de desarrollo con el sufijo `_test`.
TEST_DB = os.environ.get("DATIA_TEST_DB") or "democratizacion_metadatos_test"
os.environ["POSTGRES_DB"] = TEST_DB

# Nombre de base interpolado en DDL (`CREATE DATABASE` no admite bind parameters),
# asi que se valida en vez de confiar: sale del entorno.
assert re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", TEST_DB), f"nombre de base invalido: {TEST_DB}"


def _ensure_test_database() -> None:
    """Crea la base de pruebas si no existe. Corre ANTES de importar el engine.

    No se reusa `scripts/setup_postgres_full.create_database_if_not_exists`: importar
    ese modulo importa `app.core.database` (su linea 19), que es justo el modulo
    que hay que aislar. Con la base todavia inexistente, `database.py` cae al
    fallback SQLite y cachea ese engine para toda la corrida. Son las mismas seis
    lineas, en el unico orden que funciona.

    Si PostgreSQL no esta disponible no se corta la suite: se avisa y deja que
    `database.py` decida, que para una demo sin Postgres es el fallback que ya
    soporta.
    """
    from sqlalchemy import create_engine, text

    from app.core.config import settings

    maintenance_url = (
        f"postgresql+psycopg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}/postgres"
    )
    eng = create_engine(maintenance_url, isolation_level="AUTOCOMMIT", pool_pre_ping=True)
    try:
        with eng.connect() as conn:
            exists = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": TEST_DB}
            ).scalar()
            if not exists:
                conn.execute(text(f'CREATE DATABASE "{TEST_DB}"'))
                print(f"[conftest] base de pruebas creada: {TEST_DB}")
    finally:
        eng.dispose()


try:
    _ensure_test_database()
except Exception as exc:  # pragma: no cover - depende del entorno
    warnings.warn(
        f"No se pudo preparar la base de pruebas {TEST_DB!r} ({exc}). "
        "La suite va a correr contra el fallback que elija app.core.database."
    )


@pytest.fixture(scope="session", autouse=True)
def test_database_bootstrapped():
    """La base de pruebas arranca sembrada, aunque nadie haya corrido la app.

    `init_db` crea el esquema y siembra domains, roles, cuentas demo, la conexion
    de plataforma y la matriz de permisos. Sin esto, un test que solo lee y no
    llama a `init_db` encontraria una base vacia en vez del estado sembrado.
    """
    from app.core.database import SessionLocal
    from app.db.init_db import init_db

    db = SessionLocal()
    try:
        init_db(db)
    finally:
        db.close()

# Las mismas del README, y las mismas que restaura `scripts/unlock_users.py`.
# Viven en los dos lados a proposito: el script es la herramienta manual de
# rescate y el fixture es la garantia automatica. Que coincidan es lo que hace
# que correr el script a mano y correr la suite den el mismo estado.
DEMO_ACCOUNTS = {
    "admin": "admin123",
    "economista": "economista123",
    "felipe_economista": "economista123",
    "ti": "ti123",
    "juan_ti": "ti123",
}

# bcrypt cuesta ~0.35s por hash y lo mismo por verify. Verificar las 5 cuentas en
# los dos extremos de 408 tests serian ~24 minutos de suite: medido, no supuesto.
#
# En vez de verificar siempre se memoriza el hash que YA se comprobo bueno (o que
# escribio este mismo fixture). Si el hash guardado esta en ese conjunto, la
# contrasena es la demo por construccion y no hay nada que probar. Solo se paga
# el bcrypt cuando el hash es desconocido, o sea cuando alguien cambio la
# contrasena de verdad. El primer test de la corrida paga las 5 verificaciones y
# el resto paga cero.
_known_good_hashes: set[str] = set()


def _reset_demo_accounts():
    """Deja las cuentas demo en el estado del README. Barato si no hay nada que hacer."""
    from app.core.database import SessionLocal
    from app.core.security import get_password_hash, verify_password
    from app.modules.auth.models import User

    db = SessionLocal()
    try:
        dirty = False
        for username, password in DEMO_ACCOUNTS.items():
            user = db.query(User).filter(User.username == username).first()
            if user is None:
                # Una cuenta demo ausente la crea `init_db`, no este fixture:
                # este archivo no debe saber como se siembran las cuentas.
                continue

            if (
                not user.is_active
                or user.failed_login_attempts
                or user.locked_until is not None
                or user.must_change_password
            ):
                user.is_active = True
                user.failed_login_attempts = 0
                user.locked_until = None
                user.must_change_password = False
                dirty = True

            stored = user.hashed_password or ""
            if stored not in _known_good_hashes:
                # Hash desconocido para este proceso: hay que probar de verdad.
                if verify_password(password, stored):
                    # Era la demo, pero este proceso recien lo confirma. Se
                    # recuerda para no volver a pagar bcrypt en cada test.
                    _known_good_hashes.add(stored)
                else:
                    # Alguien la cambio de verdad: se restaura la del README.
                    stored = get_password_hash(password)
                    user.hashed_password = stored
                    _known_good_hashes.add(stored)
                    dirty = True

        if dirty:
            db.commit()
    finally:
        db.close()


@pytest.fixture(autouse=True)
def demo_accounts_in_known_state():
    """Las cuentas demo entran y salen de cada test en estado conocido.

    Autouse y por test (no por sesion) a proposito: el orden de pytest no esta
    garantizado, asi que un cleanup de sesion solo alcanzaria si todo el arbol
    fallara de forma uniforme. Resetear en los dos extremos hace que cada test
    sea independiente de sus vecinos, que es la propiedad que se pide.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        _reset_demo_accounts()
        try:
            yield
        finally:
            _reset_demo_accounts()