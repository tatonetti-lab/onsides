# OnSIDES Database Update Instructions

Follow these steps from the repo root to refresh the OnSIDES database artifacts.

## 1) Prepare the environment
- Preferred: `nix develop`
- Without Nix: `uv sync` and ensure these tools are installed and on PATH:
  `curl`, `unzip`, `pandoc`, `pdftotext`, `duckdb`, `sqlite3`, Java (for `tabula`).

## 2) Place required external data files
These are read directly by the pipeline:
- `data/mrconso.rrf` (UMLS MRCONSO; MedDRA vocab) Can be downloaded from: https://www.nlm.nih.gov/research/umls/new_users/online_learning/Meta_006.html
- `data/omop_vocab/CONCEPT.csv` (can be downloaded from OMOP common data model files)
- `data/omop_vocab/CONCEPT_RELATIONSHIP.csv`

## 3) Configure the BERT model paths
Update hardcoded paths in `snakemake/onsides/evaluate/Snakefile`:
- `network_path` (transformer model directory)
- `model_path` (trained weights)

## 4) Download label sources (per region)
```bash
snakemake -s snakemake/us/download/Snakefile --resources jobs=1
snakemake -s snakemake/uk/download/Snakefile --resources jobs=1
# 1/14/26:NPT - currently here with help from codex resume 019bbe12-8e55-7d91-9ccf-1a76df393af0
#             - running in screen -r onsides on thorshammer
# When running, please record the number of attempts it took to get this job to complete
# number of tries: 4
snakemake -s snakemake/eu/download/Snakefile --resources jobs=1 --keep-going
snakemake -s snakemake/jp/download/Snakefile --resources jobs=1
```
Notes:
- repeat each of these above until you get no output
- EU downloads are especially flaky; keep rerunning the EU download Snakefile until it completes.
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
