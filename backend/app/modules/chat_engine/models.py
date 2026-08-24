import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from app.core.database import Base

class QueryLearningMemory(Base):
    """
    Persistent self-learning memory for successful and self-healed SQL queries.
    Enables autonomous In-Context Few-Shot retrieval without requiring manual user training.
    """
    __tablename__ = "query_learning_memories"

    id = Column(Integer, primary_key=True, index=True)
    question_pattern = Column(String(500), index=True, nullable=False)
    connection_id = Column(Integer, nullable=False, default=1)
    user_role = Column(String(100), nullable=True)
    successful_sql = Column(Text, nullable=False)
    tables_used = Column(String(255), nullable=True)
    execution_count = Column(Integer, default=1)
    was_self_healed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
