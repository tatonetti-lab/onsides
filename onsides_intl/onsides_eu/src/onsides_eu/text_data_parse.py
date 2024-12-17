import argparse
import logging
import pathlib
import re

import polars as pl
import tqdm.auto as tqdm
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class LabelSections(BaseModel):
    drug: str
    clinical_particulars: str
    undesirable_effects: str
    ade_text: str


def extract_undesirable_effects(
    raw_txt_file: pathlib.Path, output_dir: pathlib.Path
) -> LabelSections | None:
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
    clinical_particulars = match.group()

    regex = r"(4\.8\. Undesirable|4\.8 Undesirable).+(4\.9 Overdose|4\.9\. Overdose)"
    match = re.search(regex, clinical_particulars)
    if match is None:
        logger.error(f"Could not find 4.8 Undesirable in {raw_txt_file}")
        return None
    undesirable_effects = match.group()
    clean_ade = re.sub(r"[^\n\w\s.,]", "", undesirable_effects)

    drug_name = raw_txt_file.stem
    sections = LabelSections(
        drug=drug_name,
        clinical_particulars=clinical_particulars,
        undesirable_effects=undesirable_effects,
        ade_text=clean_ade,
    )
    output_path = output_dir.joinpath(drug_name).with_suffix(".json")
    with open(output_path, "w") as out:
        json_str = sections.model_dump_json(indent=2)
        out.write(json_str)
    return sections


def parse_all_text(data_folder: pathlib.Path) -> None:
    txt_files = list(data_folder.joinpath("raw_txt").glob("*"))
    json_folder = data_folder.joinpath("json")
    json_folder.mkdir(exist_ok=True)

    sections_table = list()
    n_failed = 0
    for txt_file in tqdm.tqdm(txt_files):
        maybe_sections = extract_undesirable_effects(txt_file, json_folder)
        if maybe_sections is not None:
            sections_table.append(maybe_sections)
        else:
            n_failed += 1

    logger.info(f"Extracted data for {len(sections_table)}, {n_failed} failures")

    output_file = data_folder / "ade_text_table.csv"
    pl.DataFrame(sections_table).select("drug", "ade_text").write_csv(output_file)
    logger.info("finish extracting text data")


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
