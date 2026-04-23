from fastapi import APIRouter, HTTPException

from ..models import TaskDefinition

router = APIRouter(prefix="/api/tasks", tags=["tasks"])

_tasks: dict[str, TaskDefinition] = {}


def init(tasks: dict[str, TaskDefinition]) -> None:
    _tasks.update(tasks)


@router.get("")
def list_tasks() -> list[TaskDefinition]:
    return list(_tasks.values())


@router.get("/{task_id}")
def get_task(task_id: str) -> TaskDefinition:
    if task_id not in _tasks:
        raise HTTPException(404, f"Task {task_id!r} not found")
    return _tasks[task_id]
