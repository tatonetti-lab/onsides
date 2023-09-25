import argparse
import os
import numpy as np
import pandas as pd
import requests, ast, json
from tqdm import tqdm
from glob import glob
from functions import format_code, download_html
import openai

def main():
    parser = argparse.ArgumentParser(description='in this module, we extract the ade terms from each drug label section.')
    parser.add_argument('--data_folder', required=True, help='Path to the data folder.')
    parser.add_argument('--external_data_folder', required=True, help='Path to the external data folder.')
    parser.add_argument('--api_keys', required=True, help='Path to json file where api keys are stored.', default='api_keys.json')
    parser.add_argument('--model_path', required=True, help='Path to the where the model is housed.')
    args = parser.parse_args()

    data_folder = args.data_folder
    external_data_folder = args.external_data_folder
    api_file = args.api_key
    model_path = args.model_path

    with open(api_file) as apis:
        apis = json.load(apis)
    api = apis['umls_api_key']

    #read in raw dataframe
    ades_df = pd.read_csv(data_folder+'rx_drug_ade_raw.csv')
    print(ades_df.shape, len(ades_df.japic_code.unique().tolist()))
    #because we have strings of data table cells, we just look into the unique cell strings. (there is a lot of overlap)
    unique_ades = ades_df[['ade']].drop_duplicates()
    print(unique_ades.shape)

    ###############################################################
    #STEP 1. direct extraction from strings - most cells are well formatted, and can be extracted with just direct extraction.
    #read in the meddra map file
    umls_map = pd.read_csv(external_data_folder+'umls_meddra_jp.csv')
    umls_mjp_str_sdui = dict(zip(umls_map.STR, umls_map.SDUI)) #dict of meddra str -> sdui
    #read in the mesh-jp map file
    umls_mshjp = pd.read_csv(external_data_folder+'umls_mshjpn.csv')
    umls_mshjp = umls_mshjp[['CUI', 'STR']].merge(umls_map[['CUI', 'SDUI']], on = 'CUI', how = 'inner')
    umls_mshjp_str_cui = dict(zip(umls_mshjp.STR, umls_mshjp.SDUI)) #dict of mesh-jp -> meddra sdui

    meddra_found_ades = []
    mesh_found_ades = []
    meddra_names = umls_map.STR.unique().tolist()
    mesh_names = umls_mshjp.STR.unique().tolist()

    for ade_text in tqdm(unique_ades.ade.tolist()):
        ar_text = ade_text
        meddra_found_terms = []
        mesh_found_terms = []
        #iterate through list of meddra concepts, if found - add to list
        for concept_name in meddra_names:
            if ar_text.find(concept_name) == -1:
                continue
            else:
                meddra_found_terms.append(concept_name)
        #check to see if term is in MeSH too (extra coverage)
        for concept_name in mesh_names:
            if ar_text.find(concept_name) == -1:
                continue
            else:
                mesh_found_terms.append(concept_name)
        mesh_found_ades.append(mesh_found_terms)
        meddra_found_ades.append(meddra_found_terms)

    unique_ades['meddra_ade_list'] = meddra_found_ades
    unique_ades['mesh_ade_list'] = mesh_found_ades
    unique_ades['ade_combination_num'] = unique_ades.ade_list.apply(lambda x: len(x) if x!= None else None)
    unique_ades.to_csv(data_folder+'rx_raw_ade_extraction.csv', index=False)

    ###############################################################
    #STEP 2. onsides extraction - some cells are not well formatted, or convoluted, so we use onsides to extract the ade terms.
    unique_ades = pd.read_csv(data_folder+'rx_raw_ade_extraction.csv')
    unique_ades['meddra_ade_list'] = unique_ades['meddra_ade_list'].apply(lambda x: ast.literal_eval(x))
    unique_ades['mesh_ade_list'] = unique_ades['mesh_ade_list'].apply(lambda x: ast.literal_eval(x))
    unique_ades['ade_combination_num'] = unique_ades.apply(lambda x: len(x.meddra_ade_list) + len(x.mesh_ade_list), axis = 1)
    unique_ades = unique_ades.drop('ade_list', axis = 1)

    #we will only do translation extraction for the text with no terms extracted for now
    gpt_extraction = unique_ades[unique_ades.ade_combination_num == 0][['ade']]
    gpt_translation = []
    for word in tqdm(gpt_extraction.ade.tolist()):
        completion = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "user", "content": "Translate the following text including medical terms into English."\
                "Reply with only the translation. The word is {}".format(word)}
            ]
            )
        term = completion.choices[0].message['content']
        gpt_translation.append(term)
    gpt_extraction['translation'] = gpt_translation
    gpt_extraction.to_csv(data_folder+'rx_raw_ade_gpt_extraction.csv', index=False)

    #we will then extract the meddra terms from the gpt-3 translation
    gpt_extraction = pd.read_csv(data_folder+'rx_raw_ade_gpt_extraction.csv')

    #read in the meddra map file
    umls_map = pd.read_csv(external_data_folder+'umls_meddra_en.csv')
    umls_map['STR'] = umls_map.STR.apply(lambda x: x.lower())
    umls_men_str_sdui = dict(zip(umls_map.STR, umls_map.SDUI)) #dict of meddra str -> sdui
    meddra_names = umls_map.STR.tolist()

    app_data = []
    for ade_text in tqdm(gpt_extraction.translation.tolist()):
        ade_text = ade_text.lower()
        meddra_found_terms = []
        #iterate through list of meddra concepts, if found - add to list
        for concept_name in meddra_names:
            if ade_text.find(concept_name) == -1:
                continue
            else:
                i = ade_text.index(concept_name)
                meddra_found_terms.append([i, concept_name, umls_men_str_sdui[concept_name]])
    app_data.append([ade_text, meddra_found_terms])

    app_data_df = pd.DataFrame(app_data, columns = ['string', 'list'])
    app_data_df = app_data_df.explode('list')
    app_data_df['index'] = app_data_df['list'].apply(lambda x: x[0] if str(x) != 'nan' else None)
    app_data_df['found_term'] = app_data_df['list'].apply(lambda x: x[1] if str(x) != 'nan' else None)
    app_data_df['meddra_id'] = app_data_df['list'].apply(lambda x: x[2] if str(x) != 'nan' else None)
    app_data_df = app_data_df.drop(['list'], axis = 1)
    app_data_df.to_csv(data_folder+'rx_raw_ade_gpt_onsides_app.csv', index=False)

    #format into a onsides-usable dataframe
    app_data_df = pd.read_csv(data_folder+'data/ade/rx_raw_ade_gpt_onsides_app.csv')
    app_data_df['term_len'] = app_data_df.found_term.apply(lambda x: len(x) if str(x) != 'nan' else None)
    app_data_df = app_data_df[app_data_df.term_len >= 5]
    app_data_df['section'] = 'AR'
    app_data_df['drug'] = 'KEGG DRUG'
    app_data_df['label_id'] = 'KEGG'
    app_data_df['set_id'] = 'KEGG'
    app_data_df['spl_version'] = 'v1'
    app_data_df['source_method'] = 'GPT'

    meddra_llt_pt = pd.read_csv(external_data_folder+'meddra_llt_pt_map.txt', delimiter = '|')
    meddra_llt_pt_name_dict = dict(zip(meddra_llt_pt.llt_concept_name, meddra_llt_pt.pt_concept_name))
    meddra_pt_pt_name_dict = dict(zip(meddra_llt_pt.pt_concept_name, meddra_llt_pt.pt_concept_name))
    meddra_llt_pt_code_dict = dict(zip(meddra_llt_pt.llt_concept_name, meddra_llt_pt.pt_concept_code))
    meddra_pt_pt_code_dict = dict(zip(meddra_llt_pt.pt_concept_name, meddra_llt_pt.pt_concept_code))
    app_data_df['pt_meddra_term'] = app_data_df['found_term'].apply(lambda x: meddra_pt_pt_name_dict[x] if x in meddra_pt_pt_name_dict.keys() \
                                                                    else (meddra_llt_pt_name_dict[x] if x in meddra_llt_pt_name_dict.keys() else \
                                                                        None) )
    app_data_df['pt_meddra_id'] = app_data_df['found_term'].apply(lambda x: meddra_pt_pt_code_dict[x] if x in meddra_pt_pt_code_dict.keys() \
                                                                    else (meddra_llt_pt_code_dict[x] if x in meddra_llt_pt_code_dict.keys() else \
                                                                        None) )
    
    app_data_df.to_csv(data_folder+'rx_raw_ade_gpt_onsides_app.csv', index=False)
    app_data_df.to_csv(data_folder+'sentences-rx_method14_nwords125_clinical_bert_application_set_AR.csv', index=False)

    ###############################################################
    #STEP 3. onsides prediction - we will use onsides to predict the ade terms for the remaining text.

    exact_terms_df = data_folder+'sentences-rx_method14_nwords125_clinical_bert_application_set_AR.csv'
    ar_model = model_path + 'bestepoch-bydrug-PMB_14-AR-125-all_222_24_25_2.5e-05_256_32.pth'
    #bw_model = model_path + data_folder+'bestepoch-bydrug-PMB_14-AR-125-all_222_24_25_2.5e-05_256_32.pth'

    #call the prediction model
    os.system('python3 src/predict.py --model {model} --examples {f}'.format(model = ar_model, f = exact_terms_df))

    #build files using predicted labels
    results = data_folder+'bestepoch-bydrug-PMB-sentences-rx_ref14-AR-125-all_222_24_25_2.5e-05_256_32.csv.gz'
    os.system('python3 src/predict.py --release v2.0.0-AR --results {r} --examples {f}'.format(r = results, f = exact_terms_df))

    #build files using predicted labels
    #TODO : customize the create_onsides_datafiles script for the EU data
    results = data_folder+'bestepoch-bydrug-PMB-sentences-rx_ref14-AR-125-all_222_24_25_2.5e-05_256_32.csv.gz'
    #os.system('python3 src/create_onsides_datafiles.py --release v2.0.0-AR --results {r} --examples {f}'.format(r = results, f = exact_terms_df))

    #right now, we have it set up to simply run through the results and just filter against the threshold used in the original OnSIDES output.
    res = results
    ex = exact_terms_df
    threshold = 0.4633
    res = pd.read_csv(res, header=None, names=['Pred0', 'Pred1'])
    ex = pd.read_csv(ex)
    df = pd.concat([ex, res], axis=1)
    print(df.shape[0])
    df = df[df.Pred0 > threshold]
    print(df.shape[0])
    df.to_csv(data_folder+'data/ade_text_table_onsides_pred.csv', index=False)

if __name__ == '__main__':
    main()