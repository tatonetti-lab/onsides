#!/bin/bash
# Populate the onsides.about table
# Usage: ./run_populate_about.sh

# Check and prompt for required environment variables
# Password can be set via PGPASSWORD env var or .pgpass file

if [[ -z "${PGHOST:-}" ]]; then
  read -p "Enter PGHOST (default: localhost): " PGHOST
  PGHOST="${PGHOST:-localhost}"
fi

if [[ -z "${PGPORT:-}" ]]; then
  read -p "Enter PGPORT (default: 5432): " PGPORT
  PGPORT="${PGPORT:-5432}"
fi

if [[ -z "${PGUSER:-}" ]]; then
  read -p "Enter PGUSER (default: postgres): " PGUSER
  PGUSER="${PGUSER:-postgres}"
fi

if [[ -z "${PGDATABASE:-}" ]]; then
  read -p "Enter PGDATABASE: " PGDATABASE
  if [[ -z "$PGDATABASE" ]]; then
    echo "PGDATABASE is required." >&2
    exit 1
  fi
fi

# Run the population script
psql \
    --host="$PGHOST" \
    --port="$PGPORT" \
    --username="$PGUSER" \
    --dbname="$PGDATABASE" \
    --file="database/scripts/populate_about_table.sql" \
    --echo-errors \
    --quiet