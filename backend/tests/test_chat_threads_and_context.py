import pytest
from fastapi.testclient import TestClient
from app.core.database import Base, engine, SessionLocal
from app.modules.auth.models import User, Role
from app.modules.chat_engine.models import ChatConversation, QueryLearningMemory
from app.core.security import get_password_hash, create_access_token
from main import app

@pytest.fixture(scope="module")
def setup_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    
    # Ensure test user exists
    role = db.query(Role).filter(Role.name == "Economista").first()
    if not role:
        role = Role(name="Economista", description="Test Economista")
        db.add(role)
        db.commit()
        db.refresh(role)
        
    user = db.query(User).filter(User.username == "test_thread_user").first()
    if not user:
        user = User(
            username="test_thread_user",
            email="test_thread@empresa.com",
            hashed_password=get_password_hash("secret123"),
            is_admin=False,
            is_active=True,
            role_id=role.id
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    db.close()
    yield user

import uuid
from app.modules.auth.models import UserSession

@pytest.fixture
def auth_headers(setup_db):
    db = SessionLocal()
    jti = str(uuid.uuid4())
    token = create_access_token(subject=setup_db.id, jti=jti)
    session = UserSession(
        user_id=setup_db.id,
        jti=jti,
        is_revoked=False
    )
    db.add(session)
    db.commit()
    db.close()
    return {"Authorization": f"Bearer {token}"}



def test_chat_thread_crud(auth_headers):
    client = TestClient(app)
    
    # 1. Create a thread
    thread_payload = {
        "id": "thread-test-123",
        "title": "Análisis de Ventas Q3",
        "connection_id": 1,
        "results": [
            {
                "id": "q1",
                "question": "¿Cuáles son las ventas por categoría?",
                "summary_text": "Resumen de ventas",
                "data_columns": ["categoria", "monto"],
                "data_rows": [{"categoria": "Electrónica", "monto": 1000}],
                "traceability": {"sql_executed": "SELECT * FROM fact_ventas", "execution_time_ms": 12, "rows_returned": 1, "validation_status": "APROBADO", "schema_tables_used": ["fact_ventas"], "explanation": "OK"}
            }
        ]
    }
    
    res = client.post("/api/v1/chat/threads", json=thread_payload, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == "thread-test-123"
    assert data["title"] == "Análisis de Ventas Q3"
    assert len(data["results"]) == 1

    # 1.1 Upsert the same thread with updated title to verify idempotency (no UniqueViolation)
    thread_payload["title"] = "Análisis de Ventas Q3 - Actualizado"
    res_update = client.post("/api/v1/chat/threads", json=thread_payload, headers=auth_headers)
    assert res_update.status_code == 200
    assert res_update.json()["title"] == "Análisis de Ventas Q3 - Actualizado"
    
    # 2. List threads
    res_list = client.get("/api/v1/chat/threads", headers=auth_headers)
    assert res_list.status_code == 200
    threads = res_list.json()
    assert any(t["id"] == "thread-test-123" for t in threads)
    
    # 3. Get thread detail
    res_detail = client.get("/api/v1/chat/threads/thread-test-123", headers=auth_headers)
    assert res_detail.status_code == 200
    assert res_detail.json()["title"] == "Análisis de Ventas Q3 - Actualizado"
    
    # 4. Delete thread
    res_del = client.delete("/api/v1/chat/threads/thread-test-123", headers=auth_headers)
    assert res_del.status_code == 200
    assert res_del.json()["success"] is True

def test_chat_feedback(auth_headers):
    client = TestClient(app)
    
    feedback_payload = {
        "question": "cuanto se vendio en total",
        "sql": "SELECT SUM(monto) FROM fact_ventas;",
        "connection_id": 1,
        "rating": "positive",
        "comment": "Respuesta muy precisa"
    }
    
    res = client.post("/api/v1/chat/feedback", json=feedback_payload, headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["learning_saved"] is True

def test_conversation_context_prompt():
    from app.core.prompts import PromptManager
    
    history = [
        {"question": "Ventas por categoria", "sql": "SELECT * FROM fact_ventas;"}
    ]
    formatted = PromptManager.format_conversation_context(history)
    assert "Ventas por categoria" in formatted
    assert "SELECT * FROM fact_ventas;" in formatted
    assert "INSTRUCCIÓN MULTI-TURNO" in formatted
    
    user_prompt = PromptManager.get_text_to_sql_user_prompt(
        question="Y de esas cual fue la mas vendida?",
        user_role="Economista",
        schema_context="esquema demo",
        allowed_tables={"fact_ventas"},
        conversation_context=formatted
    )
    assert "Ventas por categoria" in user_prompt
    assert "Y de esas cual fue la mas vendida?" in user_prompt

