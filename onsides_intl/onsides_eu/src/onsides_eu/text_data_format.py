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

import polars as pl
import tqdm.auto as tqdm

from onsides_eu.stringsearch import (
    MeddraSearchTerm,
    build_bert_string,
    build_meddra_search_tree,
    find_meddra_terms_in_text,
)

logger = logging.getLogger(__name__)


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
    meddra_df = (
        pl.read_csv(external_data_folder / "umls_meddra_en.csv")
        .filter(
            pl.col("TTY").is_in({"PT", "LLT"}),
        )
        .with_columns(
            pl.col("STR").str.to_lowercase().alias("term"),
        )
        .rename({"SDUI": "meddra_pt_code"})
    )
    meddra_pt_code_to_term = (
        meddra_df.filter(pl.col("TTY").eq("PT"))
        .select("STR", "meddra_pt_code")
        .to_pandas()
        .set_index("meddra_pt_code")["STR"]
        .to_dict()
    )
    meddra_terms = (
        meddra_df.filter(pl.col("term").str.len_chars().ge(5))
        .select("term", "meddra_pt_code")
        .unique()
        .to_dicts()
    )
    meddra_terms = [MeddraSearchTerm.model_validate(t) for t in meddra_terms]
    logger.info(
        f"Found {len(drug_to_ade_text)} drugs. "
        f"Searching for exact matches of {len(meddra_terms)} MedDRA terms."
    )
    meddra_tree = build_meddra_search_tree(meddra_terms)

    exact_terms = list()
    for drug_term in tqdm.tqdm(drug_to_ade_text):
        ade_text = drug_term["ade_text"]
        matches = find_meddra_terms_in_text(ade_text, meddra_tree)
        for match in matches:
            bert_string = build_bert_string(ade_text, match)
            row = {
                "label_id": drug_term["drug"],
                "found_term": match.term,
                "location": match.start,
                "string": bert_string,
                "section": "AR",
                "set_id": drug_term["drug"],
                "drug": None,
                "spl_version": None,
                "pt_meddra_id": match.meddra_pt_code,
                "pt_meddra_term": meddra_pt_code_to_term.get(match.meddra_pt_code),
            }
            exact_terms.append(row)

    logger.info(f"Found {len(exact_terms)} exact matches.")
    pl.DataFrame(exact_terms).write_csv(data_folder / "bert_input_v2.csv")


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
