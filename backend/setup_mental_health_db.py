import sqlite3
import os
import sys

# Ensure backend path is in sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.core.database import SessionLocal, engine, Base
from app.models.role import Role
from app.models.permission import RoleTablePermission
from app.models.catalog import SemanticCatalog
from app.db.init_db import init_db

def setup_mental_health_catalog():
    print("=== INTEGRANDO MENTAL_HEALTH.SQLITE EN DATIA ===")
    
    db_path = settings.SQLITE_DB_PATH
    print(f"Base de datos objetivo: {db_path}")

    if not os.path.exists(db_path):
        print(f"ERROR: No se encontró el archivo de base de datos en {db_path}")
        sys.exit(1)

    # 1. Inspect target SQLite database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    tables = [t[0] for t in cursor.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
    print(f"Tablas encontradas en {os.path.basename(db_path)}: {tables}")

    for t in tables:
        t_lower = t.lower()
        if t_lower == "answer":
            count = cursor.execute("SELECT COUNT(*) FROM Answer").fetchone()[0]
            print(f"  -> Tabla `{t}`: {count} registros")
        elif t_lower == "question":
            count = cursor.execute("SELECT COUNT(*) FROM Question").fetchone()[0]
            print(f"  -> Tabla `{t}`: {count} registros")
        elif t_lower == "survey":
            count = cursor.execute("SELECT COUNT(*) FROM Survey").fetchone()[0]
            print(f"  -> Tabla `{t}`: {count} registros")
        else:
            print(f"  -> Tabla `{t}` encontrada")
    conn.close()

    # 2. Init App Metadata Database (Roles, Users, etc.)
    db = SessionLocal()
    try:
        init_db(db)

        # 3. Seed RoleTablePermissions for Answer, Question, Survey
        roles = db.query(Role).all()
        target_tables = ["Answer", "Question", "Survey", "answer", "question", "survey"]

        for role in roles:
            if role.name == "Usuario":
                continue # Unassigned users have 0 permissions by design
            
            for tbl in ["Answer", "Question", "Survey"]:
                existing = db.query(RoleTablePermission).filter(
                    RoleTablePermission.role_id == role.id,
                    RoleTablePermission.table_name.ilike(tbl)
                ).first()

                if not existing:
                    db.add(RoleTablePermission(
                        role_id=role.id,
                        connection_id=1,
                        schema_name="main",
                        table_name=tbl,
                        is_allowed=True
                    ))
                    print(f"Permiso de lectura otorgado: Rol '{role.name}' -> Tabla '{tbl}'")

        # 4. Seed Semantic Catalog
        catalog_items = [
            # Answer table
            ("Answer", "AnswerText", "Texto literal de la respuesta entregada por el encuestado (ej. Yes, No, Age, Country)"),
            ("Answer", "SurveyID", "Año de edición de la encuesta (2014, 2016, 2017, 2018, 2019)"),
            ("Answer", "UserID", "Identificador único anónimo del participante encuestado"),
            ("Answer", "QuestionID", "ID de la pregunta correspondiente (relacionado con Question.questionid)"),
            
            # Question table
            ("Question", "questiontext", "Texto descriptivo de la pregunta formulada en la encuesta de salud mental"),
            ("Question", "questionid", "Identificador numérico único de la pregunta"),
            
            # Survey table
            ("Survey", "SurveyID", "Año de realización de la encuesta OSMI (2014-2019)"),
            ("Survey", "Description", "Descripción oficial de la encuesta anual OSMI de salud mental en tech")
        ]

        for tbl, col, desc in catalog_items:
            existing_cat = db.query(SemanticCatalog).filter(
                SemanticCatalog.connection_id == 1,
                SemanticCatalog.table_name.ilike(tbl),
                SemanticCatalog.column_name.ilike(col)
            ).first()

            if not existing_cat:
                db.add(SemanticCatalog(
                    connection_id=1,
                    table_name=tbl,
                    column_name=col,
                    description=desc
                ))
                print(f"Catálogo Semántico registrado: `{tbl}.{col}` -> {desc}")

        db.commit()
        print("=== MENTAL_HEALTH.SQLITE REGISTRADA CON ÉXITO EN EL CATÁLOGO DE DATIA ===")

    except Exception as e:
        db.rollback()
        print(f"ERROR durante el registro del catálogo semántico: {e}")
        raise e
    finally:
        db.close()

if __name__ == "__main__":
    setup_mental_health_catalog()
