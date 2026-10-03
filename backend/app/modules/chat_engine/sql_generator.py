import re
from typing import Set, Dict, Any, Optional, Tuple, List
from sqlalchemy.orm import Session

from app.core.constants import ADMIN_ROLES, ROLE_ADMINISTRADOR
from app.core.prompts import PromptManager
from app.modules.chat_engine.dynamic_schema import DynamicSchemaPruningService
from app.modules.chat_engine.llm_service import LLMService
from app.modules.chat_engine.sql_executor import SQLExecutor

class SQLGenerator:
    """
    Translates citizen natural language into secure, optimized SELECT queries
    using Local LLMs with Chain-of-Thought reasoning, few-shot grounding memories,
    and RBAC boundary checks.
    """

    @classmethod
    async def generate_candidate_sql(
        cls,
        question: str,
        user_role: str,
        allowed_tables: Set[str],
        db: Optional[Session] = None,
        role_id: Optional[int] = None,
        connection_id: int = 1,
        is_admin: bool = False,
        conversation_history: Optional[List[Dict[str, Any]]] = None,
        dialect: str = "sqlite",
    ) -> Tuple[Optional[str], Optional[str], Optional[str], str, bool]:
        """
        Generates candidate SQL from natural language query.
        Returns: (candidate_sql, thinking_process, rbac_denial_reason, schema_context, is_llm_active)
        """
        schema_context = ""
        try:
            s_info = DynamicSchemaPruningService.get_authorized_schema_prompt(
                db=db,
                role_id=role_id,
                user_role=user_role,
                connection_id=connection_id,
                is_admin=is_admin,
                query=question
            )
            schema_context = s_info.get("schema_prompt", "")
        except Exception:
            pass

        few_shots = SQLExecutor.retrieve_few_shot_memories(
            db, question, connection_id, user_role=user_role
        )
        conv_context = PromptManager.format_conversation_context(conversation_history) if conversation_history else ""

        candidate_sql = None
        thinking_process = None
        rbac_denial = None
        is_llm_active = False

        try:
            system_prompt = PromptManager.get_text_to_sql_system_prompt(user_role, allowed_tables, dialect=dialect)
            prompt_llm = PromptManager.get_text_to_sql_user_prompt(
                question, user_role, schema_context, allowed_tables, few_shots,
                conversation_context=conv_context, dialect=dialect,
            )

            llm_response_text = await LLMService.generate_completion(
                prompt_llm,
                system_prompt=system_prompt,
                temperature=0.05,
                max_tokens=350
            )

            if llm_response_text:
                is_llm_active = True

                # Check explicit access denied XML tag (only for non-admin roles)
                is_admin_user = is_admin or user_role in ADMIN_ROLES or user_role in ("Administrador", ROLE_ADMINISTRADOR)
                denied_match = re.search(r'<acceso_denegado>\s*(.*?)\s*</acceso_denegado>', llm_response_text, re.DOTALL | re.IGNORECASE)
                if denied_match and not is_admin_user:
                    rbac_denial = denied_match.group(1).strip()
                    return None, None, rbac_denial, schema_context, is_llm_active

                # Check textual RBAC denial without SQL (only for non-admin roles)
                lower_llm = llm_response_text.lower()
                if not is_admin_user and any(phrase in lower_llm for phrase in [
                    "acceso denegado", "no tiene autorización", "no está autorizado",
                    "no tiene permisos", "fuera de sus tablas permitidas",
                    "no tiene autorizacion", "no esta autorizado"
                ]) and "```sql" not in llm_response_text:
                    rbac_denial = f"Gobernanza RBAC: Acceso denegado. El perfil '{user_role}' no tiene autorización para acceder a estos datos."
                    return None, None, rbac_denial, schema_context, is_llm_active

                thinking_process = None

                # Extract SQL block
                sql_match = re.search(r'```sql\s*(.*?)\s*```', llm_response_text, re.DOTALL | re.IGNORECASE)
                if sql_match:
                    extracted = sql_match.group(1).strip()
                    if "SELECT" in extracted.upper():
                        candidate_sql = extracted
                elif "SELECT" in llm_response_text.upper():
                    select_match = re.search(r'(SELECT\s+.*?(?:;|$))', llm_response_text, re.DOTALL | re.IGNORECASE)
                    if select_match:
                        candidate_sql = select_match.group(1).strip().rstrip(';')

        except Exception:
            is_llm_active = False

        return candidate_sql, thinking_process, rbac_denial, schema_context, is_llm_active
