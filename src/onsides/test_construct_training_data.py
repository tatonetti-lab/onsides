"""Tests for onsides.construct_training_data module."""

import json
import random
import tempfile
from pathlib import Path

import pytest
from ahocorasick import Automaton

from onsides.construct_training_data import (
    AnnotationRecord,
    FoundTerm,
    MedDRAVocab,
    MethodConfig,
    _resolve_sections,
    construct_reference_set,
    find_terms_in_text,
    generate_example,
    get_method_config,
    load_annotations,
    write_reference_csv,
)


# ---------------------------------------------------------------------------
# MethodConfig
# ---------------------------------------------------------------------------

class TestMethodConfig:
    def test_method_0(self):
        cfg = get_method_config(0)
        assert cfg.sub_event is True
        assert cfg.prepend_event is True
        assert cfg.prepend_source is False
        assert cfg.prop_before == 0.5

    def test_method_14(self):
        cfg = get_method_config(14)
        assert cfg.sub_event is True
        assert cfg.prepend_event is True
        assert cfg.prepend_source is True
        assert cfg.prop_before == 0.125

    def test_all_methods_valid(self):
        for m in range(16):
            cfg = get_method_config(m)
            assert isinstance(cfg, MethodConfig)

    def test_invalid_method_raises(self):
        with pytest.raises(ValueError, match="Unknown method"):
            get_method_config(16)
        with pytest.raises(ValueError, match="Unknown method"):
            get_method_config(-1)


# ---------------------------------------------------------------------------
# generate_example
# ---------------------------------------------------------------------------

class TestGenerateExample:
    TEXT = "the patient reported severe headache and nausea after treatment"
    TERM = "headache"
    START = 30  # position of "headache" in TEXT
    LENGTH = 8

    def test_method_0_basic(self):
        cfg = get_method_config(0)
        result = generate_example(
            self.TEXT, self.TERM, self.START, self.LENGTH, 20, cfg
        )
        assert "headache" in result  # prepended
        assert "EVENT" in result  # substituted
        assert result.startswith("headache")

    def test_method_3_no_changes(self):
        cfg = get_method_config(3)
        result = generate_example(
            self.TEXT, self.TERM, self.START, self.LENGTH, 20, cfg
        )
        assert "EVENT" not in result
        assert "headache" in result

    def test_method_14_prepend_source(self):
        cfg = get_method_config(14)
        result = generate_example(
            self.TEXT, self.TERM, self.START, self.LENGTH, 20, cfg, source="exact"
        )
        assert "headache exact" in result or "headache exact" in result
        assert "EVENT" in result

    def test_method_5_random(self):
        cfg = get_method_config(5)
        random.seed(42)
        result = generate_example(
            self.TEXT, self.TERM, self.START, self.LENGTH, 5, cfg
        )
        words = result.split()
        assert len(words) == 5
        assert all(w in self.TEXT.split() for w in words)

    def test_nwords_3_special_case(self):
        cfg = get_method_config(0)
        result = generate_example(
            self.TEXT, self.TERM, self.START, self.LENGTH, 3, cfg
        )
        assert result == "headache"

    def test_method_7_after_only(self):
        cfg = get_method_config(7)
        result = generate_example(
            self.TEXT, self.TERM, self.START, self.LENGTH, 20, cfg
        )
        before_words = self.TEXT[:self.START].split()
        for w in before_words:
            if w != "headache":
                assert w not in result.split()[:3]

    def test_method_4_nonsense(self):
        cfg = get_method_config(4)
        result = generate_example(
            self.TEXT, self.TERM, self.START, self.LENGTH, 20, cfg
        )
        assert "YIHFKEHDK" in result
        assert "EVENT" not in result


# ---------------------------------------------------------------------------
# find_terms_in_text
# ---------------------------------------------------------------------------

def _make_vocab(terms: dict[str, str]) -> MedDRAVocab:
    """Create a minimal MedDRAVocab from {code: term} dict."""
    automaton = Automaton()
    code_to_term = {}
    for code, term in terms.items():
        term_lower = term.lower()
        code_to_term[code] = term
        automaton.add_word(term_lower, (code, term_lower))
    automaton.make_automaton()
    return MedDRAVocab(
        automaton=automaton,
        code_to_term=code_to_term,
        llt_to_pt={code: (code, term) for code, term in terms.items()},
    )


class TestFindTermsInText:
    def test_finds_exact_matches(self):
        vocab = _make_vocab({"100": "headache", "200": "nausea"})
        text = "the patient had headache and nausea"
        found = find_terms_in_text(text, vocab)
        found_terms = {f.term for f in found}
        assert "headache" in found_terms
        assert "nausea" in found_terms

    def test_no_match(self):
        vocab = _make_vocab({"100": "headache"})
        found = find_terms_in_text("the patient felt fine", vocab)
        assert len(found) == 0

    def test_multiple_occurrences(self):
        vocab = _make_vocab({"100": "pain"})
        text = "pain in the chest and pain in the back"
        found = find_terms_in_text(text, vocab)
        assert len(found) == 2
        assert found[0].start != found[1].start

    def test_start_position_correct(self):
        vocab = _make_vocab({"100": "nausea"})
        text = "the patient had nausea"
        found = find_terms_in_text(text, vocab)
        assert len(found) == 1
        assert text[found[0].start:found[0].start + found[0].length] == "nausea"


# ---------------------------------------------------------------------------
# load_annotations
# ---------------------------------------------------------------------------

class TestLoadAnnotations:
    def _write_annotations(self, tmp_path):
        train = [
            {
                "label_id": "DRUGX",
                "section_name": "adverse reactions",
                "section_text": "patients experienced headache and nausea",
                "adverse_events": [
                    ["headache", "Headache", 10019211.0, "Headache", 10019211.0, "23", "8"],
                ],
            },
            {
                "label_id": "DRUGX",
                "section_name": "boxed warnings",
                "section_text": "serious cardiac events",
                "adverse_events": [],
            },
        ]
        test = [
            {
                "label_id": "DRUGY",
                "section_name": "adverse reactions",
                "section_text": "mild dizziness observed",
                "adverse_events": [
                    ["dizziness", "Dizziness", 10013573.0, "Dizziness", 10013573.0, "5", "9"],
                ],
            },
        ]

        train_path = tmp_path / "demner-fushman-train-labels.json"
        test_path = tmp_path / "demner-fushman-test-labels.json"
        with open(train_path, "w") as f:
            json.dump(train, f)
        with open(test_path, "w") as f:
            json.dump(test, f)
        return tmp_path

    def test_load_ar_only(self, tmp_path):
        annot_dir = self._write_annotations(tmp_path)
        records = load_annotations(["AR"], annot_dir)
        assert len(records) == 2
        assert all(r.section_code == "AR" for r in records)

    def test_load_all_sections(self, tmp_path):
        annot_dir = self._write_annotations(tmp_path)
        records = load_annotations(["AR", "BW"], annot_dir)
        assert len(records) == 3

    def test_tac_label_correct(self, tmp_path):
        annot_dir = self._write_annotations(tmp_path)
        records = load_annotations(["AR"], annot_dir)
        tac_map = {r.drug: r.tac for r in records}
        assert tac_map["DRUGX"] == "train"
        assert tac_map["DRUGY"] == "test"

    def test_annotated_codes(self, tmp_path):
        annot_dir = self._write_annotations(tmp_path)
        records = load_annotations(["AR"], annot_dir)
        drugx = [r for r in records if r.drug == "DRUGX"][0]
        assert "10019211" in drugx.annotated_codes

    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_annotations(["AR"], tmp_path)


# ---------------------------------------------------------------------------
# construct_reference_set
# ---------------------------------------------------------------------------

class TestConstructReferenceSet:
    def test_basic_construction(self):
        vocab = _make_vocab({
            "10019211": "headache",
            "10028813": "nausea",
            "10037660": "rash",
        })
        records = [
            AnnotationRecord(
                drug="DRUGX",
                section_code="AR",
                text="patients experienced headache and nausea and rash",
                annotated_codes={"10019211", "10028813"},
                tac="train",
            ),
        ]

        rows = construct_reference_set(records, vocab, method=0, nwords=20)
        assert len(rows) > 0

        classes = {row[6] for row in rows}
        assert "is_event" in classes
        assert "not_event" in classes

        for row in rows:
            assert row[0] == "AR"
            assert row[1] == "DRUGX"
            assert row[2] == "train"

    def test_event_classification(self):
        vocab = _make_vocab({
            "100": "headache",
            "200": "fever",
        })
        records = [
            AnnotationRecord(
                drug="DRUGX",
                section_code="AR",
                text="headache and fever reported",
                annotated_codes={"100"},
                tac="train",
            ),
        ]
        rows = construct_reference_set(records, vocab, method=0, nwords=20)

        row_by_term = {row[8]: row for row in rows}
        assert row_by_term["headache"][6] == "is_event"
        assert row_by_term["fever"][6] == "not_event"


# ---------------------------------------------------------------------------
# write_reference_csv
# ---------------------------------------------------------------------------

class TestWriteReferenceCsv:
    def test_writes_header_and_rows(self, tmp_path):
        rows = [
            ["AR", "DRUGX", "train", "100", "100", "exact",
             "is_event", "Headache", "headache", "headache EVENT context"],
        ]
        path = tmp_path / "ref.txt"
        write_reference_csv(path, rows)

        lines = path.read_text().strip().split("\n")
        assert len(lines) == 2
        assert lines[0].startswith("section,")

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "deep" / "nested" / "ref.txt"
        write_reference_csv(path, [])
        assert path.exists()


# ---------------------------------------------------------------------------
# _resolve_sections
# ---------------------------------------------------------------------------

class TestResolveSections:
    def test_single(self):
        assert _resolve_sections("AR") == ["AR"]
        assert _resolve_sections("BW") == ["BW"]

    def test_all(self):
        assert _resolve_sections("ALL") == ["AR", "BW", "WP"]

    def test_arbw(self):
        assert _resolve_sections("ARBW") == ["AR", "BW"]

    def test_unknown_raises(self):
        with pytest.raises(ValueError):
            _resolve_sections("XX")
