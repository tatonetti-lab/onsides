import json
import logging
import tempfile
from pathlib import Path

from .models import AnnotationDocument, AnnotationListItem

logger = logging.getLogger(__name__)

DEFAULT_ANNOTATIONS_DIR = Path("annotations")


class AnnotationStore:
    def __init__(self, base_dir: Path = DEFAULT_ANNOTATIONS_DIR):
        self._base_dir = base_dir

    def _path(self, task_id: str, annotator: str, label_id: str) -> Path:
        return self._base_dir / task_id / annotator / f"{label_id}.json"

    def save(self, doc: AnnotationDocument) -> None:
        path = self._path(doc.task_id, doc.annotator, doc.label_id)
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(
            dir=path.parent, suffix=".tmp", prefix=".ann_"
        )
        try:
            with open(fd, "w") as f:
                f.write(doc.model_dump_json(indent=2))
            Path(tmp).replace(path)
        except Exception:
            Path(tmp).unlink(missing_ok=True)
            raise
        logger.debug(f"Saved annotation: {path}")

    def load(
        self, task_id: str, annotator: str, label_id: str
    ) -> AnnotationDocument | None:
        path = self._path(task_id, annotator, label_id)
        if not path.exists():
            return None
        with open(path) as f:
            return AnnotationDocument(**json.load(f))

    def list_for_annotator(
        self, task_id: str, annotator: str
    ) -> list[AnnotationListItem]:
        ann_dir = self._base_dir / task_id / annotator
        if not ann_dir.exists():
            return []
        items: list[AnnotationListItem] = []
        for path in sorted(ann_dir.glob("*.json")):
            try:
                with open(path) as f:
                    data = json.load(f)
                count = sum(
                    len(anns) for anns in data.get("sections", {}).values()
                )
                items.append(
                    AnnotationListItem(
                        label_id=data["label_id"],
                        label_title=data.get("label_title", ""),
                        status=data.get("status", "in_progress"),
                        updated_at=data.get("updated_at", ""),
                        annotation_count=count,
                    )
                )
            except Exception:
                logger.warning(f"Failed to read {path}", exc_info=True)
        return items

    def get_status(self, task_id: str, label_id: str) -> dict[str, str]:
        """Return annotator → status mapping for a label."""
        task_dir = self._base_dir / task_id
        if not task_dir.exists():
            return {}
        statuses: dict[str, str] = {}
        for annotator_dir in task_dir.iterdir():
            if not annotator_dir.is_dir():
                continue
            path = annotator_dir / f"{label_id}.json"
            if path.exists():
                try:
                    with open(path) as f:
                        data = json.load(f)
                    statuses[annotator_dir.name] = data.get(
                        "status", "in_progress"
                    )
                except Exception:
                    pass
        return statuses
