from fastapi import APIRouter, HTTPException

from ..annotation_store import AnnotationStore
from ..models import AnnotationDocument, AnnotationListItem

router = APIRouter(prefix="/api/annotations", tags=["annotations"])

_store: AnnotationStore | None = None


def init(store: AnnotationStore) -> None:
    global _store
    _store = store


@router.get("/{task_id}/{annotator}/{label_id}")
def load_annotation(
    task_id: str, annotator: str, label_id: str
) -> AnnotationDocument | None:
    doc = _store.load(task_id, annotator, label_id)
    if not doc:
        return None
    return doc


@router.put("/{task_id}/{annotator}/{label_id}")
def save_annotation(
    task_id: str, annotator: str, label_id: str, doc: AnnotationDocument
) -> dict:
    if doc.task_id != task_id or doc.annotator != annotator or doc.label_id != label_id:
        raise HTTPException(400, "Path parameters must match document fields")
    _store.save(doc)
    return {"status": "saved"}


@router.get("/{task_id}/{annotator}")
def list_annotations(
    task_id: str, annotator: str
) -> list[AnnotationListItem]:
    return _store.list_for_annotator(task_id, annotator)
