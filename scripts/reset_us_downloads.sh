#!/usr/bin/env bash
set -euo pipefail

# Reset US download artifacts so Snakemake will re-scrape and re-download.
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
US_DIR="${ROOT_DIR}/_onsides/us"

rm -f \
  "${US_DIR}/download_page.html" \
  "${US_DIR}/map_page.html" \
  "${US_DIR}/parsed.done" \
  "${US_DIR}/map_parsed.done"

find "${US_DIR}/download" -type f -name "*.zip" -delete 2>/dev/null || true
find "${US_DIR}/download" -type f -name "*.download" -delete 2>/dev/null || true
find "${US_DIR}/download" -type f -name "*.unzipped" -delete 2>/dev/null || true

find "${US_DIR}/map_download" -type f -name "*.zip" -delete 2>/dev/null || true
find "${US_DIR}/map_download" -type f -name "*.download" -delete 2>/dev/null || true

find "${US_DIR}/labelzips" -type f -name "*.zip" -delete 2>/dev/null || true
find "${US_DIR}/labels" -type f -name "*.xml" -delete 2>/dev/null || true
find "${US_DIR}/labels" -type f -name "*.json" -delete 2>/dev/null || true
rm -f "${US_DIR}/label_text.parquet"

echo "US download artifacts cleared. Re-run:"
echo "  snakemake -s snakemake/us/download/Snakefile --resources jobs=1"
