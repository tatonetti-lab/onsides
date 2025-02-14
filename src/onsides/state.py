from pathlib import Path

from attrs import define, field
from rich.progress import Progress, TaskID, TextColumn
from sqlalchemy import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlmodel import create_engine

DEFAULT_DIRECTORY = Path("_onsides")


def ensure_exists(instance, attribute, value: Path):  # noqa: ARG001
    value.mkdir(exist_ok=True, parents=True)


@define
class State:
    directory: Path = field(default=DEFAULT_DIRECTORY, validator=[ensure_exists])
    force: bool = False
    sqlite_path: str | None = None
    progress: Progress = Progress(
        *Progress.get_default_columns(), TextColumn("{task.completed} of {task.total}")
    )
    tasks: dict[str, TaskID] = {}

    _engine: Engine | None = None
    _async_engine: AsyncEngine | None = None

    def get_engine(self) -> Engine:
        if self._engine is None:
            if self.sqlite_path is None:
                raise ValueError("No sqlite path found")
            self._engine = create_engine(f"sqlite:///{self.sqlite_path}")
        return self._engine

    def get_async_engine(self) -> AsyncEngine:
        if self._async_engine is None:
            if self.sqlite_path is None:
                raise ValueError("No sqlite path found")
            self._async_engine = create_async_engine(
                f"sqlite+aiosqlite:///{self.sqlite_path}"
            )
        return self._async_engine

    def get_async_session(self) -> async_sessionmaker[AsyncSession]:
        engine = self.get_async_engine()
        return async_sessionmaker(engine, expire_on_commit=False)

    def add_task(self, task_name: str, description: str, total: int | None) -> TaskID:
        task = self.progress.add_task(description, total=total)
        self.tasks[task_name] = task
        return task

    def get_task(self, task_name: str) -> TaskID:
        return self.tasks[task_name]
