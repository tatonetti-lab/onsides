'''
This script downloads Bemis-Murcko scaffolds and then splits the model input data based on scaffold type. 
Most of the script is derived from Chemprop documentation (https://chemprop.readthedocs.io/en/latest/_modules/chemprop/data/scaffold.html), while the rest is custom for this project.
Author : JK
'''

from collections import defaultdict
import logging
from random import Random
from typing import Dict, List, Set, Tuple, Union
import warnings
from rdkit import Chem
from rdkit.Chem.Scaffolds import MurckoScaffold
from tqdm import tqdm
import numpy as np
from chemprop.rdkit import make_mol
import os 
import random
import pandas as pd

#The following is from: https://chemprop.readthedocs.io/en/latest/_modules/chemprop/data/scaffold.html

def generate_scaffold(mol: Union[str, Chem.Mol, Tuple[Chem.Mol, Chem.Mol]], include_chirality: bool = False) -> str:

    if isinstance(mol, str):
        mol = make_mol(mol, keep_h = False, add_h = False)
    if isinstance(mol, tuple):
        mol = mol[0]
    scaffold = MurckoScaffold.MurckoScaffoldSmiles(mol = mol, includeChirality = include_chirality)

    return scaffold

def scaffold_to_smiles(mols: Union[List[str], List[Chem.Mol], List[Tuple[Chem.Mol, Chem.Mol]]],
                       use_indices: bool = False) -> Dict[str, Union[Set[str], Set[int]]]:

    scaffolds = defaultdict(set)
    for i, mol in tqdm(enumerate(mols), total = len(mols)):
        scaffold = generate_scaffold(mol)
        if use_indices:
            scaffolds[scaffold].add(i)
        else:
            scaffolds[scaffold].add(mol)

    return scaffolds


def scaffold_split(data, #data= smiles_list
                   sizes = (0.7, 0.15, 0.15), #t/v/t split
                   seed = 0):  

    # Split
    train_size, val_size, test_size = sizes[0] * len(data), sizes[1] * len(data), sizes[2] * len(data)
    train, val, test = [], [], []
    train_scaffold_count, val_scaffold_count, test_scaffold_count = 0, 0, 0

    # Map from scaffold to index in the data
    scaffold_to_indices = scaffold_to_smiles(data)

    # Seed randomness
    random = Random(seed)

    index_sets = list(scaffold_to_indices.values())
    big_index_sets = []
    small_index_sets = []
    for index_set in index_sets:
        if len(index_set) > val_size / 2 or len(index_set) > test_size / 2:
            big_index_sets.append(index_set)
        else:
            small_index_sets.append(index_set)
    random.seed(seed)
    random.shuffle(big_index_sets)
    random.shuffle(small_index_sets)
    index_sets = big_index_sets + small_index_sets

    for index_set in index_sets:
        if len(train) + len(index_set) <= train_size:
            train += index_set
            train_scaffold_count += 1
        elif len(val) + len(index_set) <= val_size:
            val += index_set
            val_scaffold_count += 1
        else:
            test += index_set
            test_scaffold_count += 1

    print('Number of scaffolds per set:',train_scaffold_count, val_scaffold_count, test_scaffold_count)
    print('Number of SMILES strings per set:',len(train), len(val), len(test))
    
    return train, val, test 


#Custom for this project 
smiles_data = pd.read_csv('../data/SMILES.csv')
random_seed = 0
seed = 0

train, val, test = scaffold_split(list(smiles_data['smiles']), seed = random_seed)
pd.DataFrame({'smiles':train}).to_csv('train_smiles_scaffoldtvt_rs'+str(random_seed)+'.csv', index=False)
pd.DataFrame({'smiles':val}).to_csv('val_smiles_scaffoldtvt_rs'+str(random_seed)+'.csv', index=False)
pd.DataFrame({'smiles':test}).to_csv('test_smiles_scaffoldtvt_rs'+str(random_seed)+'.csv', index=False)

def create_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

output_dir = 'combined_onsides_tvt_data_scaffold_split/'
create_dir(output_dir)        

adr_list=['Death and sudden death',
'Ventricular arrhythmias and cardiac arrest',
'Poisoning and toxicity',
'Nausea and vomiting symptoms',
'Cardiac signs and symptoms NEC',
'Sepsis, bacteraemia, viraemia and fungaemia NEC', 
'Renal failure and impairment',
'Heart failure signs and symptoms',
'Heart failures NEC', 
'Central nervous system haemorrhages and cerebrovascular accidents']


for adr in adr_list:    
    
    adr_df=pd.read_csv('combined_adr_data/'+adr.replace(' ','_')+'_binary_df.csv')
    print(adr, '\nOverall Dataset Imbalance:', round(sum(adr_df[adr])/adr_df.shape[0],4))
    
    adr_dir = output_dir+adr.replace(' ','_')+'/'
    create_dir(adr_dir)
    
    scaffold_train_df = pd.read_csv('train_smiles_scaffoldtvt_rs'+str(random_seed)+'.csv')
    scaffold_val_df = pd.read_csv('val_smiles_scaffoldtvt_rs'+str(random_seed)+'.csv')
    scaffold_test_df = pd.read_csv('test_smiles_scaffoldtvt_rs'+str(random_seed)+'.csv')

    train_df = adr_df.merge(scaffold_train_df, how='inner', on='smiles')
    val_df = adr_df.merge(scaffold_val_df, how='inner', on='smiles')
    test_df = adr_df.merge(scaffold_test_df, how='inner', on='smiles')
    
    #Save dataset
    test_df.to_csv(adr_dir +adr.replace(' ','_')+'_test_rs'+str(seed)+'.csv', index=False)
    train_df.to_csv(adr_dir+adr.replace(' ','_')+'_train_rs'+str(seed)+'.csv', index=False)
    val_df.to_csv(adr_dir+adr.replace(' ','_')+'_val_rs'+str(seed)+'.csv', index=False)

    print_imbalance(train_df, 'train', adr)
    print_imbalance(val_df, 'val', adr)
    print_imbalance(test_df, 'test', adr)

    #Permuted Dataset for Baseline Comparison 

    scaffold_train_df = pd.read_csv('train_smiles_scaffoldtvt_rs'+str(random_seed)+'.csv')
    scaffold_val_df = pd.read_csv('val_smiles_scaffoldtvt_rs'+str(random_seed)+'.csv')
    scaffold_test_df = pd.read_csv('test_smiles_scaffoldtvt_rs'+str(random_seed)+'.csv')

    train_df = adr_df.merge(scaffold_train_df, how='inner', on='smiles')
    val_df = adr_df.merge(scaffold_val_df, how='inner', on='smiles')
    test_df = adr_df.merge(scaffold_test_df, how='inner', on='smiles')

    adr_col = adr.replace('_',' ')

    for df in [train_df, val_df, test_df]:
        df[adr+'_shuffled'] = df[adr_col].sample(frac=1).values
        df.drop(adr_col, axis=1, inplace=True)

    #Save dataset
    test_df.to_csv(adr_dir +adr.replace(' ','_')+'_test_rs'+str(seed)+'_shuffled.csv', index=False)
    train_df.to_csv(adr_dir+adr.replace(' ','_')+'_train_rs'+str(seed)+'_shuffled.csv', index=False)
    val_df.to_csv(adr_dir+adr.replace(' ','_')+'_val_rs'+str(seed)+'_shuffled.csv', index=False)