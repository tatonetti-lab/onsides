#!/bin/bash

# Spin up the PostgreSQL database container
podman run --name postgres-container \
    -e POSTGRES_HOST_AUTH_METHOD=trust \
    -p 5432:5432 \
    -v data:/docker-entrypoint-initdb.d \
    -d postgres:latest

# Allow some time for the container to initialize
sleep 5

# Set up database: Create onsides with UTF8 encoding and appropriate locale settings.
podman exec postgres-container psql -U postgres -c "
CREATE DATABASE onsides
  WITH ENCODING 'UTF8'
       LC_COLLATE='en_US.UTF-8'
       LC_CTYPE='en_US.UTF-8'
       TEMPLATE=template0;
"

# Import schema (non-interactive). Assume your PostgreSQL schema file is named postgres.sql.
podman exec -i postgres-container psql -U postgres -d onsides -f - <data/schema/postgres.sql

cd data/csv

# Define array of CSV files
CSV_FILES=(
    "vocab_meddra_adverse_effect.csv"
    "product_label.csv"
    "vocab_rxnorm_ingredient.csv"
    "vocab_rxnorm_product.csv"
    "product_to_rxnorm.csv"
    "product_adverse_effect.csv"
    "vocab_rxnorm_ingredient_to_product.csv"
)

# Copy all CSV files to the container
for file in "${CSV_FILES[@]}"; do
    echo "Copying $file to container..."
    podman cp "$file" "postgres-container:/$file"
done

# Loop through files and execute COPY commands one by one
for file in "${CSV_FILES[@]}"; do
    table=${file%.csv} # Remove .csv extension to get table name
    echo "Loading $file into ${table} table..."
    podman exec postgres-container psql -U postgres -d onsides -c "
COPY ${table} FROM '/${file}' WITH (FORMAT csv, HEADER true, DELIMITER ',');
"
done

echo "Data import completed successfully!"
