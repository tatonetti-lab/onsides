import numpy as np 
import pandas as pd
import requests
from tqdm import tqdm
from glob import glob
import ast, re
from time import sleep
import argparse
import warnings
warnings.filterwarnings('ignore')
import os

def main():
    parser = argparse.ArgumentParser(description='let the code know where the data is held')
    parser.add_argument('--data_folder', required=True, help='Path to the data folder.')
    parser.add_argument('--external_data', required=True, help='Path to the where the external data is housed.')

    args = parser.parse_args()
    data_folder = args.data_folder
    external_data_folder = args.external_data

    #get list of all tabular files.
    tbls = glob(data_folder+'raw_tbl/*')

    #iterate through all tabular files and extract the relevant tables (i.e. those with the columns of interest)
    ade_tbl = []
    for tbl in tqdm(tbls):
        drug = tbl.split('/')[-1].split('_')[0]
        try:
            df = pd.read_csv(tbl)
            if any([i in list(df.columns) for i in ['System', 'Very common', 'Common', 'Not known', 'Rare', 'Uncommon']]):
                col = df.columns.tolist()
                for i in col:
                    l = ' '.join([i for i in df[i].tolist() if str(i) != 'nan'])
                    ade_tbl.append([drug, i, l])
        except:
            pass
    
    ades_df = pd.DataFrame(ade_tbl, columns = ['drug', 'col', 'txt'])
    ades_df.to_csv(data_folder+'raw_ade_table_v0924.csv', index=False)


if __name__ == '__main__':
    main()