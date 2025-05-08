import argparse
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True, type=str)
    args = parser.parse_args()

    zip_name = f"onsides-{args.version}.zip"
    make_db_bundle(zip_name)


def make_db_bundle(zip_path: str | Path) -> None:
    """
    Create a ZIP archive containing the four sub-folders inside the project’s
    `database/` directory—`annotations`, `csv`, `database_scripts`, and `schema`.

    The resulting ZIP has those folders at its root (as if you had first
    `cd database` and then run `zip -r … annotations csv …`).

    Parameters
    ----------
    zip_path : str | Path
        Destination file name, e.g. "../onsides-v3.0.0.zip".
    """
    root = Path.cwd() / "database"  # project_root/database
    subdirs = ["annotations", "csv", "database_scripts", "schema"]

    with ZipFile(zip_path, mode="w", compression=ZIP_DEFLATED) as zf:
        for sub in subdirs:
            for path in (root / sub).rglob("*"):
                if path.is_file():  # skip dir entries
                    # store the file relative to `database/` so the ZIP root
                    # matches a `cd database` context
                    print(f"Writing {path.relative_to(root)}")
                    zf.write(path, arcname=path.relative_to(root))
