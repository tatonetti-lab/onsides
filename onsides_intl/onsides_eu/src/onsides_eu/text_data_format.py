"""Find MedDRA term exact matches in drug label free text. Setup data for the
OnSIDES model.

There are a couple things that I did here which should be clarified.

First, I don't do any RxNorm mapping here. I saw that previous code attempted to
do this, but it was trying to join drug names from EMA to RxNorm SET IDs, which
look like UUIDs. Text joins didn't work, so I just explicitly set those columns
to None below, just to ensure we have all the same columns as the original code.

Second, I'm not sure about the "AR" section. That's what the previous code did,
so I just did it here too.

Third, I used the same MedDRA terms as previous code (I think). Not sure why
we're only using 5 character or longer terms. My code looks for either PT or LLT
and maps to PT terms.
"""

import argparse
import logging
import pathlib
import re

import polars as pl
import tqdm.auto as tqdm

logger = logging.getLogger(__name__)


def build_bert_strings(
    ade_text: str,
    meddra_name: str,
    nwords: int = 125,
    prop_before: float = 0.125,
) -> list[tuple[str, int]]:
    if meddra_name not in ade_text:
        raise ValueError(f"MedDRA name {meddra_name} not found in ade_text")

    term_nwords = len(meddra_name.split())
    n_words_before = prop_before * (nwords - 2 * term_nwords)
    n_words_after = (1 - prop_before) * (nwords - 2 * term_nwords)
    n_words_before = max(int(n_words_before), 1)
    n_words_after = max(int(n_words_after), 1)

    results = list()
    matches = re.finditer(meddra_name, ade_text)
    for match in matches:
        start_pos = match.start()
        end_pos = match.end()
        before_words = ade_text[:start_pos].split()[-n_words_before:]
        after_words = ade_text[end_pos:].split()[:n_words_after]
        words_list = [meddra_name] + before_words + ["EVENT"] + after_words
        result = " ".join(words_list)
        results.append((result, start_pos))
    return results


def format_text(
    data_folder: pathlib.Path,
    external_data_folder: pathlib.Path,
) -> None:
    drug_to_ade_text = (
        pl.read_csv(data_folder / "ade_text_table.csv")
        .with_columns(pl.col("ade_text").str.to_lowercase())
        .select("drug", "ade_text")
        .to_dicts()
    )
    meddra_terms = (
        pl.read_csv(external_data_folder / "umls_meddra_en.csv")
        .with_columns(pl.col("STR").str.to_lowercase())
        .filter(pl.col("TTY").is_in({"PT", "LLT"}))
        .with_columns(
            pl.when(pl.col("TTY").eq("PT"))
            .then(pl.col("STR"))
            .otherwise(None)
            .max()
            .over("SDUI")
            .alias("pt_meddra_term"),
            pl.col("SDUI").alias("pt_meddra_id"),
        )
        .select(
            "pt_meddra_term",
            "pt_meddra_id",
            pl.col("CODE").alias("other_meddra_id"),
            pl.col("STR").alias("other_meddra_term"),
        )
        .filter(pl.col("other_meddra_term").str.len_chars().ge(5))
        .to_dicts()
    )
    logger.info(
        f"Found {len(drug_to_ade_text)} drugs. "
        f"Searching for exact matches of {len(meddra_terms)} MedDRA terms."
    )
    exact_terms = list()
    for drug_term in tqdm.tqdm(drug_to_ade_text):
        for meddra_term in meddra_terms:
            meddra_name = meddra_term["other_meddra_term"]
            ade_text = drug_term["ade_text"]
            if meddra_name not in ade_text:
                continue

            bert_strings = build_bert_strings(ade_text, meddra_name)
            for bert_string, start_pos in bert_strings:
                row = {
                    "label_id": drug_term["drug"],
                    "found_term": meddra_name,
                    "meddra_id": meddra_term["other_meddra_id"],
                    "location": start_pos,
                    "string": bert_string,
                    "section": "AR",
                    "set_id": drug_term["drug"],
                    "drug": None,
                    "spl_version": None,
                    "pt_meddra_id": meddra_term["pt_meddra_id"],
                    "pt_meddra_term": meddra_term["pt_meddra_term"],
                }
                exact_terms.append(row)

    logger.info(f"Found {len(exact_terms)} exact matches.")
    pl.DataFrame(exact_terms).write_csv(data_folder / "bert_input.csv")


def main():
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data_folder",
        type=pathlib.Path,
        required=True,
        help="Path to the data folder.",
    )
    parser.add_argument(
        "--external_data",
        type=pathlib.Path,
        required=True,
        help="Path to the external data folder.",
    )
    args = parser.parse_args()
    format_text(args.data_folder, args.external_data)


if __name__ == "__main__":
    main()
