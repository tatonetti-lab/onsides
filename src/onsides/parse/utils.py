import logging
from pathlib import Path

import pandas as pd
import tabula

logger = logging.getLogger(__name__)


def pull_tables_from_pdf(input_file, output_file, output_folder) -> None:
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
