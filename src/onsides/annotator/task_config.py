import logging
from pathlib import Path

import yaml

from .models import TaskDefinition

logger = logging.getLogger(__name__)

TASKS_DIR = Path(__file__).parent / "tasks"


def load_tasks(tasks_dir: Path = TASKS_DIR) -> dict[str, TaskDefinition]:
    tasks: dict[str, TaskDefinition] = {}
    for path in sorted(tasks_dir.glob("*.yaml")):
        with open(path) as f:
            raw = yaml.safe_load(f)
        task = TaskDefinition(**raw)
        tasks[task.task_id] = task
        logger.info(f"Loaded task: {task.task_id} ({task.name})")
    return tasks
