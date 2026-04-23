import logging

from onsides.construct_training_data import (
    MedDRAVocab,
    find_terms_in_text,
    load_meddra_vocab,
)

from .models import VocabMatch, VocabSearchResult

logger = logging.getLogger(__name__)


class VocabService:
    def __init__(self) -> None:
        self._vocabs: dict[str, MedDRAVocab] = {}

    def load_vocab(self, vocab_id: str, path: str) -> None:
        if vocab_id in self._vocabs:
            return
        logger.info(f"Loading vocabulary: {vocab_id} from {path}")
        vocab = load_meddra_vocab(vocab_path=path)
        self._vocabs[vocab_id] = vocab
        logger.info(
            f"Loaded {vocab_id}: {len(vocab.code_to_term)} terms, "
            f"{len(vocab.llt_to_pt)} LLT→PT mappings"
        )

    def get_vocab(self, vocab_id: str) -> MedDRAVocab:
        if vocab_id not in self._vocabs:
            raise ValueError(f"Vocabulary {vocab_id!r} not loaded")
        return self._vocabs[vocab_id]

    def match_terms(
        self, text: str, vocab_id: str, highlight_color: str = "#fff3cd"
    ) -> list[VocabMatch]:
        vocab = self.get_vocab(vocab_id)
        found = find_terms_in_text(text.lower(), vocab)

        matches = [
            VocabMatch(
                term=f.term,
                code=f.code,
                start=f.start,
                length=f.length,
                pt_code=f.pt_code,
                pt_name=f.pt_name,
                vocab_id=vocab_id,
            )
            for f in found
            if f.length >= 4
        ]

        return _resolve_overlaps(matches)

    def search_vocab(
        self, query: str, vocab_id: str, limit: int = 50
    ) -> list[VocabSearchResult]:
        vocab = self.get_vocab(vocab_id)
        query_lower = query.lower()
        results: list[VocabSearchResult] = []

        for code, term in vocab.code_to_term.items():
            if query_lower in term.lower():
                pt_code, pt_name = vocab.llt_to_pt.get(code, (None, None))
                results.append(
                    VocabSearchResult(
                        term=term,
                        code=code,
                        pt_code=pt_code,
                        pt_name=pt_name,
                        vocab_id=vocab_id,
                    )
                )
                if len(results) >= limit:
                    break
        return results


def _resolve_overlaps(matches: list[VocabMatch]) -> list[VocabMatch]:
    """Keep longest non-overlapping matches for display."""
    if not matches:
        return []

    by_length = sorted(matches, key=lambda m: m.length, reverse=True)
    kept: list[VocabMatch] = []
    occupied: list[tuple[int, int]] = []

    for m in by_length:
        m_start, m_end = m.start, m.start + m.length
        overlaps = any(
            not (m_end <= s or m_start >= e) for s, e in occupied
        )
        if not overlaps:
            kept.append(m)
            occupied.append((m_start, m_end))

    return sorted(kept, key=lambda m: m.start)
