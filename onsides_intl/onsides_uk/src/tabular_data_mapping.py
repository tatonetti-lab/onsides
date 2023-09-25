import numpy as np 
import pandas as pd
import requests
from tqdm import tqdm
import ast, re
from time import sleep
import argparse
import warnings
warnings.filterwarnings('ignore')

def main():
    parser = argparse.ArgumentParser(description='let the code know where the data is held')
    parser.add_argument('--data_folder', required=True, help='Path to the data folder.')
    parser.add_argument('--external_data', required=True, help='Path to the where the external data is housed.')

    args = parser.parse_args()
    data_folder = args.data_folder
    external_data_folder = args.external_data

    processed_df = pd.read_csv(data_folder+'drug_ade_data_parsed.csv')
    processed_df = processed_df[['product_id', 'freq', 'soc', 'ade']]

    #to not increase the amount of computation, we will map the unique terms to standard vocabulary, and merge it back into the drug-ade tabular data later. 
    unique_terms = processed_df[['ade']].drop_duplicates()
    unique_terms = unique_terms[unique_terms.ade.notna()]

    ##Standard Vocabulary Mapping - here, we will use the UMLS MedDRA tables.
    meddra_df = pd.read_csv(external_data_folder+'umls_meddra_en.csv')
    meddra_df['STR'] = meddra_df.STR.apply(lambda x: x.lower())
    meddra_df['len'] = meddra_df.STR.apply(lambda x: len(x))
    meddra_dict = dict(zip(meddra_df.STR, meddra_df.SDUI))
    meddra_df = meddra_df[(meddra_df.TTY == 'PT')|(meddra_df['len'] > 5)]

    ## we match all of the terms in the vocabulary to the unique terms in the drug-ade tabular data to find matched terms.
    found_ades = []
    meddra_names = meddra_df.STR.tolist()
    for ade_text in tqdm(unique_terms.ade.tolist()):
        ar_text = ' '.join(ade_text.split()).lower() 
        found_terms = []
        for concept_name in meddra_names:
            if ar_text.find(concept_name) == -1:
                continue
            else:
                found_terms.append(concept_name)
        found_ades.append(found_terms)

    #save this as intermediate data.
    unique_terms['exact_match_list'] = found_ades
    unique_terms.to_csv(data_folder+'drug_ade_data_parsed_text_unique.csv', index=False)

    #we are able to extract the unique terms found in tabular data using the standard MedDRA vocabulary. 
    processed_df = processed_df.merge(unique_terms, on = 'ade', how = 'left')
    processed_df['matched_codes'] = processed_df.exact_match_list.apply(lambda x: [meddra_dict[i] for i in x] if str(x) != 'nan' else None)
    processed_df.to_csv(data_folder+'drug_ade_data_parsed.csv', index=False)

if __name__ == '__main__':
    main()