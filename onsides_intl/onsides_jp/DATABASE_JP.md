# OnSIDES-JP Database Generation Walkthrough

Generating the database is done in five steps:

1. download the ingredient and drug tables, and then download the individual drug label files  (`download_files.py`)
2. extract the ades (and other relevant data) - all of the ades for JP data is in tabular form (`extract_ades.py`) - specific helper functions are in `extract_ades_functions.py`
3. extact the ades against a standard vocabulary, and for the strings we are unable to extract ades for, we translate and then use onsides model (`predict_ades.py`)
4. for the drugs we have in the database, map to standard vocabulary (RxNorm) (`map_drugs_to_rxnorm.py`)
5. integrate the results between the terms directly extracted and predicted, and map to standard vocabularies (`build_onsides_jp.py`)
