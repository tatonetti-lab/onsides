#!/bin/bash
# Populate the onsides.about table
# Usage: ./run_populate_about.sh

# Set defaults if env vars not set
PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-5433}"
PGUSER="${PGUSER:-postgres}"
PGDATABASE="${PGDATABASE:-cem_development_2025}"

# Run the population script
psql \
    --host="$PGHOST" \
    --port="$PGPORT" \
    --username="$PGUSER" \
    --dbname="$PGDATABASE" \
    --file="database/scripts/populate_about_table.sql" \
    --echo-errors \
    --quiet