from enum import Enum
from typing import Any

import httpx
from pydantic import BaseModel
from ratelimit import limits, sleep_and_retry

type DrugTerms = list[str]
type RxCui = str


class MatchType(str, Enum):
    exact = "exact"
    normalized = "normalized"
    approximate = "approximate"


class RxCuiMatch(BaseModel):
    rxcui: RxCui
    match_type: MatchType


def match_terms_to_rxcui(
    terms: DrugTerms,
    match_vocabulary: dict[str, RxCui] | None = None,
    base_url: str = "https://rxnav.nlm.nih.gov",
) -> RxCuiMatch | None:
    """Match a set of terms corresponding to a single drug concept to the best
    matching RxCUI. Terms should be ranked in decreasing order of preference
    (e.g. ["BrandName", "simple brand name", "generic name"]).
    """
    if match_vocabulary is None:
        match_vocabulary = dict()
    else:
        match_vocabulary = {k.lower(): v for k, v in match_vocabulary.items()}

    # Try exact matches first
    for term in terms:
        if (match := match_vocabulary.get(term.lower())) is not None:
            return RxCuiMatch(rxcui=match, match_type=MatchType.exact)

    # No exact matches, proceed with normalized match via RxNav
    for term in terms:
        if (match := normalized_match(term, base_url)) is not None:
            return RxCuiMatch(rxcui=match, match_type=MatchType.normalized)

    # No normalized matches, proceed with approximate match via RxNav
    for term in terms:
        if (match := approximate_match(term, base_url)) is not None:
            return RxCuiMatch(rxcui=match, match_type=MatchType.approximate)

    # Couldn't match via any method
    return None


def normalized_match(
    term: str, base_url: str = "https://rxnav.nlm.nih.gov"
) -> str | None:
    response = call_rxnav(
        f"{base_url}/REST/rxcui.json", params={"name": term, "search": 2}
    )
    response.raise_for_status()  # type: ignore
    content = response.json()  # type: ignore
    results = content["idGroup"].get("rxnormId")
    if results is None or len(results) == 0:
        return None
    else:
        return results[0]


def approximate_match(
    term: str, base_url: str = "https://rxnav.nlm.nih.gov"
) -> str | None:
    response = call_rxnav(
        f"{base_url}/REST/approximateTerm.json",
        params={"term": term, "maxEntries": 1},
    )
    response.raise_for_status()  # type: ignore
    content = response.json()  # type: ignore
    results = content["approximateGroup"].get("candidate")
    if results is None or len(results) == 0:
        return None
    else:
        return results[0]["rxcui"]


@sleep_and_retry
@limits(calls=20, period=1)
def call_rxnav(url: str, params: dict[str, Any]) -> httpx.Response:
    return httpx.get(url, params=params)
