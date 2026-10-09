"""`/chat/predict` bajo los MISMOS gates de RBAC que el chat.

Que se verifica aca
-------------------
1. Separacion de dominios: un perfil TI que tiene `fact_ventas` en su matriz de
   permisos NO se lleva agregados de ingresos por `/predict`. Esa pregunta
   escrita en el chat ya salia denegada por `governance_guard.py:193`; por el
   endpoint de prediccion no. `/predict` no es un camino privilegiado alrededor
   de la gobernanza.
2. El perfil inicial "Usuario" sin rol asignado no entra, igual que en el chat.
3. Con los gates puestos, un rol de SU dominio sigue funcionando: el fix no
   rompe el caso normal.

La traduccion del guard de dominio
----------------------------------
`GovernanceGuard.check_domain_governance` decide sobre keywords del TEXTO de la
consulta, y `/predict` no recibe una pregunta en lenguaje natural. Lo que si se
puede observar desde el endpoint es el conjunto de tablas autorizadas del rol, y
ese es el sujeto real que el SQL va a leer. Por eso el gate le pasa las tablas y
no una frase inventada.
"""

import asyncio
import unittest
from unittest.mock import MagicMock, patch

from app.core.constants import ROLE_USUARIO
from app.modules.chat_engine import forecast_service
from app.modules.chat_engine.router import run_prediction
from app.modules.chat_engine.schemas import PredictionRequest


def _usuario(role_name=None, role_id=1, is_admin=False):
    user = MagicMock()
    user.id = 7
    user.username = "tester"
    user.is_admin = is_admin
    user.role_id = role_id
    user.role = MagicMock() if role_name is not None else None
    if role_name is not None:
        user.role.name = role_name
    return user


def _payload(**kwargs):
    base = dict(connection_id=1, include_forecast=True, include_retention=True)
    base.update(kwargs)
    return PredictionRequest(**base)


class _FiltroFalso:
    def filter(self, *a, **k):
        return self

    def first(self):
        return None  # sin CorporateConnection: el audit log usa el nombre por defecto

    def all(self):
        return []


class _SesionFalsa:
    """Sesion vacia: los tres servicios van patcheados, asi que el unico uso real
    de `db` es `_resolve_target_database` y `_persist_audit_log`, y ninguno debe
    tocar la metadata de verdad."""

    def query(self, *a, **k):
        return _FiltroFalso()

    def add(self, *a, **k):
        pass

    def commit(self):
        pass

    def refresh(self, *a, **k):
        pass

    def rollback(self):
        pass

    def close(self):
        pass


class TestPredictRbac(unittest.TestCase):
    """Los dos gates de `engine.py:155-167` tambien aplican a `/predict`."""

    def _correr(self, user, tablas, payload=None):
        """Corre `/predict` con las tablas autorizadas controladas.

        Los servicios de prediccion quedan patcheados para que este test mida
        SOLO el gate: si el gate deja pasar, el forecast responde y el test falla
        por el motivo correcto (datos publicados), no por una excepcion.
        """
        from app.modules.chat_engine.governance_guard import GovernanceGuard

        forecast = MagicMock(return_value={"available": False, "reason": "stub", "series": []})
        retention = MagicMock(return_value={"total_clients": 0, "tiers": {}, "top": []})
        quality = MagicMock(return_value=[])
        with patch.object(GovernanceGuard, "get_allowed_tables_for_role", return_value=set(tablas)), \
             patch.object(forecast_service, "run_forecast", forecast), \
             patch.object(forecast_service, "run_retention", retention), \
             patch.object(forecast_service, "audit_data_quality", quality):
            return asyncio.run(run_prediction(payload or _payload(), user, _SesionFalsa()))

    # --- 1. Separacion de dominios (el bug de seguridad) -----------------------

    def test_ti_con_fact_ventas_no_saca_agregados_de_ingresos(self):
        """TI con `fact_ventas` en su matriz: el chat lo denies, `/predict` no."""
        user = _usuario("TI", role_id=11)
        with self.assertRaises(Exception) as ctx:
            self._correr(user, {"fact_ventas", "dim_servidores"})
        self.assertEqual(getattr(ctx.exception, "status_code", None), 403)
        self.assertIn("Gobernanza RBAC: Acceso denegado", str(ctx.exception.detail))

    def test_rol_financiero_no_saca_datos_de_ti(self):
        """El otro lado del mismo muro: Economista no entra a `fact_incidentes_ti`."""
        user = _usuario("Analista Financiero & Comercial", role_id=10)
        with self.assertRaises(Exception) as ctx:
            self._correr(user, {"fact_ventas", "fact_incidentes_ti"})
        self.assertEqual(getattr(ctx.exception, "status_code", None), 403)
        self.assertIn("infraestructura TI", str(ctx.exception.detail))

    # --- 2. Cuenta sin rol asignado --------------------------------------------

    def test_cuenta_sin_rol_denegado(self):
        """El corte real: `user.role is None`, sin importar el nombre.

        Antes disparaba con `role == ROLE_USUARIO`, o sea que un Usuario Consultor
        con su rol asignado era rechazado igual. Con la matriz de 8 roles el
        Consultor tiene lectura minima declarada y pasar por este gate lo dejaba
        como un perfil que no puede hacer nada.
        """
        user = _usuario(None, role_id=None)
        with self.assertRaises(Exception) as ctx:
            self._correr(user, {"fact_ventas"})
        self.assertEqual(getattr(ctx.exception, "status_code", None), 403)
        self.assertIn("rol asignado", str(ctx.exception.detail).lower())

    def test_consultor_con_rol_no_es_bloqueado_por_el_gate(self):
        """Contrapunto: tener rol es lo que abre la puerta, y el Usuario Consultor
        tiene uno. Si este test falla, el gate volvio a bloquear por nombre y el
        Consultor quedo muerto otra vez."""
        user = _usuario(ROLE_USUARIO, role_id=12)
        resp = self._correr(user, {"dim_categorias"})
        self.assertEqual(resp.errors, [])

    # --- 3. El caso normal sigue funcionando ---------------------------------

    def test_rol_de_su_dominio_sigue_funcionando(self):
        """El gate no puede cerrar la puerta a un Economista legimo."""
        resp = self._correr(_usuario("Analista Financiero & Comercial", role_id=10),
                            {"fact_ventas", "dim_clientes"})
        self.assertEqual(resp.errors, [])
        self.assertIsNotNone(resp.forecast)

    def test_ti_con_sus_propias_tablas_sigue_funcionando(self):
        """TI leyendo `dim_servidores` no matchea ninguna keyword financiera."""
        resp = self._correr(_usuario("TI", role_id=11), {"dim_servidores", "fact_incidentes_ti"})
        self.assertEqual(resp.errors, [])
        self.assertIsNotNone(resp.forecast)

    def test_admin_no_pasa_por_el_gate_de_dominio(self):
        """Admin tiene vision cross-dominio: el gate es fail-open por diseño."""
        resp = self._correr(_usuario("Administrador de Plataforma", role_id=1, is_admin=True),
                            {"fact_ventas", "dim_servidores"})
        self.assertEqual(resp.errors, [])
        self.assertIsNotNone(resp.forecast)

    # --- Budget: la tabla de hechos se resuelve UNA vez por request ------------

    def test_un_solo_budget_compartido_entre_los_tres_bloques(self):
        """Los tres bloques reciben el MISMO dict: sin eso cada uno vuelve a
        pagar los N COUNT(*) y la memoizacion no arregla nada."""
        with patch("app.modules.chat_engine.router.SessionLocal", return_value=_SesionFalsa()):
            with patch("app.modules.chat_engine.governance_guard.GovernanceGuard."
                       "get_allowed_tables_for_role", return_value={"fact_ventas"}):
                vistos = []

                def _spy(service_name):
                    def _f(db, conn_id, role, is_admin, role_id, *rest):
                        budget = rest[-1]
                        vistos.append((service_name, id(budget)))
                        return {"available": False, "reason": "stub", "series": []} \
                            if service_name == "run_forecast" else \
                            ({"total_clients": 0, "tiers": {}, "top": []}
                             if service_name == "run_retention" else [])
                    return _f

                with patch.object(forecast_service, "run_forecast", _spy("run_forecast")), \
                     patch.object(forecast_service, "run_retention", _spy("run_retention")), \
                     patch.object(forecast_service, "audit_data_quality", _spy("audit_data_quality")):
                    asyncio.run(run_prediction(
                        _payload(include_data_quality=True),
                        _usuario("Analista Financiero & Comercial", role_id=10),
                        _SesionFalsa(),
                    ))

        self.assertEqual(len(vistos), 3, "los tres bloques deben correr")
        self.assertEqual(len({b for _, b in vistos}), 1, "los tres deben compartir el budget")


class TestTablaDeHechosSeResuelveUnaVez(unittest.TestCase):
    """`_load_fact_table` no puede re-escanear la fact table por bloque."""

    def test_segunda_llamada_al_cache_no_toca_la_base(self):
        budget = {"allowed_tables": {"fact_ventas"}, "fact_table": ("fact_ventas", [{"name": "monto"}])}
        conn = MagicMock()
        # Ni `db` ni `connection` se usan: si se tocaran, el MagicMock no
        # fallaria solo, asi que se pasa `None` para que un acceso reviente.
        with patch.object(forecast_service, "SQLExecutor") as executor:
            table, cols = forecast_service._load_fact_table(
                None, None, False, "Economista", 1, 1, "sqlite", budget
            )
        self.assertEqual(table, "fact_ventas")
        self.assertEqual(cols, [{"name": "monto"}])
        executor.execute_raw_sql.assert_not_called()

    def test_sin_budget_sigue_resolviendo(self):
        """Los llamadores sin cache (o un test viejo) no se rompen: se crea uno local."""
        allowed = {"fact_ventas"}
        cols = [{"name": "monto", "type": "bigint", "is_pk": False}]
        conn = MagicMock()
        db = MagicMock()
        with patch.object(forecast_service.GovernanceGuard, "get_allowed_tables_for_role",
                          return_value=allowed), \
             patch.object(forecast_service.ASTValidator, "validate_and_secure_sql",
                          side_effect=lambda sql, **k: (True, sql, None)), \
             patch.object(forecast_service.SQLExecutor, "execute_raw_sql",
                          return_value=[{"n": 10}]), \
             patch.object(forecast_service.DynamicSchemaPruningService,
                          "get_physical_table_columns", return_value=cols):
            self.assertEqual(
                forecast_service._load_fact_table(db, conn, False, "Economista", 1, 1, "sqlite"),
                ("fact_ventas", cols),
            )


if __name__ == "__main__":
    unittest.main()
