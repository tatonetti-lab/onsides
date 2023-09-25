import numpy as np 
import pandas as pd
import requests
from tqdm import tqdm
import ast, re
from time import sleep
import argparse
import warnings
warnings.filterwarnings('ignore')
import os

def main():
    print('run the model')
    parser = argparse.ArgumentParser(description='let the code know where the data is held')
    parser.add_argument('--data_folder', required=True, help='Path to the data folder.')
    parser.add_argument('--external_data', required=True, help='Path to the where the external data is housed.')
    parser.add_argument('--model_path', required=True, help='Path to the where the model is housed.')

    args = parser.parse_args()
    data_folder = args.data_folder
    external_data_folder = args.external_data
    model_path = args.model_path

    exact_terms_df = data_folder+'sentences-rx_method14_nwords125_clinical_bert_application_set_AR.csv'
    ar_model = model_path + data_folder+'bestepoch-bydrug-PMB_14-AR-125-all_222_24_25_2.5e-05_256_32.pth'
    #bw_model = model_path + data_folder+'bestepoch-bydrug-PMB_14-AR-125-all_222_24_25_2.5e-05_256_32.pth'

    #call the prediction model
    os.system('python3 src/predict.py --model {model} --examples {f}'.format(model = ar_model, f = exact_terms_df))

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