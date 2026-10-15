import os
from pathlib import Path
import tempfile

os.environ.setdefault("SECRET_KEY", "test-secret-key")
_test_database_path = Path(tempfile.gettempdir()) / f"apexive-rpa-tests-{os.getpid()}.db"
os.environ["DATABASE_URL"] = f"sqlite:///{_test_database_path.as_posix()}"
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("ROBOT_TOKEN", "test-robot-token")

import pytest
from fastapi.testclient import TestClient

from app.db import Base, engine
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def cleanup_test_database():
    yield
    engine.dispose()
    _test_database_path.unlink(missing_ok=True)


@pytest.fixture()
def client():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    with TestClient(app) as test_client:
        yield test_client
    Base.metadata.drop_all(bind=engine)


def test_workflow_can_be_designed_queued_and_completed_by_robot(client):
    project_response = client.post(
        "/api/rpa/projects",
        json={"name": "Test automation", "description": "API test"},
    )
    assert project_response.status_code == 200
    project_id = project_response.json()["id"]

    workflow_response = client.post(
        "/api/rpa/workflows",
        json={
            "project_id": project_id,
            "name": "Desktop workflow",
            "definition": {"steps": [{"action": "log", "message": "hello"}]},
        },
    )
    assert workflow_response.status_code == 200
    workflow_id = workflow_response.json()["id"]

    saved = client.put(
        f"/api/rpa/workflows/{workflow_id}",
        json={
            "name": "Updated desktop workflow",
            "definition": {"steps": [{"action": "log", "message": "updated"}]},
        },
    )
    assert saved.status_code == 200
    assert saved.json()["definition"]["steps"][0]["message"] == "updated"
    assert len(client.get(f"/api/rpa/projects/{project_id}/workflows").json()) == 1

    queued = client.post(f"/api/rpa/workflows/{workflow_id}/run")
    assert queued.status_code == 200
    assert queued.json()["status"] == "queued"
    assert client.get("/api/rpa/robot/status").json() == {"online": False, "workers": 0}

    unauthorized = client.post("/api/rpa/robot/claim", json={"worker_name": "test-robot"})
    assert unauthorized.status_code == 401
    headers = {"X-Robot-Token": "test-robot-token"}
    claimed = client.post(
        "/api/rpa/robot/claim",
        json={"worker_name": "test-robot"},
        headers=headers,
    )
    assert claimed.status_code == 200
    assert claimed.json()["workflow_id"] == workflow_id
    assert claimed.json()["definition"]["steps"][0]["message"] == "updated"
    assert client.get("/api/rpa/robot/status").json() == {"online": True, "workers": 1}
    assert client.post(
        "/api/rpa/robot/claim",
        json={"worker_name": "test-robot"},
        headers=headers,
    ).json() is None

    completed = client.post(
        f"/api/rpa/robot/runs/{queued.json()['id']}/complete",
        headers=headers,
        json={"status": "success", "output": {"steps": [{"status": "success"}]}},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "success"
    assert completed.json()["output"]["steps"][0]["status"] == "success"


def test_robot_rejects_invalid_tokens_and_duplicate_completion(client):
    project = client.post("/api/rpa/projects", json={"name": "Robot auth"}).json()
    workflow = client.post(
        "/api/rpa/workflows",
        json={"project_id": project["id"], "name": "Test", "definition": {"steps": []}},
    ).json()
    run = client.post(f"/api/rpa/workflows/{workflow['id']}/run").json()

    rejected = client.post(
        "/api/rpa/robot/claim",
        headers={"X-Robot-Token": "wrong"},
        json={"worker_name": "test-robot"},
    )
    assert rejected.status_code == 401

    headers = {"X-Robot-Token": "test-robot-token"}
    claimed = client.post(
        "/api/rpa/robot/claim",
        headers=headers,
        json={"worker_name": "test-robot"},
    )
    assert claimed.status_code == 200
    completed = client.post(
        f"/api/rpa/robot/runs/{run['id']}/complete",
        headers=headers,
        json={"status": "failed", "error": "Expected test failure"},
    )
    assert completed.status_code == 200
    assert completed.json()["status"] == "failed"
    duplicate = client.post(
        f"/api/rpa/robot/runs/{run['id']}/complete",
        headers=headers,
        json={"status": "success"},
    )
    assert duplicate.status_code == 409
