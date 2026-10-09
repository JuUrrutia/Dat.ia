"""Por que el chat esta vacio: tres diagnosticos que hoy son el mismo texto.

El defecto: `allowed_tables` vacio caia siempre en el mismo "el rol no tiene
tablas asignadas", y en el despliegue de desarrollo las 11 conexiones estan
con `is_active=False`. El usuario veia un RBAC que no era el problema y no
tenia forma de saber que faltaba encender una base.

Lo que se verifica aca:
  - sin conexion activa el mensaje dice ESO, y no el del rol (confundir los dos
    diagnosticos es el bug)
  - con conexion activa y rol sin tablas el mensaje sigue siendo el del rol
  - la accion de activar solo se ofrece al admin
  - con tablas visibles el camino normal no cambia
"""
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from app.modules.chat_engine.engine import QueryEngine
from app.modules.chat_engine.intent_classifier import IntentClassifier


def _conn(conn_id: int, name: str, is_active: bool) -> MagicMock:
    c = MagicMock()
    c.id = conn_id
    c.name = name
    c.is_active = is_active
    return c


def _db(connections):
    """Sesion que responde solo lo que el diagnostico consulta."""
    db = MagicMock()
    db.query.return_value.all.return_value = connections
    return db


class TestNoActiveConnection(unittest.TestCase):
    """El caso 1 es el que importa: los dos diagnosticos jamas se mezclan."""

    def _ask(self, connections, *, is_admin=False, role="Economista", connection_id=1, allowed=set()):
        with patch.object(QueryEngine, "get_allowed_tables_for_role", return_value=allowed):
            import asyncio
            return asyncio.run(QueryEngine.execute_query(
                question="¿Cuántos registros hay?",
                user_role=role,
                is_admin=is_admin,
                db=_db(connections),
                role_id=2,
                connection_id=connection_id,
            ))

    def test_sin_conexion_activa_el_mensaje_no_es_el_del_rol(self):
        """1. Nadie encendio una base: eso es lo que dice, no 'sin tablas'."""
        resp = self._ask([_conn(1, "Plataforma", False)], is_admin=False)

        self.assertTrue(resp.no_active_connection)
        self.assertEqual(resp.traceability.validation_status, "SIN_CONEXION_ACTIVA")
        self.assertIn("No hay ninguna conexión de datos activa", resp.summary_text)
        self.assertIn(
            "ningún administrador ha activado una base",
            resp.summary_text,
            "el mensaje tiene que nombrar la causa, no el sintoma",
        )
        # El bug: decir que el rol no tiene tablas cuando el problema es otro.
        self.assertNotIn("no tiene tablas asignadas", resp.summary_text)
        self.assertNotIn("matriz RBAC", resp.summary_text)
        # Sin tablas no se ejecuta SQL ni se devuelven filas que se lean como
        # "esta tabla no tiene datos".
        self.assertEqual(resp.data_rows, [])
        self.assertIn("NO HAY NINGUNA CONEXIÓN ACTIVA", resp.traceability.sql_executed)

    def test_cero_conexiones_no_es_lo_mismo_que_ninguna_activa(self):
        """Sin ninguna base dada de alta la accion que falta es CREAR, no activar.

        Sin este caso, una instalacion nueva caia en el mensaje de
        `no_active_connection` y mandaba al admin a buscar un interruptor que no
        existe: ninguna conexion esta apagada porque no hay ninguna.
        """
        resp = self._ask([], is_admin=True)

        self.assertIsNone(resp.no_active_connection, "no es el caso de conexion inactiva")
        self.assertEqual(
            resp.traceability.validation_status, "SIN_CONEXION_REGISTRADA"
        )
        self.assertIn("No hay ninguna conexión de datos registrada", resp.summary_text)
        self.assertNotIn(
            "ningún administrador ha activado una base",
            resp.summary_text,
            "con cero conectores no hay nadie que haya podido activar uno",
        )
        # Y el KPI tampoco: si dice 'DESCONOCIDO' el admin no sabe si fallo el
        # chequeo o realmente no hay nada.
        self.assertEqual(resp.kpis[0].value, "SIN CONEXIÓN REGISTRADA")
        self.assertEqual(resp.data_rows, [])
        # Sin base no hay nada que encender, y sin ser admin tampoco habria accion.
        self.assertIsNone(resp.activate_connection_action)

    def test_conexion_activa_pero_rol_sin_tablas_es_el_mensaje_del_rol(self):
        """2. Con una base encendida el diagnostico vuelve a ser el de siempre."""
        resp = self._ask(
            [_conn(1, "Plataforma", True), _conn(2, "Bodega", False)],
            is_admin=False,
            role="Oficial de Cumplimiento",
        )

        self.assertIsNone(resp.no_active_connection)
        self.assertEqual(resp.traceability.validation_status, "RECHAZADO_RBAC")
        self.assertIn("no tiene tablas asignadas", resp.summary_text)
        self.assertIn("matriz RBAC", resp.summary_text)
        self.assertNotIn("No hay ninguna conexión de datos activa", resp.summary_text)

    def test_la_accion_de_activar_solo_es_del_admin(self):
        """3. Un no-admin no recibe ninguna accion; el admin si."""
        conexiones = [_conn(7, "ERP Bodega", False)]

        usuario = self._ask(conexiones, is_admin=False)
        self.assertIsNone(usuario.activate_connection_action)
        self.assertIn(
            "tarea de administración",
            usuario.conversational_response,
            "al que no puede activarla se le dice a quien pedirlo",
        )

        admin = self._ask(conexiones, is_admin=True, role="Administrador de Plataforma")
        self.assertTrue(admin.no_active_connection)
        self.assertIsNotNone(admin.activate_connection_action)
        self.assertEqual(admin.activate_connection_action["connection_id"], 7)
        self.assertEqual(admin.activate_connection_action["connection_name"], "ERP Bodega")
        self.assertIn("Podés resolverlo vos mismo", admin.conversational_response)

    def test_si_no_se_puede_comprobar_se_declara_desconocido(self):
        """No afirmar 'no hay conexiones' sin haberlo comprobado."""
        with patch.object(QueryEngine, "get_allowed_tables_for_role", return_value=set()):
            import asyncio
            db = MagicMock()
            db.query.side_effect = Exception("la metadata no responde")
            resp = asyncio.run(QueryEngine.execute_query(
                question="¿Cuántos registros hay?",
                user_role="Economista",
                is_admin=False,
                db=db,
                role_id=2,
                connection_id=1,
            ))

        self.assertIsNone(resp.no_active_connection)
        self.assertEqual(resp.traceability.validation_status, "DIAGNOSTICO_DESCONOCIDO")
        self.assertIn("No se pudo verificar", resp.summary_text)
        self.assertNotIn("No hay ninguna conexión de datos activa", resp.summary_text)

    def test_caso_normal_no_cambia(self):
        """4. Con tablas visibles el motor sigue por su camino de siempre."""
        with patch.object(QueryEngine, "get_allowed_tables_for_role", return_value={"fact_ventas"}), \
             patch.object(IntentClassifier, "classify_intent", new=AsyncMock(return_value="greeting")), \
             patch.object(IntentClassifier, "generate_conversational_response", new=AsyncMock(return_value="Hola")):
            import asyncio
            resp = asyncio.run(QueryEngine.execute_query(
                question="Hola",
                user_role="Economista",
                is_admin=False,
                db=_db([_conn(1, "Plataforma", True)]),
                role_id=2,
                connection_id=1,
            ))

        self.assertEqual(resp.response_type, "greeting")
        self.assertIsNone(resp.no_active_connection)
        self.assertIsNone(resp.activate_connection_action)
        self.assertEqual(resp.data_rows, [])


if __name__ == "__main__":
    unittest.main()