import numpy as np
import argparse
import pandas as pd
import requests
from tqdm import tqdm
from glob import glob
import ast, json
from bs4 import BeautifulSoup

from functions import format_code
from extract_ades_functions import extract_metadata, parse_metadata_df, extract_ades, extract_serious_ades, \
                                   extract_special_pop_ades, extract_ddi

def main():
    parser = argparse.ArgumentParser(description='download drug labels from KEGG website')
    parser.add_argument('--data_folder', required=True, help='Path to the data folder.')
    args = parser.parse_args()

    data_folder = args.data_folder

    #read in table of drugs
    kegg_df = pd.read_csv(data_folder+'kegg_rx_drug_data.csv')
    print(kegg_df.shape[0])

    #extract metadata for drugs
    japic_df = extract_metadata(kegg_df, data_folder, type = 'rx')

    #format the metadata to make usable
    japic_df = parse_metadata_df(japic_df, data_folder, type = 'rx')

    #extract ades from the drug labels
    ades_df, failed_df = extract_ades(japic_df, data_folder, type = 'rx')
    #extract serious ades from drug labels
    serious_ades_df = extract_serious_ades(kegg_df, data_folder, type = 'rx')

    #extract special populations ades from drug labels
    special_pop_ades_df = extract_special_pop_ades(kegg_df, data_folder, type = 'rx')

    #extract drug-drug interactions from drug labels
    ddi_ades_df = extract_ddi(kegg_df, data_folder, type = 'rx')

if __name__ == "__main__":
    main()