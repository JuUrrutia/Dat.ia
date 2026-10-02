import re
from typing import Set, Optional
from sqlalchemy.orm import Session

from app.core.constants import ADMIN_ROLES
from app.modules.chat_engine.dynamic_schema import DynamicSchemaPruningService

class GovernanceGuard:
    """
    Enforces Fail-Closed RBAC table access, column masking, and cross-domain boundary isolation.
    """

    @classmethod
    def get_allowed_tables_for_role(
        cls,
        user_role: str,
        is_admin: bool,
        db: Optional[Session] = None,
        role_id: Optional[int] = None,
        connection_id: Optional[int] = None
    ) -> Set[str]:
        if is_admin or user_role in ADMIN_ROLES:
            is_admin = True

        local_db = None
        if db is None:
            try:
                from app.core.database import SessionLocal
                local_db = SessionLocal()
                active_db = local_db
            except Exception:
                active_db = None
        else:
            active_db = db

        if active_db is not None:
            try:
                schema_info = DynamicSchemaPruningService.get_authorized_schema_prompt(
                    db=active_db,
                    role_id=role_id,
                    user_role=user_role,
                    connection_id=connection_id,
                    is_admin=is_admin
                )
                return schema_info.get("allowed_tables", set())
            except Exception:
                return set()
            finally:
                if local_db is not None:
                    local_db.close()

        return set()

    @classmethod
    def get_blocked_columns_for_role(
        cls,
        user_role: str,
        is_admin: bool,
        db: Optional[Session] = None,
        role_id: Optional[int] = None,
        connection_id: int = 1
    ) -> Set[str]:
        if is_admin or user_role in ADMIN_ROLES:
            return set()

        local_db = None
        if db is None:
            try:
                from app.core.database import SessionLocal
                local_db = SessionLocal()
                active_db = local_db
            except Exception:
                active_db = None
        else:
            active_db = db

        if active_db is not None:
            try:
                schema_info = DynamicSchemaPruningService.get_authorized_schema_prompt(
                    db=active_db,
                    role_id=role_id,
                    user_role=user_role,
                    connection_id=connection_id,
                    is_admin=is_admin
                )
                return schema_info.get("blocked_columns", set())
            except Exception:
                return set()
            finally:
                if local_db is not None:
                    local_db.close()

        return set()

    @classmethod
    def check_domain_governance(cls, question: str, user_role: str, allowed_tables: Set[str]) -> Optional[str]:
        """
        Enforces cross-domain governance guardrails (Fail-Closed).
        Detects if a user role attempts to query topics strictly outside their business domain.
        Returns a denial reason string if violated, or None if permitted.
        """
        role_lower = (user_role or "").lower().strip()
        q_lower = (question or "").lower().strip()

        # 0. Global Admin and C-Level have cross-domain visibility
        if any(k in role_lower for k in ["admin", "director ejecutivo", "c-level", "super", "plataforma"]):
            return None

        # Domain 1: Tech / TI / Infrastructure roles attempting to access financial, commercial or sales data
        is_tech_role = any(k in role_lower for k in ["ti", "infraestructura", "tecnolog", "sistemas", "devops", "soporte"])
        if is_tech_role and not any(k in role_lower for k in ["financ", "comercial", "econom"]):
            financial_keywords = [
                r'\b(saldo|saldos|balance|balances)\b',
                r'\b(venta|ventas|preventa|postventa)\b',
                r'\b(ingreso|ingresos|recaudaci[oó]n|cobro|cobros)\b',
                r'\b(ganancia|ganancias|lucro|utilidad|utilidades)\b',
                r'\b(precio|precios|tarifa|tarifas|cotizaci[oó]n|cotizaciones)\b',
                r'\b(facturaci[oó]n|factura|facturas|facturado)\b',
                r'\b(margen|m[aá]rgenes|ebitda|rentabilidad)\b',
                r'\b(costo|costos|gasto|gastos|egreso|egresos|presupuesto|presupuestos)\b',
                r'\b(dinero|monto|montos|financier[oa]s?|finanzas)\b',
                r'\b(econ[oó]mic[oa]s?|econom[íi]a|comercial(es)?)\b',
                r'\b(cartera\s+de\s+clientes|comprador|compradores)\b',
                r'\b(m[oó]dulo|[aá]rea|departamento)\s+(de\s+)?(finanzas|financier[oa]|comercial|ventas|facturaci[oó]n|econom[íi]a)\b',
                r'\b(fact_ventas|fact_ingresos_costos|vbak_cabpedidoventa|vbap_pospedidoventa|kna1_clientes)\b'
            ]
            if re.search('|'.join(financial_keywords), q_lower):
                return (
                    f"Gobernanza RBAC: Acceso denegado. El perfil '{user_role}' no tiene autorización "
                    "para consultar información financiera, facturación, ventas, ingresos ni balances comerciales de la organización."
                )

        # Domain 2: Business / Financial / Commercial roles attempting to access technical IT infrastructure
        is_fin_role = any(k in role_lower for k in ["economista", "financiero", "finanzas", "comercial", "negocio", "contab"])
        if is_fin_role and not any(k in role_lower for k in ["ti", "infraestructura", "tecnolog"]):
            # Check if it is a legitimate product or catalog inquiry about technology goods
            commercial_context = r'\b(vendid[oa]s?|vendieron|vendimos|vender|venta|ventas|comprad[oa]s?|compraron|compramos|compras?|precio|precios|facturaci[oó]n|facturas?|cliente|clientes)\b'
            product_context = r'\b(producto|productos|categor[íi]a|categor[íi]as|art[íi]culo|art[íi]culos|cat[aá]logo)\b'
            is_product_query = bool(re.search(product_context, q_lower) and re.search(commercial_context, q_lower))

            if not is_product_query:
                tech_keywords = [
                    r'\b(tecnol[oó]gic[oa]s?|tecnolog[ií]a)\b',
                    r'\b(ti|it|t\.i\.)\b',
                    r'\b(inform[aá]tic[oa]s?|telecomunicaci[oó]n|telecomunicaciones)\b',
                    r'\b(servidor|servidores|server|servers|host|hosts|cluster|clusters|nodo|nodos)\b',
                    r'\b(cpu|memoria\s+ram|\bram\b|disco|discos|almacenamiento)\b',
                    r'\b(incidente|incidentes|incidentes\s+ti|incidentes_ti)\b',
                    r'\b(ticket|tickets|soporte\s+t[ée]cnico|helpdesk|mesa\s+de\s+ayuda)\b',
                    r'\b(uptime|downtime|ca[íi]da|ca[íi]das|disponibilidad\s+del?\s+sistema)\b',
                    r'\b(consumo\s+de\s+recursos|latencia|ancho\s+de\s+banda|ping|router|switch|firewall)\b',
                    r'\b(infraestructura(\s+de\s+ti|\s+tecnol[oó]gica|\s+t[ée]cnica)?)\b',
                    r'\b(m[oó]dulo|[aá]rea|departamento)\s+(de\s+)?(ti|it|tecnolog[íi]a|infraestructura|sistemas)\b',
                    r'\b(m[oó]dulo\s+(ti|it|tecnol[oó]gic[oa]))\b',
                    r'\b(sistemas\s+inform[aá]ticos|telemetr[íi]a)\b',
                    r'\b(parche|parches|vulnerabilidad|vulnerabilidades|ciberseguridad|seguridad\s+ti)\b',
                    r'\b(backup|backups|respaldo|respaldos)\b',
                    r'\b(dim_servidores|fact_incidentes_ti|fact_consumo_recursos)\b'
                ]
                if re.search('|'.join(tech_keywords), q_lower):
                    return (
                        f"Gobernanza RBAC: Acceso denegado. El perfil '{user_role}' no tiene autorización "
                        "para consultar servidores, incidentes técnicos ni métricas de infraestructura TI."
                    )

        # Domain 3: HR / Payroll Isolation (only HR / Gerente de Talento, C-Level, Admin can access salaries/payroll)
        is_hr_role = any(k in role_lower for k in ["talento", "rrhh", "recursos humanos", "personas"])
        if not is_hr_role:
            hr_keywords = [
                r'\b(sueldo|sueldos|salario|salarios|remuneraci[oó]n|remuneraciones)\b',
                r'\b(n[oó]mina|n[oó]minas|honorario|honorarios)\b',
                r'\b(cu[aá]nto\s+gana[n]?|compensaci[oó]n|compensaciones)\b',
                r'\b(m[oó]dulo|[aá]rea|departamento)\s+(de\s+)?(rrhh|recursos humanos|talento|personal)\b',
            ]
            if re.search('|'.join(hr_keywords), q_lower):
                return (
                    f"Gobernanza RBAC: Acceso denegado. El perfil '{user_role}' no tiene autorización "
                    "para consultar salarios, remuneraciones, nóminas ni información confidencial de Recursos Humanos."
                )

        return None
