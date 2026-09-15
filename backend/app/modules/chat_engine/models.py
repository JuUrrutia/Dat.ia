import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
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
    is_golden = Column(Boolean, default=False, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class ChatConversation(Base):
    """
    Persistent chat conversation thread containing user query history and analytics results.
    """
    __tablename__ = "chat_conversations"

    id = Column(String(64), primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    connection_id = Column(Integer, nullable=True, default=1)
    messages_json = Column(Text, nullable=False, default="[]")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class DashboardWidget(Base):
    """
    Persistent dashboard widget pinned by user from analytics responses.
    """
    __tablename__ = "dashboard_widgets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    connection_id = Column(Integer, nullable=True, default=1)
    chart_type = Column(String(50), default="bar")
    chart_option_json = Column(Text, nullable=False)
    kpis_json = Column(Text, nullable=True)
    query_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

