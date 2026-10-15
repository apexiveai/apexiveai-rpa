import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func, select, update
from app.db import get_db
from app.core.config import settings
from app.models.rpa import RPAProject, Workflow, ExecutionRun, RobotWorker, AuditLog
from app.schemas.rpa import (
    ProjectCreate, ProjectOut, WorkflowCreate, WorkflowUpdate, WorkflowOut,
    RunOut, RobotClaim, RobotStatus, RobotRunOut, RobotCompletion,
)
from app.services.engine import execute_workflow

router = APIRouter(prefix="/rpa", tags=["RPA"])

@router.get("/health")
def health():
    return {"status": "ok", "service": "rpa"}

@router.post("/projects", response_model=ProjectOut)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    if db.scalar(select(RPAProject).where(RPAProject.name == payload.name)):
        raise HTTPException(409, "Project already exists")
    obj = RPAProject(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@router.get("/projects", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return list(db.scalars(select(RPAProject).order_by(RPAProject.id.desc())))

@router.post("/workflows", response_model=WorkflowOut)
def create_workflow(payload: WorkflowCreate, db: Session = Depends(get_db)):
    if not db.get(RPAProject, payload.project_id):
        raise HTTPException(404, "Project not found")
    obj = Workflow(**payload.model_dump())
    db.add(obj); db.commit(); db.refresh(obj)
    return obj

@router.get("/projects/{project_id}/workflows", response_model=list[WorkflowOut])
def list_workflows(project_id: int, db: Session = Depends(get_db)):
    if not db.get(RPAProject, project_id):
        raise HTTPException(404, "Project not found")
    return list(db.scalars(
        select(Workflow).where(Workflow.project_id == project_id).order_by(Workflow.id.desc())
    ))

@router.get("/workflows/{workflow_id}", response_model=WorkflowOut)
def get_workflow(workflow_id: int, db: Session = Depends(get_db)):
    obj = db.get(Workflow, workflow_id)
    if not obj:
        raise HTTPException(404, "Workflow not found")
    return obj

@router.put("/workflows/{workflow_id}", response_model=WorkflowOut)
def update_workflow(workflow_id: int, payload: WorkflowUpdate, db: Session = Depends(get_db)):
    obj = db.get(Workflow, workflow_id)
    if not obj:
        raise HTTPException(404, "Workflow not found")
    obj.name = payload.name
    obj.interval_seconds = payload.interval_seconds
    obj.definition = payload.definition
    db.commit(); db.refresh(obj)
    return obj

@router.patch("/workflows/{workflow_id}/enabled", response_model=WorkflowOut)
def set_enabled(workflow_id: int, enabled: bool, db: Session = Depends(get_db)):
    obj = db.get(Workflow, workflow_id)
    if not obj: raise HTTPException(404, "Workflow not found")
    obj.enabled = enabled
    db.commit(); db.refresh(obj)
    return obj

@router.post("/workflows/{workflow_id}/run", response_model=RunOut)
def run_workflow(workflow_id: int, db: Session = Depends(get_db)):
    obj = db.get(Workflow, workflow_id)
    if not obj: raise HTTPException(404, "Workflow not found")
    return execute_workflow(db, obj)

@router.get("/runs", response_model=list[RunOut])
def list_runs(db: Session = Depends(get_db)):
    return list(db.scalars(select(ExecutionRun).order_by(ExecutionRun.id.desc()).limit(100)))

def authenticate_robot(x_robot_token: str | None = Header(default=None)):
    if not settings.robot_token:
        raise HTTPException(503, "Windows Robot authentication is not configured")
    if not x_robot_token or not secrets.compare_digest(x_robot_token, settings.robot_token):
        raise HTTPException(401, "Invalid robot token")

@router.get("/robot/status", response_model=RobotStatus)
def robot_status(db: Session = Depends(get_db)):
    cutoff = datetime.utcnow() - timedelta(seconds=30)
    count = db.scalar(
        select(func.count(RobotWorker.id)).where(RobotWorker.last_seen >= cutoff)
    ) or 0
    return {"online": count > 0, "workers": count}

@router.post("/robot/heartbeat", response_model=RobotStatus, dependencies=[Depends(authenticate_robot)])
def robot_heartbeat(payload: RobotClaim, db: Session = Depends(get_db)):
    worker = db.scalar(select(RobotWorker).where(RobotWorker.name == payload.worker_name))
    if worker is None:
        worker = RobotWorker(name=payload.worker_name)
        db.add(worker)
    worker.last_seen = datetime.utcnow()
    db.commit()
    return robot_status(db)

@router.post("/robot/claim", response_model=RobotRunOut | None, dependencies=[Depends(authenticate_robot)])
def claim_robot_run(payload: RobotClaim, db: Session = Depends(get_db)):
    while True:
        worker = db.scalar(select(RobotWorker).where(RobotWorker.name == payload.worker_name))
        if worker is None:
            worker = RobotWorker(name=payload.worker_name)
            db.add(worker)
            db.flush()
        worker.last_seen = datetime.utcnow()
        run_id = db.scalar(
            select(ExecutionRun.id)
            .where(ExecutionRun.status == "queued")
            .order_by(ExecutionRun.id)
            .limit(1)
        )
        if run_id is None:
            worker.current_run_id = None
            db.commit()
            return None
        claimed = db.execute(
            update(ExecutionRun)
            .where(ExecutionRun.id == run_id, ExecutionRun.status == "queued")
            .values(status="running", started_at=datetime.utcnow())
        )
        if claimed.rowcount != 1:
            db.rollback()
            continue
        run = db.get(ExecutionRun, run_id)
        workflow = db.get(Workflow, run.workflow_id)
        worker.current_run_id = run.id
        db.add(AuditLog(
            action="robot.claim",
            resource="execution_run",
            resource_id=str(run.id),
            actor=payload.worker_name,
            details={"workflow_id": workflow.id},
        ))
        db.commit()
        return RobotRunOut(
            run_id=run.id,
            workflow_id=workflow.id,
            workflow_name=workflow.name,
            definition=workflow.definition,
        )

@router.post(
    "/robot/runs/{run_id}/complete",
    response_model=RunOut,
    dependencies=[Depends(authenticate_robot)],
)
def complete_robot_run(run_id: int, payload: RobotCompletion, db: Session = Depends(get_db)):
    run = db.get(ExecutionRun, run_id)
    if not run:
        raise HTTPException(404, "Execution run not found")
    if run.status != "running":
        raise HTTPException(409, "Execution run is not assigned to a robot")
    run.status = payload.status
    run.finished_at = datetime.utcnow()
    run.error = payload.error if payload.status == "failed" else None
    run.output = payload.output
    db.add(AuditLog(
        action=f"robot.{payload.status}",
        resource="execution_run",
        resource_id=str(run.id),
        details={"error": run.error, "output": run.output},
    ))
    worker = db.scalar(
        select(RobotWorker).where(RobotWorker.current_run_id == run.id)
    )
    if worker is not None:
        worker.current_run_id = None
        worker.last_seen = datetime.utcnow()
    db.commit(); db.refresh(run)
    return run
