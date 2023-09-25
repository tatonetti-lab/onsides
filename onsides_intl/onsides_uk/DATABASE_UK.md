# OnSIDES-UK Database Generation Walkthrough

Generating the database is done in six steps:

1. download the ingredient and drug tables, and then download the individual drug label files  (`download_files.py`)
2. parse the individual drug label files to extract the adverse drug event sections for each drug, and then the free-string text and tabular data from each section (`parse_files.py`)
3. for the tabular adverse drug event data, extract terms from structured text using standard vocabulary (`tabular_data_mapping.py`) 
4. construct data for onsides model to be run on free-text (`text_data_format.py`)
5. apply the model to score feature sentence fragments (`text_data_predict.py`)
6. integrate the results between the terms extracted from the tabular and free-text data, and map to standard vocabularies (`build_onsides_uk.py`)

