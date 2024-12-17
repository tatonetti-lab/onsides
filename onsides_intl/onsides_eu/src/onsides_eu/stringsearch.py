import ahocorasick
from pydantic import BaseModel


class MeddraSearchTerm(BaseModel):
    term: str
    meddra_pt_code: int


class FoundMeddraTerm(BaseModel):
    term: str
    meddra_pt_code: int
    start: int
    end: int


def build_meddra_search_tree(
    meddra_terms: list[MeddraSearchTerm],
) -> ahocorasick.Automaton:
    """
    Builds an Aho-Corasick tree from a list of MedDRA terms.
    """
    tree = ahocorasick.Automaton(str, str)
    for meddra_obj in meddra_terms:
        tree.add_word(meddra_obj.term, meddra_obj.model_dump_json())
    tree.make_automaton()
    return tree


def find_meddra_terms_in_text(
    text: str,
    meddra_tree: ahocorasick.Automaton,
) -> list[FoundMeddraTerm]:
    """
    Finds all MedDRA terms in a text using an Aho-Corasick tree.
    """
    found_terms = list()
    for end_index, obj_json in meddra_tree.iter(text):
        meddra_obj = MeddraSearchTerm.model_validate_json(obj_json)
        start_index = end_index - len(meddra_obj.term) + 1
        obj = FoundMeddraTerm(
            term=meddra_obj.term,
            meddra_pt_code=meddra_obj.meddra_pt_code,
            start=start_index,
            end=end_index,
        )
        found_terms.append(obj)
    return found_terms


def build_bert_string(
    text: str,
    match: FoundMeddraTerm,
    nwords: int = 125,
    prop_before: float = 0.125,
) -> str:
    term_nwords = len(match.term.split())
    n_words_before = prop_before * (nwords - 2 * term_nwords)
    n_words_after = (1 - prop_before) * (nwords - 2 * term_nwords)
    n_words_before = max(int(n_words_before), 1)
    n_words_after = max(int(n_words_after), 1)
    before_words = text[: match.start].split()[-n_words_before:]
    after_words = text[match.end :].split()[:n_words_after]
    words_list = [match.term] + before_words + ["EVENT"] + after_words
    result = " ".join(words_list)
    return result
