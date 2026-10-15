from datetime import datetime
from sqlalchemy import String, Text, Boolean, DateTime, ForeignKey, Integer, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base

class RPAProject(Base):
    __tablename__ = "rpa_projects"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    description: Mapped[str | None] = mapped_column(Text())
    status: Mapped[str] = mapped_column(String(30), default="draft")
    version: Mapped[str] = mapped_column(String(30), default="1.0.0")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    workflows = relationship("Workflow", back_populates="project", cascade="all, delete-orphan")

class Workflow(Base):
    __tablename__ = "workflows"
    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("rpa_projects.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(160))
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    interval_seconds: Mapped[int | None] = mapped_column(Integer)
    definition: Mapped[dict] = mapped_column(JSON, default=dict)
    project = relationship("RPAProject", back_populates="workflows")
    runs = relationship("ExecutionRun", back_populates="workflow", cascade="all, delete-orphan")

class ExecutionRun(Base):
    __tablename__ = "execution_runs"
    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[int] = mapped_column(ForeignKey("workflows.id", ondelete="CASCADE"), index=True)
    status: Mapped[str] = mapped_column(String(30), default="queued")
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)
    error: Mapped[str | None] = mapped_column(Text())
    output: Mapped[dict] = mapped_column(JSON, default=dict)
    workflow = relationship("Workflow", back_populates="runs")

class RobotWorker(Base):
    __tablename__ = "robot_workers"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    current_run_id: Mapped[int | None] = mapped_column(
        ForeignKey("execution_runs.id", ondelete="SET NULL"),
        nullable=True,
    )

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    action: Mapped[str] = mapped_column(String(100), index=True)
    resource: Mapped[str] = mapped_column(String(100))
    resource_id: Mapped[str | None] = mapped_column(String(100))
    actor: Mapped[str] = mapped_column(String(160), default="system")
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
