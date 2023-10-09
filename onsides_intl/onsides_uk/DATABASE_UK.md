# OnSIDES-UK Database Generation Walkthrough

Generating the database is done in six steps:

1. download the ingredient and drug tables, and then download the individual drug label files  (`download_files.py`)
2. parse the individual drug label files to extract the adverse drug event sections for each drug, and then the free-string text and tabular data from each section (`parse_files.py`)
3. for the tabular adverse drug event data, extract terms from structured text using standard vocabulary (`tabular_data_mapping.py`) 
4. construct data for onsides model to be run on free-text (`text_data_format.py`)
5. apply the model to score feature sentence fragments (`text_data_predict.py`)
6. integrate the results between the terms extracted from the tabular and free-text data, and map to standard vocabularies (`build_onsides_uk.py`)

## Semi-Automatic OnSIDES-UK Database Generation

As with the OnSIDES database, we provide a semi-automatic script to go through the whole process of generating OnSIDES-UK to aid with the periodic updating of the database.
Currently, this only supports a default pipeline, with external data and models expected to already be in the local environment - however, we aim to add further customizability as we develop this method further. 

Before running, make sure you are in the onsides_intl folder.
```bash
# to download the individual drug label files
python3 onsides_uk/src/download_files.py --data_folder onsides_uk/data
# to run the processing of the extraction of the ADE terms
python3 onsides_uk/src/compute_onsides_uk.py --data_folder onsides_uk/data --external_data external_data --model models --commands onsides_uk/src
# to build the database itself
python3 onsides_uk/src/build_onsides_uk.py --data_folder onsides_uk/data --external_data external_data --final_data onsides_uk/final_data
```