from fastapi import APIRouter, HTTPException, Query

from ..models import TaskDefinition, VocabSearchResult
from ..vocab_service import VocabService

router = APIRouter(prefix="/api/vocab", tags=["vocab"])

_vocab_service: VocabService | None = None
_tasks: dict[str, TaskDefinition] = {}


def init(vocab_service: VocabService, tasks: dict[str, TaskDefinition]) -> None:
    global _vocab_service
    _vocab_service = vocab_service
    _tasks.update(tasks)


@router.get("/search")
def search_vocab(
    task_id: str = Query(...),
    q: str = Query(..., min_length=2),
    limit: int = Query(50, ge=1, le=200),
) -> list[VocabSearchResult]:
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(404, f"Task {task_id!r} not found")

    results: list[VocabSearchResult] = []
    for vs in task.vocab_sources:
        results.extend(
            _vocab_service.search_vocab(q, vs.vocab_id, limit=limit)
        )
    return results[:limit]
