#!/usr/bin/env bash
set -euo pipefail

# Reset JP download artifacts so Snakemake will re-scrape and re-download.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JP_DIR="${ROOT_DIR}/_onsides/jp"

find "${JP_DIR}" -type f -name "*.html" -path "*/med_index_page/*" -delete 2>/dev/null || true
find "${JP_DIR}" -type f -name "*.html" -path "*/otc_index_page/*" -delete 2>/dev/null || true
find "${JP_DIR}" -type f -name "*.download" -path "*/med_index_page/*" -delete 2>/dev/null || true
find "${JP_DIR}" -type f -name "*.download" -path "*/otc_index_page/*" -delete 2>/dev/null || true
find "${JP_DIR}" -type f -name "*.json" -name "n_index_pages.json" -delete 2>/dev/null || true
find "${JP_DIR}" -type f -name "reparse_*.txt" -delete 2>/dev/null || true

find "${JP_DIR}" -type f -name "*.download" -path "*/med_labels/*" -delete 2>/dev/null || true
find "${JP_DIR}" -type f -name "*.download" -path "*/otc_labels/*" -delete 2>/dev/null || true
find "${JP_DIR}" -type f -name "*.html" -path "*/med_labels/*" -delete 2>/dev/null || true
find "${JP_DIR}" -type f -name "*.html" -path "*/otc_labels/*" -delete 2>/dev/null || true

find "${JP_DIR}" -type f -name "*.side_effects.html" -delete 2>/dev/null || true
find "${JP_DIR}" -type f -name "*.side_effects.txt" -delete 2>/dev/null || true
find "${JP_DIR}" -type f -name "*.tables.txt" -delete 2>/dev/null || true
find "${JP_DIR}" -type f -name "*.txt" -path "*/med_labels/*" -delete 2>/dev/null || true
find "${JP_DIR}" -type f -name "*.txt" -path "*/otc_labels/*" -delete 2>/dev/null || true
find "${JP_DIR}" -type f -name "*_label_text.parquet" -delete 2>/dev/null || true

echo "JP download artifacts cleared. Re-run:"
echo "  snakemake -s snakemake/jp/download/Snakefile --resources jobs=1"
