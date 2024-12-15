import argparse
import logging
import pathlib
import shlex
import shutil
import subprocess

import pandas as pd
import PyPDF2
import tabula
import tqdm.auto as tqdm

logger = logging.getLogger(__name__)


def parse_all_files(data_folder: pathlib.Path) -> None:
    pdfs = list(data_folder.joinpath("raw").glob("*_label.pdf"))
    print(f"We have downloaded {len(pdfs)} PDF drug label files.")

    pdftotext = shutil.which("pdftotext")
    if pdftotext is None:
        logger.warning(
            "pdftotext was not found. A slower python implementation will be used."
        )

    raw_txt_folder = data_folder.joinpath("raw_txt")
    raw_txt_folder.mkdir(exist_ok=True)
    raw_tbl_folder = data_folder.joinpath("raw_tbl")
    raw_tbl_folder.mkdir(exist_ok=True)

    for pdf in tqdm.tqdm(pdfs):
        pull_text_from_pdf(pdf, raw_txt_folder)
        pull_tables_from_pdf(pdf, raw_tbl_folder)


def pull_text_from_pdf(input_file: pathlib.Path, output_folder: pathlib.Path) -> None:
    if not input_file.name.endswith("_label.pdf"):
        raise ValueError(
            f"Input path {input_file.as_posix()} doesn't have the expected ending."
        )
    if not output_folder.exists():
        raise NotADirectoryError(
            f"Output folder {output_folder.as_posix()} is not a directory"
        )
    drug_name = input_file.stem.removesuffix("_label")
    output_file = output_folder.joinpath(drug_name).with_suffix(".txt")

    pdftotext = shutil.which("pdftotext")
    if pdftotext is not None:
        _pull_text_pdftotext(input_file, output_file)
    else:
        _pull_text_python(input_file, output_file)


def _pull_text_pdftotext(input_file: pathlib.Path, output_file: pathlib.Path) -> None:
    command = (
        f"pdftotext -nopgbrk -raw {input_file.as_posix()} {output_file.as_posix()}"
    )
    subprocess.run(shlex.split(command), check=True)


def _pull_text_python(input_file: pathlib.Path, output_file: pathlib.Path) -> None:
    with open(input_file, "rb") as pdf_file:
        read_pdf = PyPDF2.PdfReader(pdf_file)
        n_pages = len(read_pdf.pages)
        p_text = ""
        for n in range(n_pages):
            page = read_pdf.pages[n]
            page_content = page.extract_text()
            p_text += page_content

    with open(output_file, "w+") as f:
        f.write(p_text)


def pull_tables_from_pdf(input_file: pathlib.Path, output_folder: pathlib.Path) -> None:
    if not input_file.name.endswith("_label.pdf"):
        raise ValueError(
            f"Input path {input_file.as_posix()} doesn't have the expected ending."
        )
    if not output_folder.exists():
        raise NotADirectoryError(
            f"Output folder {output_folder.as_posix()} is not a directory"
        )

    try:
        tables = tabula.read_pdf(input_file, pages="all", silent=True)  # type: ignore
    except Exception as e:
        logger.error(f"Failed to read {input_file.as_posix()}. {e}")
        return

    drug_name = input_file.stem.removesuffix("_label")
    for i, table in enumerate(tables):
        assert isinstance(table, pd.DataFrame)
        table.to_csv(output_folder / f"{drug_name}_{i}.csv", index=False)


def main():
    parser = argparse.ArgumentParser(description="download drug labels from EU website")
    parser.add_argument(
        "--data_folder",
        type=pathlib.Path,
        required=True,
        help="Path to the data folder.",
    )
    args = parser.parse_args()
    parse_all_files(args.data_folder)


if __name__ == "__main__":
    main()
