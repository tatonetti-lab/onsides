from fastapi import APIRouter, HTTPException, Query

from ..label_store import LabelStore, extract_drug_name
from ..models import LabelDetail, LabelSection, LabelSummary, TaskDefinition
from ..vocab_service import VocabService

router = APIRouter(prefix="/api/labels", tags=["labels"])

_label_store: LabelStore | None = None
_vocab_service: VocabService | None = None
_tasks: dict[str, TaskDefinition] = {}


def init(
    label_store: LabelStore,
    vocab_service: VocabService,
    tasks: dict[str, TaskDefinition],
) -> None:
    global _label_store, _vocab_service
    _label_store = label_store
    _vocab_service = vocab_service
    _tasks.update(tasks)


@router.get("")
def list_labels(
    task_id: str = Query(...),
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    search: str = Query(""),
    seed: int = Query(42),
) -> dict:
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(404, f"Task {task_id!r} not found")

    items, total = _label_store.list_labels(
        required_sections=task.sections,
        page=page,
        per_page=per_page,
        search=search,
        label_pool=task.label_pool,
        seed=seed,
    )
    return {
        "items": items,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": (total + per_page - 1) // per_page,
    }


@router.get("/{set_id}")
def get_label(set_id: str, task_id: str = Query(...)) -> LabelDetail:
    task = _tasks.get(task_id)
    if not task:
        raise HTTPException(404, f"Task {task_id!r} not found")

    label = _label_store.get_label(set_id)
    if not label:
        raise HTTPException(404, f"Label {set_id!r} not found")

    sections: list[LabelSection] = []
    for code in task.sections:
        text = label.get("sections", {}).get(code, "")
        if not text or not text.strip():
            continue

        all_matches = []
        for vs in task.vocab_sources:
            matches = _vocab_service.match_terms(text, vs.vocab_id, vs.highlight_color)
            all_matches.extend(matches)
        all_matches.sort(key=lambda m: m.start)

        sections.append(
            LabelSection(section_code=code, text=text, vocab_matches=all_matches)
        )

    title = label.get("title", "")
    return LabelDetail(
        set_id=label.get("set_id", set_id),
        title=title,
        drug_name=extract_drug_name(title),
        sections=sections,
    )
