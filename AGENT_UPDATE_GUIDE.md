# OnSIDES Data Update Guide for AI Agents

This document gives an AI coding agent (e.g. Claude Code) the context it needs to
assist a human operator in producing a new OnSIDES data release. Read this file in
full before starting work. Refer to `UPDATE_INSTRUCTIONS.md` for the canonical
step-by-step commands; this file supplements it with troubleshooting knowledge,
validation procedures, and lessons learned from prior releases.

## Overview

OnSIDES extracts structured adverse-event data from drug product labels across four
regulatory regions (US, UK, EU, Japan). The pipeline downloads labels, parses them
into text, matches MedDRA terms via string search, scores matches with a BERT model,
and exports a SQLite database plus CSV files.

The pipeline is orchestrated by Snakemake. Each region has its own download and parse
Snakefile. The evaluate and export stages are shared across all regions.

```
Step 1: Environment setup
Step 2: External data files (MRCONSO.RRF, OMOP vocab)
Step 3: BERT model files
Step 4: Download labels (US, UK, EU, JP — can run in parallel)
Step 5: Parse labels (US, UK, EU, JP — can run in parallel)
Step 6: Evaluate (vocab build + string matching + BERT scoring)
Step 7: Export (DuckDB transforms + SQLite database)
Step 8: Build release zip
```

## Your role as agent

You are assisting a human operator who will run commands in their terminal. Your
responsibilities:

- **Diagnose errors** by reading Snakemake logs and rule-specific log files.
- **Fix code issues** when pipeline failures are caused by bugs (not data problems).
- **Validate outputs** at checkpoints between steps.
- **Track progress** — the pipeline takes days end-to-end; use your memory system
  to record which steps are complete so you can resume across conversations.
- **Do NOT run long pipeline commands yourself** — the operator runs them in
  `screen`/`tmux` sessions. You read logs and fix code.

## Environment

- **Python**: 3.12 via `uv`. Use `uv run` for Python commands.
- **System tools**: `pandoc`, `pdftotext`, `duckdb`, `sqlite3`, `curl`, `unzip`,
  Java (for tabula). These come from `nix develop`. The Snakemake `shell:` rules
  need these on PATH, so the operator must run pipeline commands inside `nix develop`
  (or `nix develop -c <command>`). `uv run snakemake ...` alone will NOT have pandoc,
  duckdb, etc.
- **GPU**: Required for Step 6 (BERT scoring). One GPU is sufficient.
- **Disk**: ~40 GB for `_onsides/` intermediates, ~4 GB for external data.

## Step-by-step details and known issues

### Step 1: Environment

```bash
uv sync
```

Verify with `uv run python -c "import onsides"`.

### Step 2: External data files

| File | Location | Source |
|------|----------|--------|
| UMLS MRCONSO | `data/MRCONSO.RRF` | UMLS license required. Must be the **full** file (~17M rows, several GB). A truncated sample will produce empty vocabulary tables. |
| OMOP CONCEPT | `data/omop_vocab/CONCEPT.csv` | OMOP CDM vocabulary download |
| OMOP CONCEPT_RELATIONSHIP | `data/omop_vocab/CONCEPT_RELATIONSHIP.csv` | Same source |

**Validation**: `wc -l data/MRCONSO.RRF` should show millions of lines. If it shows
<1000 lines, the file is a sample and will silently produce empty outputs.

**Important**: The filename is case-sensitive. All SQL and Snakefile references use
`MRCONSO.RRF` (uppercase). If the file is named `mrconso.rrf`, rename it.

### Step 3: BERT model files

Expected at:
- `models/microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract/`
- `models/bestepoch-bydrug-PMB_14-ALL-125-all_222_24_25_1e-06_256_32.pth`

Symlinks are fine. Custom paths can be passed:
```bash
snakemake -s snakemake/onsides/evaluate/Snakefile \
  --config network_path=/path/to/model weights_path=/path/to/weights.pth
```

### Step 4: Download

Commands (run inside `nix develop` or `nix develop -c ...`):
```bash
snakemake -s snakemake/us/download/Snakefile --resources jobs=1
snakemake -s snakemake/uk/download/Snakefile --resources jobs=1
snakemake -s snakemake/eu/download/Snakefile --resources jobs=1 --keep-going
snakemake -s snakemake/jp/download/Snakefile --resources jobs=1 --keep-going
```

**Known issues**:
- **EU and JP are flaky.** KEGG and EMA servers reset connections. Use `--keep-going`
  and re-run until Snakemake reports nothing to do.
- **US map files arrive zipped.** After download, check:
  ```
  _onsides/us/map_download/rxnorm_mappings.txt
  _onsides/us/map_download/dm_spl_zip_files_meta_data.txt
  ```
  If only `.zip` files exist, unzip them in place:
  ```bash
  cd _onsides/us/map_download && unzip -o rxnorm_mappings.zip && unzip -o dm_spl_zip_files_meta_data.zip
  ```
  The export step will fail with `MissingInputException` if these are still zipped.

### Step 5: Parse

Commands (run inside `nix develop`):
```bash
snakemake -s snakemake/us/parse/Snakefile
snakemake -s snakemake/uk/parse/Snakefile
snakemake -s snakemake/eu/parse/Snakefile
snakemake -s snakemake/jp/parse/Snakefile --keep-going
```

**Known issues**:
- **JP labels without side-effects section.** Many Japanese labels (~55%) lack a
  `par-11` (side effects) section. `pull_side_effects_jp` writes an empty file for
  these. This is expected — they are supplements, diagnostics, etc.
- **pandoc must be on PATH.** The `convert_html_to_text` rule calls pandoc via
  `shell:`. If you get "command not found", the operator needs to be in the nix
  shell.
- **Filename length (JP).** `sanitize_filename` truncates to 220 bytes to leave
  room for derived suffixes (`.side_effects.table.NN.csv` = up to 27 bytes). If you
  see `ENAMETOOLONG` errors, the byte budget may need further reduction.

**Checkpoint validation** (run after all four regions complete):
```python
import polars as pl
for source, path in [
    ('US', '_onsides/us/label_text.parquet'),
    ('UK', '_onsides/uk/label_text.parquet'),
    ('EU', '_onsides/eu/label_text.parquet'),
    ('JP', '_onsides/jp/med_label_text.parquet'),
]:
    df = pl.read_parquet(path)
    print(f'{source}: {len(df):,} rows ({path})')
```
All four must have non-zero row counts. Expected order of magnitude:
US ~50k, UK ~7k, EU ~1.5k, JP ~9k.

### Step 6: Evaluate

```bash
snakemake -s snakemake/onsides/evaluate/Snakefile
```

This is the longest step (days on a single GPU). It runs:
1. `build_vocabulary` — DuckDB reads MRCONSO.RRF, extracts MedDRA English and
   Japanese terms.
2. `build_labels` — Combines all regional parquets into English and Japanese label
   sets.
3. `string_match` — Finds exact MedDRA term matches in label text.
4. `evaluate_onsides` — BERT scoring on English string matches.
5. `create_jp_to_eng_meddra_map` — Builds Japanese-to-English MedDRA mapping.

**Note**: BERT scoring currently runs only on English labels. Japanese labels use
string match only (line 23 of the evaluate Snakefile).

**Known issues**:
- **DuckDB `ignore_errors = true`** is required for MRCONSO.RRF because some
  non-English UMLS rows contain invalid UTF-8 bytes. The skipped rows are irrelevant
  (Swedish, etc.) and do not affect English/Japanese MedDRA extraction.
- **Stale intermediate files.** If a previous run failed partway through, Snakemake
  may consider output files "done" even if they are empty or corrupt. Common symptom:
  `Matching 0 terms` in the string_match log. Fix: delete the stale parquet files
  and re-run.
  ```bash
  rm -f _onsides/vocab/meddra_*.parquet _onsides/combined/label_*_string_match.parquet
  rm -f duck.db
  ```

**Checkpoint validation** (after completion):
```python
import polars as pl
checks = {
    'MedDRA English vocab': '_onsides/vocab/meddra_english.parquet',
    'MedDRA Japanese vocab': '_onsides/vocab/meddra_japanese.parquet',
    'MedDRA JP-EN map': '_onsides/vocab/meddra_jp_to_eng.parquet',
    'English labels': '_onsides/combined/english_labels.parquet',
    'Japanese labels': '_onsides/combined/japanese_labels.parquet',
    'English string match': '_onsides/combined/label_english_string_match.parquet',
    'Japanese string match': '_onsides/combined/label_japanese_string_match.parquet',
    'English BERT preds': '_onsides/combined/label_english_preds.parquet',
}
for name, path in checks.items():
    df = pl.read_parquet(path)
    print(f'{name}: {len(df):,} rows')
```
Expected: vocab tables ~65-107k rows, string matches in the millions (English) or
hundreds of thousands (Japanese), BERT preds should equal English string match count.

### Step 7: Export

```bash
snakemake -s snakemake/onsides/export/Snakefile
```

This runs in minutes. It:
1. Maps each region's labels to RxNorm identifiers (DuckDB SQL scripts).
2. Generates RxNorm ingredient mappings.
3. Populates vocabulary tables (RxNorm, MedDRA).
4. Applies confidence thresholds.
5. Exports to `database/onsides.db` and `database/csv/*.csv`.

**Known issues**:
- **`duck.db` must be clean.** If a previous export run failed partway, `duck.db`
  will contain leftover tables causing `CREATE TABLE ... already exists` errors.
  Always delete `duck.db` and `database/onsides.db` before re-running:
  ```bash
  rm -f duck.db database/onsides.db
  ```
- **MedDRA UNIQUE constraint.** The MedDRA vocabulary INSERT uses `ROW_NUMBER()` to
  deduplicate — a single meddra_id can map to multiple names across OMOP and MRCONSO.
  If you see `UNIQUE constraint failed: vocab_meddra_adverse_effect.meddra_id`, the
  dedup logic may need attention.
- **US map files must be unzipped.** See Step 4 notes.

**Checkpoint validation**:
```python
import sqlite3
con = sqlite3.connect('database/onsides.db')
tables = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
for t in tables:
    count = con.execute(f'SELECT count(*) FROM [{t[0]}]').fetchone()[0]
    print(f'{t[0]}: {count:,} rows')
con.close()
```
Expected: `product_adverse_effect` in the millions, `product_label` in the tens of
thousands, vocabulary tables populated with non-zero counts.

### Step 8: Build release zip

```bash
build-zip --version vX.Y.Z
```

This packages `database/csv/`, `database/schema/`, `database/annotations/`, and
`database/database_scripts/` into `onsides-vX.Y.Z.zip`.

See `VERSIONING.md` for the version numbering convention:
- Code version: `major.minor.patch` (in `pyproject.toml`)
- Data version: `<code_version>-<YYYYMMDD>` for releases with new data

## General troubleshooting patterns

### Reading Snakemake errors

Snakemake logs are in `.snakemake/log/` (sorted by timestamp). The log shows which
rule failed and its inputs/outputs, but often not the actual error. Check:
1. The rule-specific log file (shown in the error as `log: ...`)
2. If the rule uses `run:` (inline Python), the traceback is in the Snakemake log.
3. If the rule uses `shell:`, stderr may not be captured — reproduce the command
   manually.

### Stale output files

Snakemake skips rules whose output files already exist. After a partial failure,
output files may be empty or corrupt. Delete them to force re-execution. Key files
that commonly need cleanup between retries:
- `duck.db` (DuckDB working database)
- `database/onsides.db` (final SQLite output)
- `_onsides/vocab/*.parquet` (vocabulary tables)
- `_onsides/combined/*_string_match.parquet` (string match outputs)

### Re-running a single step

To re-run only a specific rule, delete its output files and run the Snakefile
normally — Snakemake will pick up only the missing outputs.

### The `--keep-going` flag

Use `--keep-going` for download and JP parse steps. These have many independent jobs
and a few may fail transiently (network errors, server resets). Without this flag,
one failure stops the entire run.

## Tracking progress across conversations

Use your memory system to record:
- Which steps are complete (with dates)
- Row counts from validation checkpoints
- Any fixes applied during this release
- The target version number

This allows you to resume across multiple conversations without losing context.
