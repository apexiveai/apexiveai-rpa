from sqlalchemy.orm import Session
from app.models.rpa import Workflow, ExecutionRun

def execute_workflow(db: Session, workflow: Workflow) -> ExecutionRun:
    run = ExecutionRun(workflow_id=workflow.id, status="queued")
    db.add(run)
    db.commit()
    db.refresh(run)
    return run
