# OnSIDES-EU Database Generation Walkthrough

Generating the database is done in seven steps:

1. download the ingredient and drug tables, and then download the individual drug label files  (`download_files.py`)
2. for the PDF file, extract all of the text data and tabular data using pypdf and tabula into txt and csv files respectively (`parse_files.py`)
3. for the tabular adverse drug event data, extract terms from structured text using standard vocabulary (`tabular_data_mapping.py`) 
4. for the free-text data, we first parse the data to extract the ADE section from the PDF-extracted text (`text_data_parse.py`) 
4. then, from the free-text data, we format data to be able to run the onsides model (`text_data_format.py`)
5. apply the model to score feature sentence fragments (`text_data_predict.py`)
6. for the drugs we have, map to standard vocabulary (RxNorm) (`map_drugs_to_rxnorm.py`)
7. integrate the results between the terms extracted from the tabular and free-text data, and map to standard vocabularies (`build_onsides_eu.py`)

## Semi-Automatic OnSIDES-EU Database Generation

As with the OnSIDES database, we provide a semi-automatic script to go through the whole process of generating OnSIDES-EU to aid with the periodic updating of the database.
Currently, this only supports a default pipeline, with external data and models expected to already be in the local environment - however, we aim to add further customizability as we develop this method further. Additionally, we will add further checks to keep all of the processing stable.

Before running, make sure you are in the onsides_intl folder.
```bash
# to download the individual drug label files
python3 onsides_eu/src/download_files.py --data_folder onsides_eu/data
# to run the processing of the extraction of the ADE terms
python3 onsides_eu/src/compute_onsides_uk.py --data_folder onsides_eu/data --external_data external_data --model models --commands onsides_eu/src
# to build the database itself
python3 onsides_eu/src/build_onsides_eu.py --data_folder onsides_eu/data --external_data external_data --final_data onsides_eu/final_data
```