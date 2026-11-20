# CLAUDE.md

OnSIDES: a database of drug adverse events extracted from product labels
(US DailyMed, EU EMA, UK EMC, JP KEGG) with a fine-tuned PubMedBERT model.
Python 3.12 package plus Snakemake pipelines.

General repo conventions (layout, style, commits) live in AGENTS.md:
@AGENTS.md

## Environment
- `nix develop` (preferred) or `uv sync`; add `--extra annotator` for the annotation tool.
- Run commands through `uv run …` when not inside the Nix shell.
- Tests: `uv run pytest` (tests sit next to code as `src/onsides/test_*.py`).

## CLI entry points (pyproject `[project.scripts]`)
- `build-zip --version vX.Y.Z` — release ZIP archive
- `onsides-construct-ref` — build reference/training sets
- `onsides-train` — fine-tune the BERT scorer
- `onsides-compute-flags` — annotation quality flags
- `onsides-annotate` — web annotation tool (FastAPI); needs parsed labels in `_onsides/us/labels/`

## Pipelines
- Per-region download/parse: `snakemake/{us,uk,eu,jp}/`.
- Training experiments: `snakemake -s snakemake/onsides/train/Snakefile --config experiment=<name>|all -j1`;
  parameter grids come from `experiments.json`.
- Evaluate and export: `snakemake/onsides/{evaluate,export}/`.
- A full refresh is long (days) and needs a GPU for BERT scoring. For a data
  release, follow AGENT_UPDATE_GUIDE.md (written for agents) — not UPDATE_INSTRUCTIONS.md.

## Versioning (see VERSIONING.md)
- Code is `major.minor.patch`: major = what/how we extract (schema changes),
  minor = quality changes that alter output, patch = no output change.
- Data releases are `<code_version>-<YYYYMMDD>`.
- When the version moves, update `pyproject.toml` and `CHANGELOG.md` together.

## Annotation tool
- `src/onsides/annotator/`; task definitions are YAML in `src/onsides/annotator/tasks/`.
- Annotations it produces are the independent evaluation set — never mix them
  into training data.

## Model
- Published at huggingface.co/tatonettilab/onsides-bert via
  `scripts/upload_to_huggingface.py`. Update the README "Model accuracy" numbers
  whenever the model changes.

## Don't
- Commit generated data or `_onsides/` intermediates (~40 GB); releases ship via GitHub Releases.
- Change `database/schema/*.sql` without noting it in the PR and CHANGELOG.
