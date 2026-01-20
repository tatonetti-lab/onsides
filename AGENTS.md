# Repository Guidelines

## Project Structure & Module Organization
Source code lives in `src/onsides/` (Python package and CLI entrypoint). Data workflows and pipelines are in `snakemake/` with per-region subfolders (`us/`, `uk/`, `eu/`, `jp/`) plus `onsides/` for evaluation and export steps. Database schemas and helpers are in `database/` (see `database/schema/` and `database/database_scripts/`). Docs and assets live in `docs/`, including `docs/schema.png`. Analysis notebooks live in `analyses/`.

## Build, Test, and Development Commands
- `nix develop` sets up the full environment using Nix (preferred).
- `uv sync` creates the Python environment without Nix (see `pyproject.toml` for deps).
- `snakemake -s snakemake/us/download/Snakefile --resources jobs=1` downloads US labels; similar paths exist for `uk`, `eu`, `jp`.
- `snakemake -s snakemake/onsides/evaluate/Snakefile` runs evaluation steps.
- `snakemake -s snakemake/onsides/export/Snakefile` exports final tables.
- `build-zip --version vX.Y.Z` creates a release archive.

## Coding Style & Naming Conventions
Follow PEP 8 with 4-space indentation. Use `snake_case` for functions and variables and `CapWords` for classes. Keep modules focused and named after their domain (e.g., `rxnorm.py`, `stringsearch.py`). Prefer explicit types via `pydantic` models where applicable.

## Testing Guidelines
Tests use `pytest` (dev dependency). Tests currently live alongside code in `src/onsides/` (e.g., `src/onsides/test_stringsearch.py`). Name new tests `test_*.py` and keep fixtures small and deterministic. Run tests with `pytest`.

## Commit & Pull Request Guidelines
Recent history uses short, imperative subjects and occasionally Conventional Commits (`fix:`, `chore:`). Aim for concise, scoped messages (e.g., `fix: handle EU retry`). PRs should include a clear description, linked issue (if any), and note any data or schema changes. For pipeline edits, mention which Snakefiles were validated.

## Data & Database Notes
Large datasets are distributed via GitHub Releases; avoid committing generated data. Schema references are in `database/schema/*.sql`, with test and summary helpers in `database/test.sql` and `database/summarize.sql`.
