import json
import logging
import random
import re
from pathlib import Path

import duckdb

from .models import LabelSummary

logger = logging.getLogger(__name__)

DEFAULT_LABELS_DIR = Path("_onsides/us/labels")
DEFAULT_PARQUET_PATH = Path("_onsides/us/label_text.parquet")

_DOSAGE_FORM_RE = re.compile(
    r"([\s,]+(USP|tablets?|capsules?|injection|solution|oral|for|"
    r"extended[- ]release|delayed[- ]release))+\s*$",
    re.IGNORECASE,
)


def extract_drug_name(title: str) -> str:
    if not title:
        return ""
    m = re.search(r"to use\s+(.+?)\s+safely", title, re.IGNORECASE)
    if m:
        name = _DOSAGE_FORM_RE.sub("", m.group(1).strip()).rstrip(" ,")
        if name:
            return name
    m = re.search(r"prescribing information for\s+(.+?)[.\n]", title, re.IGNORECASE)
    if m:
        name = _DOSAGE_FORM_RE.sub("", m.group(1).strip()).rstrip(" ,")
        if name:
            return name
    first = title.split("\n")[0].strip()
    first = re.sub(
        r"^HIGHLIGHTS OF PRESCRIBING INFORMATION\s*", "", first, flags=re.IGNORECASE
    ).strip()
    first = re.sub(r"^These highlights.*", "", first, flags=re.IGNORECASE).strip()
    if first:
        return first[:80]
    return title[:80]


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
            clean_title = " ".join((title or "").split())
            index[set_id] = {
                "set_id": set_id,
                "title": clean_title,
                "drug_name": extract_drug_name(title or ""),
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
                clean_title = " ".join((title or "").split())
                index[set_id] = {
                    "set_id": set_id,
                    "title": clean_title,
                    "drug_name": extract_drug_name(title or ""),
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
        seed: int = 42,
    ) -> tuple[list[LabelSummary], int]:
        required = set(required_sections)
        results = []
        for info in self.index.values():
            if not info["title"]:
                continue
            if label_pool and info["set_id"] not in label_pool:
                continue
            avail = set(info["sections_available"])
            if not required.intersection(avail):
                continue
            if search:
                q = search.lower()
                if q not in info["title"].lower() and q not in info["drug_name"].lower():
                    continue
            filtered = {
                **info,
                "sections_available": [s for s in info["sections_available"] if s in required],
            }
            results.append(filtered)

        if search:
            results.sort(key=lambda x: x["title"].lower())
        else:
            rng = random.Random(seed)
            rng.shuffle(results)

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
