import csv
import logging
import re
from pathlib import Path

import pandas as pd
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


# def extract_undesirable_effects(raw_label: str) -> str | None:
#     """Extract the 'Undesirable Effects' section from a drug label.
#     Applicable only to UK and EU labels, which have this sections.
#     """
#
#     normed = " ".join(raw_label.split())
#
#     regex = (
#         r"(4\. CLINICAL|4 CLINICAL|4\. CLINCAL|4\. Clinical).+"
#         r"(5\. PHARMACOLOGIC|5 PHARMACOLOGIC)"
#     )
#     match = re.search(regex, normed)
#     if match is None:
#         logger.error("Could not find 4. CLINICAL")
#         return None
#
#     clinical_particulars = match.group()
#     regex = r"(4\.8\. Undesirable|4\.8 Undesirable).+(4\.9 Overdose|4\.9\. Overdose)"
#     match = re.search(regex, clinical_particulars)
#     if match is None:
#         logger.error("Could not find 4.8 Undesirable")
#         return None
#
#     undesirable_effects = match.group()
#     clean_ade = re.sub(r"[^\n\w\s.,]", "", undesirable_effects)
#     return clean_ade


# def analyze_drug_tables(input_folder, output_file):
#     """
#     Analyze drug tables to extract adverse events information.
#     This function reimplements the logic from the original code, but in a cleaner way.
#
#     Args:
#         input_folder: Folder containing the CSV table files
#         output_file: Path to save the processed dataframe
#     """
#     # Define known categories
#     freqs = ["very common", "common", "uncommon", "rare", "very rare", "not known"]
#
#     socs = [
#         "blood and lymphatic system disorders",
#         "cardiac disorders",
#         "congenital, familial and genetic disorders",
#         "ear and labyrinth disorders",
#         "endocrine disorders",
#         "eye disorders",
#         "gastrointestinal disorders",
#         "general disorders and administration site conditions",
#         "hepatobiliary disorders",
#         "immune system disorders",
#         "infections and infestations",
#         "injury, poisoning and procedural complications",
#         "investigations",
#         "metabolism and nutrition disorders",
#         "musculoskeletal and connective tissue disorders",
#         "neoplasms benign, malignant and unspecified (incl cysts and polyps)",
#         "nervous system disorders",
#         "pregnancy, puerperium and perinatal conditions",
#         "psychiatric disorders",
#         "renal and urinary disorders",
#         "reproductive system and breast disorders",
#         "respiratory, thoracic and mediastinal disorders",
#         "skin and subcutaneous tissue disorders",
#         "social circumstances",
#         "surgical and medical procedures",
#         "vascular disorders",
#         "product issues",
#     ]
#
#     titles = ["system organ class", "frequency", "adverse events"]
#
#     processed_list = []
#     input_folder = Path(input_folder)
#
#     # Process all CSV files in the input folder
#     for csv_file in input_folder.glob("*.table.*.csv"):
#         # Extract product ID from filename
#         product_id = csv_file.stem.split(".table.")[0]
#
#         # Read CSV file
#         try:
#             df = pd.read_csv(csv_file)
#
#             # Process each row of the table
#             for _, row in df.iterrows():
#                 items = [str(item).lower().strip() for item in row if pd.notna(item)]
#
#                 # Skip header rows
#                 if any(title in " ".join(items) for title in titles):
#                     continue
#
#                 # Initialize values
#                 f, s, a = None, None, None
#
#                 # Categorize each cell
#                 for item in items:
#                     item = item.strip().replace("*", "")
#
#                     if item in freqs:
#                         f = item
#                     elif item in socs:
#                         s = item
#                     else:
#                         a = item
#
#                 # Add to processed list
#                 processed_list.append([product_id, f, s, a])
#
#         except Exception as e:
#             print(f"Error processing {csv_file}: {e}")
#
#     # Create DataFrame
#     processed_df = pd.DataFrame(
#         processed_list, columns=["product_id", "freq", "soc", "ade"]
#     )
#
#     # Further process frequency from adverse event text
#     processed_df["freq"] = processed_df.apply(
#         lambda x: str(x.ade).split(":")[0]
#         if pd.notna(x.ade) and str(x.ade).split(":")[0] in freqs
#         else x.freq,
#         axis=1,
#     )
#
#     # Save processed data
#     processed_df.to_csv(output_file, index=False)
#     print(
#         f"Finished processing of tabular data for {processed_df.product_id.nunique()} products"
#     )
