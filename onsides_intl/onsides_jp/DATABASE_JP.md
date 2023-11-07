# OnSIDES-JP Database Generation Walkthrough

Generating the database is done in five steps:

1. download the ingredient and drug tables, and then download the individual drug label files  (`download_files.py`)
2. extract the ades (and other relevant data) - all of the ades for JP data is in tabular form (`extract_ades.py`) - specific helper functions are in `extract_ades_functions.py`
3. extact the ades against a standard vocabulary, and for the strings we are unable to extract ades for, we translate and then use onsides model (`predict_ades.py`)
4. for the drugs we have in the database, map to standard vocabulary (RxNorm) (`map_drugs_to_rxnorm.py`)
5. integrate the results between the terms directly extracted and predicted, and map to standard vocabularies (`build_onsides_jp.py`)

## Semi-Automatic OnSIDES-JP Database Generation

As with the OnSIDES database, we provide a semi-automatic script to go through the whole process of generating OnSIDES-JP to aid with the periodic updating of the database.
Currently, this only supports a default pipeline, with external data and models expected to already be in the local environment - however, we aim to add further customizability as we develop this method further. Additionally, we will add further checks to keep all of the processing stable.

Before running, make sure you are in the onsides_intl folder.
```bash
# to download the individual drug label files
python3 onsides_jp/src/download_files.py --data_folder onsides_jp/data
# to run the processing of the extraction of the ADE terms
python3 onsides_jp/src/compute_onsides_jp.py --data_folder onsides_jp/data --external_data external_data --model models --commands onsides_jp/src
# to build the database itself
python3 onsides_jp/src/build_onsides_eu.py --data_folder onsides_jp/data --external_data external_data --final_data onsides_jp/final_data
```