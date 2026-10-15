from pydantic import BaseModel, Field
from typing import Any

class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    description: str | None = None

class ProjectOut(ProjectCreate):
    id: int
    status: str
    version: str
    model_config = {"from_attributes": True}

class WorkflowCreate(BaseModel):
    project_id: int
    name: str = Field(min_length=2, max_length=160)
    interval_seconds: int | None = Field(default=None, ge=10)
    definition: dict[str, Any] = Field(default_factory=dict)

class WorkflowUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=160)
    interval_seconds: int | None = Field(default=None, ge=10)
    definition: dict[str, Any] = Field(default_factory=dict)

class WorkflowOut(WorkflowCreate):
    id: int
    enabled: bool
    model_config = {"from_attributes": True}

class RunOut(BaseModel):
    id: int
    workflow_id: int
    status: str
    error: str | None
    output: dict[str, Any]
    model_config = {"from_attributes": True}

class RobotClaim(BaseModel):
    worker_name: str = Field(min_length=1, max_length=160)

class RobotStatus(BaseModel):
    online: bool
    workers: int

class RobotRunOut(BaseModel):
    run_id: int
    workflow_id: int
    workflow_name: str
    definition: dict[str, Any]

class RobotCompletion(BaseModel):
    status: str = Field(pattern="^(success|failed)$")
    output: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None
