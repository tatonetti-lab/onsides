# OnSIDES Database Update Instructions

Follow these steps from the repo root to refresh the OnSIDES database artifacts.

## Computational requirements

A full pipeline run requires:
- **Disk**: ~40 GB for intermediate files (`_onsides/`), plus ~4 GB for external data files.
- **GPU**: Required for Step 6 (BERT scoring). A single GPU is sufficient.
- **RAM**: 16 GB+ recommended for the DuckDB-based export and vocabulary steps.
- **Time estimates** (will vary by hardware and network):

| Step | Duration | Notes |
|------|----------|-------|
| 4. Download | Hours to days | EU and JP sources are flaky; expect multiple reruns |
| 5. Parse | Hours | US is the largest (~51k labels) |
| 6. Evaluate | Days (single-digit) | GPU-bound; BERT scoring over millions of string matches |
| 7. Export | Minutes | CPU-only, DuckDB + SQLite |
| 8. Build zip | Seconds | |

We recommend running long steps (download, parse, evaluate) in `screen` or `tmux` sessions.

## 1) Prepare the environment
- Preferred: `nix develop`
- Without Nix: `uv sync` and ensure these tools are installed and on PATH:
  `curl`, `unzip`, `pandoc`, `pdftotext`, `duckdb`, `sqlite3`, Java (for `tabula`).

## 2) Place required external data files
These are read directly by the pipeline:
- `data/mrconso.rrf` (UMLS MRCONSO; MedDRA vocab) Can be downloaded from: https://www.nlm.nih.gov/research/umls/new_users/online_learning/Meta_006.html
- `data/omop_vocab/CONCEPT.csv` (can be downloaded from OMOP common data model files)
- `data/omop_vocab/CONCEPT_RELATIONSHIP.csv`

## 3) Place BERT model files
The evaluate step expects model files under `models/` in the repo root:
- `models/microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract/` (transformer model directory)
- `models/bestepoch-bydrug-PMB_14-ALL-125-all_222_24_25_1e-06_256_32.pth` (trained weights)

To use a different location, pass `--config network_path=/path/to/model weights_path=/path/to/weights.pth` to the evaluate snakemake command.

## 4) Download label sources (per region)
```bash
snakemake -s snakemake/us/download/Snakefile --resources jobs=1
snakemake -s snakemake/uk/download/Snakefile --resources jobs=1
snakemake -s snakemake/eu/download/Snakefile --resources jobs=1 --keep-going
snakemake -s snakemake/jp/download/Snakefile --resources jobs=1 --keep-going
```
Notes:
- repeat each of these above until you get no output
- EU and JP downloads are flaky (KEGG resets connections); use `--keep-going`
  and keep rerunning until all labels are fetched.
- US download also pulls DailyMed map files. The export step expects:
  `_onsides/us/map_download/rxnorm_mappings.txt` and
  `_onsides/us/map_download/dm_spl_zip_files_meta_data.txt`.
  If they arrive zipped, unzip them in place.
- If will need to force a clean US re-download, run:
  ```bash
  bash scripts/reset_us_downloads.sh
  ```
  This clears US downloads plus extracted label zips, parsed label files, and
  `_onsides/us/label_text.parquet` so the pipeline fully re-extracts. Note that
  after you reset the us downloads, you will also have to run the snakemake command 
  above twice, once to download and once to process.

## 5) Parse labels into standardized text
```bash
snakemake -s snakemake/us/parse/Snakefile
snakemake -s snakemake/uk/parse/Snakefile
snakemake -s snakemake/eu/parse/Snakefile
snakemake -s snakemake/jp/parse/Snakefile
```
Outputs land in `_onsides/*/label_text.parquet`.

**Checkpoint — verify parsed labels before continuing.** Empty or missing parquet
files will silently propagate through the rest of the pipeline, producing a release
with missing data for that region. Run:
```bash
python -c "
import polars as pl
for source, path in [
    ('US', '_onsides/us/label_text.parquet'),
    ('UK', '_onsides/uk/label_text.parquet'),
    ('EU', '_onsides/eu/label_text.parquet'),
    ('JP', '_onsides/jp/med_label_text.parquet'),
]:
    df = pl.read_parquet(path)
    print(f'{source}: {len(df):,} rows ({path})')
"
```
All four sources should have a non-zero row count. If any are empty, check that the
download step fully completed for that region before re-running the parse.

## 6) Build vocabularies, match terms, run model scoring
```bash
snakemake -s snakemake/onsides/evaluate/Snakefile
```
This creates vocab files in `_onsides/vocab/` and predictions in
`_onsides/combined/`.

## 7) Export final database artifacts
```bash
snakemake -s snakemake/onsides/export/Snakefile
```
This produces:
- `database/onsides.db`
- `database/csv/*.csv`
- `database/schema/{sqlite,postgres,mysql}.sql`
- `database/csv/high_confidence.csv`

## 8) (Optional) Build release zip
```bash
build-zip --version vX.Y.Z
```
