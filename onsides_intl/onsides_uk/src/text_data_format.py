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
    parser.add_argument('--map_folder', required=True, help='Path to the where the external data used for OnSIDES model is housed.')
    args = parser.parse_args()
    data_folder = args.data_folder
    external_data_folder = args.external_data
    map_folder = args.map_folder

    #read in table for drug-ade free-text data
    ade_text_table_df = pd.read_csv(data_folder+'drug_ade_text_parsed.csv')

    ##Standard Vocabulary Mapping - here, we will use the UMLS MedDRA tables.
    meddra_df = pd.read_csv(external_data_folder+'umls_meddra_en.csv')
    meddra_df['STR'] = meddra_df.STR.apply(lambda x: x.lower())
    meddra_df['len'] = meddra_df.STR.apply(lambda x: len(x))
    meddra_dict = dict(zip(meddra_df.STR, meddra_df.SDUI))
    meddra_df = meddra_df[(meddra_df.TTY == 'PT')|(meddra_df['len'] > 5)]

    exact_terms = []
    for i, row in tqdm(ade_text_table_df.iterrows()):
        label_id = row['drug']
        text = row['ade_txt'].lower()
        found_terms = list()
        for mdr_term in meddra_dict.keys():
            if text.find(mdr_term) == -1:
                continue
            else:
                li = text.split(mdr_term)
                start_pos = 0
                for i in range(len(li)-1):
                    # the occurrence of the word is at the end of the previous string
                    start_pos = sum([len(li[j]) for j in range(i+1)]) + i*len(mdr_term)
                    if not mdr_term == text[start_pos:(start_pos+len(mdr_term))]:
                        raise Exception(f" mdr_term: '{mdr_term}', term_in_text: '{text[start_pos:(start_pos+len(mdr_term))]}'")
                    found_terms.append((mdr_term, meddra_dict[mdr_term], start_pos, len(mdr_term)))
        exact_terms.append([label_id, found_terms])

    exact_terms_df = pd.DataFrame(exact_terms, columns=['label_id', 'found_terms'])
    exact_terms_df = exact_terms_df.explode('found_terms')
    exact_terms_df['len'] = exact_terms_df['found_terms'].apply(lambda x: x[3] if str(x) != 'nan' else None)
    exact_terms_df = exact_terms_df[exact_terms_df['len'] >= 5]
    exact_terms_df['found_term'] = exact_terms_df['found_terms'].apply(lambda x: x[0] if str(x) != 'nan' else None)
    exact_terms_df['meddra_id'] = exact_terms_df['found_terms'].apply(lambda x: x[1] if str(x) != 'nan' else None)
    exact_terms_df['location'] = exact_terms_df['found_terms'].apply(lambda x: x[2] if str(x) != 'nan' else None)
    exact_terms_df = exact_terms_df.drop(['found_terms', 'len'], axis = 1)

    building_strings = []
    ade_text_table_dict = dict(zip(ade_text_table_df.drug, ade_text_table_df.ade_txt))
    for i, row in tqdm(exact_terms_df.iterrows()):
        term, label_id, start_pos = row['found_term'], row['label_id'], row['location']
        #default settings
        nwords, prop_before = 125, 0.125
        #pull the full text
        ar_text = ade_text_table_dict[label_id]

        term_nwords = len(term.split())
        size_before = max(int((nwords-2*term_nwords)*prop_before), 1)
        size_after = max(int((nwords-2*term_nwords)*(1-prop_before)), 1)

        before_text = ar_text[:start_pos]
        after_text = ar_text[(start_pos+term_nwords):]

        before_parts = before_text.split()[-1*size_before:]
        after_parts = after_text.split()[:size_after]

        li = [term]
        li.extend(before_parts)
        li.append('EVENT')
        li.extend(after_parts)
        example_string = ' '.join(li)
        building_strings.append(example_string)
        exact_terms_df['string'] = building_strings
    
    #save dataframe
    exact_terms_df.to_csv(data_folder+'sentences-rx_method14_nwords125_clinical_bert_application_set_AR.csv', index=False)

    #further prep the data for the model
    #required columns : section, drug, label_id, set_id, spl_version, pt_meddra_id, pt_meddra_term
    exact_terms_df = pd.read_csv(data_folder+'sentences-rx_method14_nwords125_clinical_bert_application_set_AR_v0924.csv')
    exact_terms_df['section'] = 'AR'
    exact_terms_df['set_id'] = exact_terms_df['label_id']
    
    drug_map = pd.read_csv(map_folder+'spl/maps/20230512/rxnorm_mappings.txt', delimiter = '|')
    drug_id_dict = dict(zip(drug_map.SETID, drug_map.RXCUI))
    drug_ver_dict = dict(zip(drug_map.SETID, drug_map.SPL_VERSION))
    exact_terms_df['drug'] = exact_terms_df.set_id.apply(lambda x: drug_id_dict[x] if x in drug_id_dict.keys() else None)
    exact_terms_df['spl_version'] = exact_terms_df.set_id.apply(lambda x: drug_ver_dict[x] if x in drug_ver_dict.keys() else None)

    llt_pt = pd.read_csv(map_folder+'meddra_llt_pt_map.txt', delimiter = '|')
    llt_pt_id_dict = dict(zip(llt_pt.llt_concept_code, llt_pt.pt_concept_code))
    llt_pt_term_dict = dict(zip(llt_pt.llt_concept_code, llt_pt.pt_concept_name))
    exact_terms_df['pt_meddra_id'] = exact_terms_df.meddra_id.apply(lambda x: llt_pt_id_dict[x] if x in llt_pt_id_dict.keys() else None)
    exact_terms_df['pt_meddra_term'] =  exact_terms_df.meddra_id.apply(lambda x: llt_pt_term_dict[x] if x in llt_pt_term_dict.keys() else None)

    #save dataframe
    exact_terms_df.to_csv(data_folder+'sentences-rx_method14_nwords125_clinical_bert_application_set_AR.csv', index=False)

if __name__ == "__main__":
    main()