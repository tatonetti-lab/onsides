import argparse
import json
import logging
import pathlib
import re

import polars as pl
import tqdm.auto as tqdm

logger = logging.getLogger(__name__)


# add in titles as reference. may use these in the future.
titles = [
    "1. NAME OF THE MEDICINAL PRODUCT",
    "2. QUALITATIVE AND QUANTITATIVE COMPOSITION",
    "3. PHARMACEUTICAL FORM",
    "4. CLINICAL PARTICULARS",
    "5. PHARMACOLOGICAL PROPERTIES",
    "6. PHARMACEUTICAL PARTICULARS",
    "7. MARKETING AUTHORISATION HOLDER",
    "8. MARKETING AUTHORISATION NUMBER",
    "9. DATE OF FIRST AUTHORISATION/RENEWAL OF THE AUTHORISATION",
    "10. DATE OF REVISION OF THE TEXT",
]

sec4_titles = [
    "4.1 Therapeutic indications",
    "4.2 Posology and method of administration",
    "4.3 Contraindications",
    "4.4 Special warnings and precautions for use",
    "4.5 Interaction with other medicinal products and other forms of interaction",
    "4.6 Fertility, pregnancy and lactation",
    "4.7 Effects on ability to drive and use machines",
    "4.8 Undesirable effects",
    "4.9 Overdose",
]


def extract_clinical_particulars(
    raw_txt_file: pathlib.Path, output_dir: pathlib.Path
) -> pathlib.Path | None:
    """Extract the '4. CLINICAL PARTICULARS' section of a txt drug label and
    save it to a JSON file"""

    with open(raw_txt_file) as f:
        txt = f.read()

    normed = " ".join(txt.split())

    regex = (
        r"(4\. CLINICAL|4 CLINICAL|4\. CLINCAL|4\. Clinical).+"
        r"(5\. PHARMACOLOGIC|5 PHARMACOLOGIC)"
    )
    match = re.search(regex, normed)
    if match is None:
        logger.error(f"Could not find 4. CLINICAL in {raw_txt_file}")
        return None

    section = {"4. CLINICAL PARTICULARS": match.group()}
    drug_name = raw_txt_file.stem
    output_path = output_dir.joinpath(drug_name).with_suffix(".json")
    with open(output_path, "w") as out:
        json.dump(section, out)
    return output_path


def extract_undesirable_effects(
    raw_json_file: pathlib.Path, output_dir: pathlib.Path
) -> pathlib.Path | None:
    """Extract the '4.8 Undesirable effects' section of a json drug label and
    save it to a JSON file"""

    with open(raw_json_file) as f:
        d = json.load(f)

    txt = d["4. CLINICAL PARTICULARS"]

    regex = r"(4\.8\. Undesirable|4\.8 Undesirable).+(4\.9 Overdose|4\.9\. Overdose)"
    match = re.search(regex, txt)
    if match is None:
        logger.error(f"Could not find 4.8 Undesirable in {raw_json_file}")
        return None

    section = {"Undesirable effects": match.group()}
    drug_name = raw_json_file.stem
    output_path = output_dir.joinpath(drug_name).with_suffix(".json")
    with open(output_path, "w") as out:
        json.dump(section, out)
    return output_path


def parse_all_text(data_folder: pathlib.Path) -> None:
    txt_files = list(data_folder.joinpath("raw_txt").glob("*"))
    raw_json_folder = data_folder.joinpath("raw_json")
    raw_json_folder.mkdir(exist_ok=True)

    # Extract the "clinical particulars" section
    raw_json_paths = list()
    n_failed = 0
    for txt_file in tqdm.tqdm(txt_files):
        maybe_path = extract_clinical_particulars(txt_file, raw_json_folder)
        if maybe_path is not None:
            raw_json_paths.append(maybe_path)
        else:
            n_failed += 1

    logger.info(
        f"Found clinical particulars for {len(raw_json_paths)}, {n_failed} failures"
    )

    # Extract the "undesirable effects" subsection from the "clinical particulars"
    # section extracted above
    raw_json_ue_folder = data_folder.joinpath("raw_json_ue")
    raw_json_ue_folder.mkdir(exist_ok=True)

    undesired_effect_paths = list()
    n_failed = 0
    for json_file in tqdm.tqdm(raw_json_paths):
        maybe_path = extract_undesirable_effects(json_file, raw_json_ue_folder)
        if maybe_path is not None:
            undesired_effect_paths.append(maybe_path)
        else:
            n_failed += 1

    logger.info(
        f"Found undesired effects for {len(undesired_effect_paths)}, "
        f"{n_failed} failures"
    )

    # Format the undesirable effects into a table to use.
    ade_table = list()
    for json_file in tqdm.tqdm(undesired_effect_paths):
        with open(json_file) as f:
            d = json.load(f)

        txt = d["Undesirable effects"]
        clean_ade = re.sub(r"[^\n\w\s.,]", "", txt)
        drug = json_file.stem
        row = {
            "drug": drug,
            "ade_text": clean_ade,
        }
        ade_table.append(row)

    output_file = data_folder / "ade_text_table.csv"
    pl.DataFrame(ade_table).write_csv(output_file)
    logger.info("finish extracting text data.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--data_folder",
        type=pathlib.Path,
        required=True,
        help="Path to the data folder.",
    )
    args = parser.parse_args()
    parse_all_text(args.data_folder)


if __name__ == "__main__":
    main()
