#!/bin/bash

set -e

# Spin up the database
podman run --name mysql-container -e MYSQL_ALLOW_EMPTY_PASSWORD=yes -p 3306:3306 -d mysql:latest

# Allow some time for the container to initialize
sleep 5

# Set up database
podman exec mysql-container mysql -e "
CREATE DATABASE IF NOT EXISTS onsides CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE onsides;
SET GLOBAL max_allowed_packet = 1073741824;
SET GLOBAL character_set_server = 'utf8mb4';
SET GLOBAL character_set_client = 'utf8mb4';
SET GLOBAL character_set_connection = 'utf8mb4';
SET GLOBAL local_infile = 1;
"

cd database/schema

# Import schema - non-interactive
podman exec -i mysql-container mysql onsides <mysql.sql

cd ../csv

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

# Copy all CSV files to container
for file in "${CSV_FILES[@]}"; do
    echo "Copying $file to container..."
    podman cp "$file" "mysql-container:/$file"
done

# Loop through files and execute LOAD DATA commands one by one
for file in "${CSV_FILES[@]}"; do
    table=${file%.csv} # Remove .csv extension to get table name
    echo "Loading $file into $table table..."
    podman exec mysql-container mysql --local-infile=1 -e "
  USE onsides;
  LOAD DATA LOCAL INFILE '/$file'
  INTO TABLE $table
  CHARACTER SET utf8mb4
  FIELDS TERMINATED BY ','
  OPTIONALLY ENCLOSED BY '\\\"'
  LINES TERMINATED BY '\\n'
  IGNORE 1 ROWS;
  "
done

echo "Data import completed successfully!"

cd ..
