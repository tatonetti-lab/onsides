import argparse
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .annotation_store import AnnotationStore
from .label_store import LabelStore
from .routers import annotations, labels, tasks, vocab
from .task_config import load_tasks
from .vocab_service import VocabService

logger = logging.getLogger(__name__)

STATIC_DIR = Path(__file__).parent / "static"


def create_app(
    annotations_dir: Path = Path("annotations"),
    labels_dir: Path = Path("_onsides/us/labels"),
    parquet_path: Path = Path("_onsides/us/label_text.parquet"),
) -> FastAPI:
    label_store = LabelStore(labels_dir=labels_dir, parquet_path=parquet_path)
    vocab_service = VocabService()
    annotation_store = AnnotationStore(base_dir=annotations_dir)
    task_defs = load_tasks()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Load vocabularies on startup
        for task in task_defs.values():
            for vs in task.vocab_sources:
                vocab_service.load_vocab(vs.vocab_id, vs.path)
        # Warm the label index
        _ = label_store.index
        logger.info(
            f"Ready: {len(task_defs)} tasks, {len(label_store.index)} labels"
        )
        yield

    app = FastAPI(title="OnSIDES Annotator", lifespan=lifespan)

    # Initialize routers with shared state
    tasks.init(task_defs)
    labels.init(label_store, vocab_service, task_defs)
    annotations.init(annotation_store)
    vocab.init(vocab_service, task_defs)

    app.include_router(tasks.router)
    app.include_router(labels.router)
    app.include_router(annotations.router)
    app.include_router(vocab.router)

    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description="OnSIDES Annotation Tool")
    parser.add_argument(
        "--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port (default: 8000)"
    )
    parser.add_argument(
        "--annotations-dir",
        type=Path,
        default=Path("annotations"),
        help="Directory for annotation storage",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s: %(message)s",
    )

    import uvicorn

    app = create_app(annotations_dir=args.annotations_dir)
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
