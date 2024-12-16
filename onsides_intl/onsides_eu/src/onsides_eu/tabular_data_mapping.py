"""Find all ADEs listed in the ADEs table.

There are basically 2 steps to this script:
    1. read each table file to see if it could be an ADE table, discard if not
    2. read each ADE table and export all words that match a MedDRA term
"""

import argparse
import logging
import pathlib

import pandas as pd
import polars as pl
import tqdm.auto as tqdm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

freqs = ["very common", "common", "uncommon", "rare", "very rare", "not known"]
socs = [
    "blood and lymphatic system disorders",
    "cardiac disorders",
    "congenital, familial and genetic disorders",
    "ear and labyrinth disorders",
    "endocrine disorders",
    "eye disorders",
    "gastrointestinal disorders",
    "general disorders and administration site conditions",
    "hepatobiliary disorders",
    "immune system disorders",
    "infections and infestations",
    "injury, poisoning and procedural complications",
    "investigations",
    "metabolism and nutrition disorders",
    "musculoskeletal and connective tissue disorders",
    "neoplasms benign, malignant and unspecified (incl cysts and polyps)",
    "nervous system disorders",
    "pregnancy, puerperium and perinatal conditions",
    "psychiatric disorders",
    "renal and urinary disorders",
    "reproductive system and breast disorders",
    "respiratory, thoracic and mediastinal disorders",
    "skin and subcutaneous tissue disorders",
    "social circumstances",
    "surgical and medical procedures",
    "vascular disorders",
    "product issues",
]
titles = ["system organ class", "frequency", "adverse events"]


def map_tabular(data_folder: pathlib.Path, external_data_folder: pathlib.Path):
    # Load (drug, ade_text) pairs
    output_path = data_folder / "raw_ade_table.csv"
    if output_path.exists():
        logger.info(f"File already exists, skipping: {output_path}")
        ade_rows = pl.read_csv(output_path).to_dicts()
    else:
        logger.info(f"Extracting raw ADE table from tabular files: {output_path}")
        ade_rows = extract_raw_ade_table(data_folder)

    # Load MedDRA terms for reference
    meddra_df = pl.read_csv(external_data_folder / "umls_meddra_en.csv").with_columns(
        pl.col("STR").str.to_lowercase(),
        pl.col("STR").str.len_chars().alias("len"),
    )
    meddra_name_to_code = meddra_df.to_pandas().set_index("STR")["SDUI"].to_dict()
    meddra_names = meddra_df.filter(pl.col("TTY").eq("PT") | pl.col("len").gt(5))[
        "STR"
    ].to_list()

    logger.info("Updating ADE table with MedDRA terms")
    updated_rows = list()
    for row in tqdm.tqdm(ade_rows):
        ade_text = row["txt"]
        # remove all of the freqs, socs, and titles
        for f in freqs:
            ade_text = ade_text.replace(f, "")
        for s in socs:
            ade_text = ade_text.replace(s, "")
        for t in titles:
            ade_text = ade_text.replace(t, "")

        for meddra_name in meddra_names:
            if meddra_name in ade_text:
                code = meddra_name_to_code[meddra_name]
                new_row = {
                    "drug": row["drug"],
                    "exact_match_list": meddra_name,
                    "matched_codes": code,
                }
                updated_rows.append(new_row)

    pl.DataFrame(updated_rows).write_csv(data_folder / "parsed_ade_tabular.csv")


def extract_raw_ade_table(data_folder: pathlib.Path) -> list[dict[str, str]]:
    tbl_files = list(data_folder.joinpath("raw_tbl").glob("*.csv"))

    ade_table_words = [
        "system",
        "very common",
        "common",
        "not known",
        "rare",
        "uncommon",
    ]
    ade_table_rows = list()
    for tbl_file in tqdm.tqdm(tbl_files):
        df = pd.read_csv(tbl_file)

        # Check if the dataframe contains any of the words that indicate it
        # might be an ADE table.
        first_line = " ".join(df.columns.tolist())
        word_match = [word for word in ade_table_words if word in first_line]
        if not any(word_match):
            continue

        # Convert the dataframe to a string in column-major order (i.e. concat
        # columns then concat rows), dropping any nan values along the way.
        table_values = df.values.flatten("F").tolist()
        table_string = " ".join(v for v in table_values if isinstance(v, str))
        table_string = table_string.replace("- ", "").replace("\r", " ").lower()

        drug_name = tbl_file.stem
        row = {"drug": drug_name, "txt": table_string}
        ade_table_rows.append(row)

    pl.DataFrame(ade_table_rows).write_csv(data_folder / "raw_ade_table.csv")
    return ade_table_rows


def main():
    parser = argparse.ArgumentParser(
        description="let the code know where the data is held"
    )
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
        help="Path to the where the external data is housed.",
    )
    args = parser.parse_args()
    map_tabular(args.data_folder, args.external_data)


if __name__ == "__main__":
    main()
