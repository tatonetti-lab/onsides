import argparse
import logging
import pathlib
import time

import pandas as pd
import tqdm.auto as tqdm
import wget

logger = logging.getLogger(__name__)


def download_medicines_table(data_folder: pathlib.Path) -> None:
    output_path = data_folder.joinpath("medicines-output-medicines-report_en.xlsx")
    if output_path.exists():
        logger.info(f"File already exists, skipping download: {output_path}")
        return None

    # The original link is broken.
    # https://www.ema.europa.eu/sites/default/files/Medicines_output_european_public_assessment_reports.xlsx
    # I believe that below is an updated link, or at least an equivalent table.
    url = "https://www.ema.europa.eu/en/documents/report/medicines-output-medicines-report_en.xlsx"
    wget.download(url, out=output_path.as_posix())


def download(url_id: str, output_path: pathlib.Path) -> bool:
    url = f"https://www.ema.europa.eu/en/documents/product-information/{url_id}-epar-product-information_en.pdf"
    time.sleep(5)
    try:
        wget.download(url, out=output_path.as_posix())
        return True
    except KeyboardInterrupt as e:
        raise e
    except Exception as e:
        print(f"Failed to download {url_id}. {e}")
    return False


def try_download(raw_url: str, output_path: pathlib.Path) -> bool:
    url = raw_url.split("/")[-1]
    return download(url, output_path)


def retry_download(med: str, output_path: pathlib.Path) -> bool:
    med_alt = med.replace(" ", "-").lower()
    if "known as" in med or "previously" in med:
        med_alt = med_alt.split(" (")[0]
    else:
        med_alt = med_alt.replace("(", "").replace(")", "")

    return download(med_alt, output_path)


def download_all(data_folder: pathlib.Path) -> None:
    raw_folder = data_folder.joinpath("raw")
    raw_folder.mkdir(exist_ok=True)

    drug_info = (
        pd.read_excel(
            data_folder.joinpath("medicines-output-medicines-report_en.xlsx"),
            skiprows=8,
        )
        .query("Category == 'Human'")
        .drop(columns=["Category"])
        .rename(columns={"Name of medicine": "drug_name", "Medicine URL": "url"})
        .assign(
            drug_name=lambda df: df["drug_name"].str.replace(" ", "-").str.lower(),
            path=lambda df: df["drug_name"].apply(
                lambda x: raw_folder.joinpath(f"{x}_label.pdf")
            ),
        )
        .to_dict(orient="records")
    )

    logger.info(f"Found {len(drug_info)} drugs of interest.")
    drug_info = [d for d in drug_info if not d["path"].exists()]
    n_drugs = len(drug_info)
    logger.info(f"Will download the raw files of {n_drugs} drugs.")

    # download the raw files
    n_downloaded = 0
    n_not_found = 0
    n_not_found_2 = 0
    for row in tqdm.tqdm(drug_info):
        med = row["drug_name"]
        raw_url = row["url"]
        output_path = row["path"]

        first_try = try_download(raw_url, output_path)
        if first_try:
            n_downloaded += 1
        else:
            n_not_found += 1
            second_try = retry_download(med, output_path)
            if second_try:
                n_downloaded += 1
            else:
                n_not_found_2 += 1

    logger.info(
        f"found : {n_drugs}, downloaded : {n_downloaded}, failed : {n_not_found_2}"
    )


def main():
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(
        description="download drug labels from EU EMA website"
    )
    parser.add_argument(
        "--data_folder",
        type=pathlib.Path,
        required=True,
        help="Path to the data folder.",
    )
    args = parser.parse_args()
    args.data_folder.mkdir(exist_ok=True, parents=True)
    download_medicines_table(args.data_folder)
    download_all(args.data_folder)


if __name__ == "__main__":
    main()
