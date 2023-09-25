# OnSIDES-EU Database Generation Walkthrough

Generating the database is done in six steps:

1. download the ingredient and drug tables, and then download the individual drug label files  (`download_files.py`)
2. for the PDF file, extract all of the text data and tabular data using pypdf and tabula into txt and csv files respectively (`parse_files.py`)
3. for the tabular adverse drug event data, extract terms from structured text using standard vocabulary (`tabular_data_mapping.py`) 
4. for the free-text data, we first parse the data to extract the ADE section from the PDF-extracted text (`text_data_parse.py`) 
4. then, from the free-text data, we format data to be able to run the onsides model (`text_data_format.py`)
5. apply the model to score feature sentence fragments (`text_data_predict.py`)
6. integrate the results between the terms extracted from the tabular and free-text data, and map to standard vocabularies (`build_onsides_eu.py`)