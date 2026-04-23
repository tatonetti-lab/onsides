import json
import logging
from pathlib import Path

import duckdb

from .models import LabelSummary

logger = logging.getLogger(__name__)

DEFAULT_LABELS_DIR = Path("_onsides/us/labels")
DEFAULT_PARQUET_PATH = Path("_onsides/us/label_text.parquet")


class LabelStore:
    def __init__(
        self,
        labels_dir: Path = DEFAULT_LABELS_DIR,
        parquet_path: Path = DEFAULT_PARQUET_PATH,
    ):
        self._labels_dir = labels_dir
        self._parquet_path = parquet_path
        self._index: dict[str, dict] | None = None

    def _build_index(self) -> dict[str, dict]:
        if self._parquet_path.exists():
            return self._build_index_from_parquet()
        return self._build_index_from_files()

    def _build_index_from_parquet(self) -> dict[str, dict]:
        logger.info(f"Building label index from {self._parquet_path}")
        con = duckdb.connect()
        rows = con.execute(
            """
            SELECT set_id, title,
                   length(trim(coalesce(AR, ''))) > 0 AS has_AR,
                   length(trim(coalesce(BW, ''))) > 0 AS has_BW,
                   length(trim(coalesce(WP, ''))) > 0 AS has_WP,
                   length(trim(coalesce(WA, ''))) > 0 AS has_WA,
                   length(trim(coalesce(PR, ''))) > 0 AS has_PR,
                   length(trim(coalesce(SP, ''))) > 0 AS has_SP,
                   length(trim(coalesce(OV, ''))) > 0 AS has_OV
            FROM read_parquet(?)
            """,
            [str(self._parquet_path)],
        ).fetchall()
        con.close()

        index: dict[str, dict] = {}
        section_codes = ["AR", "BW", "WP", "WA", "PR", "SP", "OV"]
        for row in rows:
            set_id, title = row[0], row[1]
            has_sections = {
                code: bool(row[2 + i]) for i, code in enumerate(section_codes)
            }
            avail = [c for c, v in has_sections.items() if v]
            index[set_id] = {
                "set_id": set_id,
                "title": " ".join((title or "").split()),
                "date": "",
                "sections_available": avail,
            }
        logger.info(f"Indexed {len(index)} labels from parquet")
        return index

    def _build_index_from_files(self) -> dict[str, dict]:
        logger.info(f"Building label index from {self._labels_dir} (scanning files)")
        index: dict[str, dict] = {}
        for path in self._labels_dir.glob("*.json"):
            parts = path.stem.split("_", 1)
            date = parts[0] if len(parts) > 1 else ""
            set_id = parts[1] if len(parts) > 1 else path.stem
            try:
                with open(path) as f:
                    data = json.load(f)
                title = data.get("title", "")
                avail = [
                    code
                    for code, text in data.get("sections", {}).items()
                    if text and text.strip()
                ]
                index[set_id] = {
                    "set_id": set_id,
                    "title": " ".join((title or "").split()),
                    "date": date,
                    "sections_available": avail,
                }
            except Exception:
                logger.warning(f"Failed to read {path}", exc_info=True)
        logger.info(f"Indexed {len(index)} labels from files")
        return index

    @property
    def index(self) -> dict[str, dict]:
        if self._index is None:
            self._index = self._build_index()
        return self._index

    def list_labels(
        self,
        required_sections: list[str],
        page: int = 1,
        per_page: int = 50,
        search: str = "",
        label_pool: list[str] | None = None,
    ) -> tuple[list[LabelSummary], int]:
        required = set(required_sections)
        results = []
        for info in self.index.values():
            if label_pool and info["set_id"] not in label_pool:
                continue
            avail = set(info["sections_available"])
            if not required.intersection(avail):
                continue
            if search and search.lower() not in info["title"].lower():
                continue
            results.append(info)

        results.sort(key=lambda x: x["title"].lower())
        total = len(results)
        start = (page - 1) * per_page
        page_items = results[start : start + per_page]
        return [LabelSummary(**item) for item in page_items], total

    def get_label(self, set_id: str) -> dict | None:
        if set_id not in self.index:
            return None
        info = self.index[set_id]
        date = info["date"]
        path = self._labels_dir / f"{date}_{set_id}.json"
        if not path.exists():
            for p in self._labels_dir.glob(f"*_{set_id}.json"):
                path = p
                break
            else:
                return None
        with open(path) as f:
            return json.load(f)
