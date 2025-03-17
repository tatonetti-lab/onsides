import pytest

from onsides.stringsearch import (
    ContextSettings,
    MatchContext,
    _build_bert_string,
    _build_search_tree,
    _find_terms_in_text,
    _FoundTerm,
    parse_texts,
)
from onsides.types import IndexedText


@pytest.fixture
def search_terms():
    return [
        IndexedText(text="foo", text_id=1),
        IndexedText(text="bar", text_id=2),
        IndexedText(text="baz", text_id=3),
        IndexedText(text="zab", text_id=4),
    ]


@pytest.fixture
def search_tree(search_terms):
    return _build_search_tree(search_terms)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("baz", [_FoundTerm(term_id=3, term="baz", start=0, end=2)]),
        (
            "bar baz",
            [
                _FoundTerm(term_id=2, term="bar", start=0, end=2),
                _FoundTerm(term_id=3, term="baz", start=4, end=6),
            ],
        ),
        (
            "foo baz",
            [
                _FoundTerm(term_id=1, term="foo", start=0, end=2),
                _FoundTerm(term_id=3, term="baz", start=4, end=6),
            ],
        ),
        (
            "foo bar",
            [
                _FoundTerm(term_id=1, term="foo", start=0, end=2),
                _FoundTerm(term_id=2, term="bar", start=4, end=6),
            ],
        ),
        (
            "foo bar baz",
            [
                _FoundTerm(term_id=1, term="foo", start=0, end=2),
                _FoundTerm(term_id=2, term="bar", start=4, end=6),
                _FoundTerm(term_id=3, term="baz", start=8, end=10),
            ],
        ),
        (
            # Terms overlap (share characters)
            "foobazab",
            [
                _FoundTerm(term_id=1, term="foo", start=0, end=2),
                _FoundTerm(term_id=3, term="baz", start=3, end=5),
                _FoundTerm(term_id=4, term="zab", start=5, end=7),
            ],
        ),
    ],
)
def test_find_terms(search_tree, text: str, expected: list[int]):
    assert _find_terms_in_text(text, search_tree) == expected


@pytest.mark.parametrize(
    "text,match,n_words,prop_before,expected",
    [
        (
            # Basic example
            "foo bar baz",
            _FoundTerm(term_id=1, term="bar", start=4, end=6),
            1,
            0.5,
            "bar foo EVENT baz",
        ),
        (
            # Ignore prop_before if there are no words before the match
            "foo bar baz",
            _FoundTerm(term_id=1, term="bar", start=4, end=6),
            1,
            0.15,
            "bar foo EVENT baz",
        ),
        (
            # Behave correctly if match is at the end of the text
            "foo bar baz",
            _FoundTerm(term_id=2, term="baz", start=8, end=10),
            1,
            0.5,
            "baz bar EVENT",
        ),
        (
            # Correctly extract multiple words
            "a b bar c d",
            _FoundTerm(term_id=2, term="bar", start=4, end=6),
            6,
            0.5,
            "bar a b EVENT c d",
        ),
        (
            # Correctly limit the total number of words
            "a b c bar d e f",
            _FoundTerm(term_id=2, term="bar", start=6, end=8),
            6,
            0.5,
            "bar b c EVENT d e",
        ),
        (
            # Correctly limit the total number of words
            "a b c bar d e f",
            _FoundTerm(term_id=2, term="bar", start=6, end=8),
            6,
            0.5,
            "bar b c EVENT d e",
        ),
        (
            # Respect the prop_before parameter
            "a b c bar d e f",
            _FoundTerm(term_id=2, term="bar", start=6, end=8),
            6,
            0.75,
            "bar a b c EVENT d",
        ),
    ],
)
def test_build_bert_string(
    text: str, match: _FoundTerm, n_words: int, prop_before: float, expected: str
):
    result = _build_bert_string(text, match, n_words, prop_before)
    assert result == expected


def test_parse_texts(
    search_terms,
):
    texts = [
        IndexedText(text_id=1, text="qux mux lux foo abc def ghi"),
        IndexedText(text_id=2, text="qux mux lux foobarbaz abc def ghi"),
    ]
    settings = ContextSettings(nwords=1, prop_before=0.5)
    results = parse_texts(texts, search_terms, settings, progress=False)
    expected = [
        MatchContext(
            match_id=0,
            text_id=1,
            term_id=1,
            term="foo",
            context="foo lux EVENT abc",
        ),
        # Handle match inside a word (at the start)
        MatchContext(
            match_id=1,
            text_id=2,
            term_id=1,
            term="foo",
            context="foo lux EVENT barbaz",
        ),
        # Handle match inside a word (in the middle)
        MatchContext(
            match_id=2,
            text_id=2,
            term_id=2,
            term="bar",
            context="bar foo EVENT baz",
        ),
        # Handle match inside a word (at the end)
        MatchContext(
            match_id=3,
            text_id=2,
            term_id=3,
            term="baz",
            context="baz foobar EVENT abc",
        ),
    ]
    assert results == expected
