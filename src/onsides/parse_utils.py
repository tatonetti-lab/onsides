import csv
import logging
import re
from pathlib import Path

import pandas as pd
import polars as pl
import tabula
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)


def pull_tables_from_pdf(input_file, output_file, output_folder) -> None:
    """Read all tables from a PDF file, writing each table to a csv file in
    the output directory, and writing the number of tables written to the
    output file."""
    input_file = Path(input_file)
    output_file = Path(output_file)
    output_folder = Path(output_folder)

    output_folder.mkdir(exist_ok=True, parents=True)

    try:
        tables = tabula.read_pdf(input_file, pages="all", silent=True)  # type: ignore
        name = input_file.stem
        for i, table in enumerate(tables):
            assert isinstance(table, pd.DataFrame)
            table.to_csv(output_folder / f"{name}.table.{i}.csv", index=False)
    except Exception as e:
        logger.error(f"Failed to read {input_file}. {e}")
        tables = []

    with open(output_file, "w") as f:
        f.write(str(len(tables)))


def pull_tables_from_html(input_file, output_file, output_folder) -> None:
    """Read all tables from an input HTML file. Write the output file to be
    just the number of tables found. Write all other tables as separate files
    like {input_file.stem}.table.{i}.csv for i in 0, 1, ..., number of tables - 1.
    """
    input_file = Path(input_file)
    output_file = Path(output_file)
    output_folder = Path(output_folder)
    output_folder.mkdir(exist_ok=True, parents=True)

    with open(input_file, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    tables = soup.find_all("table")
    n_written = 0
    for i, table in enumerate(tables):
        assert isinstance(table, Tag)
        table_data = list()
        for row in table.find_all("tr"):
            assert isinstance(row, Tag)
            row_data = list()
            for cell in row.find_all(["td", "th"]):
                cell_text = cell.get_text().replace("\n", " ")
                cell_text = re.sub(r"\s+", " ", cell_text).strip()
                row_data.append(cell_text)

            if len(row_data) > 0:
                table_data.append(row_data)

        if len(table_data) == 0:
            continue

        max_n_cols = max(len(row) for row in table_data)
        table_filename = output_folder / f"{input_file.stem}.table.{i}.csv"
        with open(table_filename, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            for row in table_data:
                # Pad rows with empty strings if they don't have enough columns
                padded_row = row + [""] * (max_n_cols - len(row))
                writer.writerow(padded_row)

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(str(n_written))

    return


def pull_undesirable_effects(input_file, output_file) -> None:
    """Extract the 'Undesirable Effects' section of a drug label. Applicable
    to labels from the UK and EU only.
    """
    input_file = Path(input_file)
    output_file = Path(output_file)

    with open(input_file, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    details = soup.find_all("details")
    for detail in details:
        assert isinstance(detail, Tag)
        summary = detail.find("summary")
        assert isinstance(summary, Tag)
        if (name := summary.get("id")) is not None and name == "UNDESIRABLE_EFFECTS":
            ade_section = detail.find("div", {"class": "sectionWrapper"})
            assert ade_section is not None
            assert isinstance(ade_section, Tag)
            with open(output_file, "w") as f:
                f.write(str(ade_section))
                return

    logger.error(f"No ADE section in {input_file}")
    output_file.touch()


def pull_side_effects_jp(input_file, output_file) -> None:
    """Extract the side effects section from a Japan drug label, export HTML"""

    input_file = Path(input_file)
    output_file = Path(output_file)

    with open(input_file, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "html.parser")

    header = re.compile("^h[1-6]$")
    start = soup.find(header, {"class": "contents-title", "id": "par-11"})
    assert isinstance(start, Tag), start

    end = start.find_next(header, {"class": "contents-title"})
    assert isinstance(end, Tag)

    elements_between = start.find_all_next()
    elements_between = elements_between[: elements_between.index(end)]

    text = "\n".join(str(e) for e in elements_between)
    with open(output_file, "w") as f:
        f.write(text)
