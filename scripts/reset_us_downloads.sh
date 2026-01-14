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

rm -f "${US_DIR}"/download/*.zip
rm -f "${US_DIR}"/download/*.download
rm -f "${US_DIR}"/download/*.unzipped

rm -f "${US_DIR}"/map_download/*.zip
rm -f "${US_DIR}"/map_download/*.download

echo "US download artifacts cleared. Re-run:"
echo "  snakemake -s snakemake/us/download/Snakefile --resources jobs=1"
