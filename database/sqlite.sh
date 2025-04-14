#!/bin/bash

set -e

# Define the SQLite database file
DATABASE="onsides.db"

cd database/

# Remove any existing database file to start fresh
if [ -f "$DATABASE" ]; then
    echo "Removing existing database file: $DATABASE"
    rm "$DATABASE"
fi

# Import the schema into the database
echo "Creating SQLite database and importing schema..."
sqlite3 "$DATABASE" <schema/sqlite.sql

echo "Importing CSV files..."

cd csv

CSV_FILES=(
    "vocab_meddra_adverse_effect.csv"
    "product_label.csv"
    "vocab_rxnorm_ingredient.csv"
    "vocab_rxnorm_product.csv"
    "product_to_rxnorm.csv"
    "product_adverse_effect.csv"
    "vocab_rxnorm_ingredient_to_product.csv"
)

# Copy all CSV files to container
for file in "${CSV_FILES[@]}"; do
    # Derive table name from file base name (remove directory and .csv extension)
    table=$(basename "$file" .csv)
    echo "Loading $file into ${table} table..."

    # Use sqlite3's .import command in CSV mode to load the data
    sqlite3 "../$DATABASE" <<EOF
.mode csv
.import --skip 1 '$file' $table
EOF
done

echo "Data import completed successfully!"

cd ..
