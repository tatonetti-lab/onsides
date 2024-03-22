'''
Data Processing code for OnSIDES application to the prediction of ADRs directly from SMILES strings. 

Input: OnSIDES files, PubChem drug-SMILES conversion, MedDRA HLT conversion file 

Output: SMILES-ADR csv's for 10 selected ADRs

Outline: 
-For drugs found in the OnSIDES database, retrieve SMILES strings from the PubChem API
-Convert ADRs from OnSIDES database to MedDRA HLTs (proprietary file, not included)
-Save dataframes for SMILES-ADR (binary) pairs for 10 selected ADRs 

Author : JK
'''

import pandas as pd
import pickle
import pubchempy as pcp
from time import sleep
from collections import Counter
import matplotlib.pyplot as plt
import seaborn as sns
sns.set_theme(style="white", palette=None)
import random

#Boxed Warnings
bw_df = pd.read_csv('../data/onsides_files_v2.0.0-20221112/boxed_warnings.csv')
#Adverse Reactions 
ar_df = pd.read_csv('../data/onsides_files_v2.0.0-20221112/adverse_reactions.csv')

#Get SMILES strings from PUBCHEM API based on drug name 
def get_smiles_string(df):
    
    smiles_dict = {}
    list_of_drugs = list(set(df['ingredients_names']))
    for name in list_of_drugs:
        #Note: Not sensitive to capitalization 
        results = pcp.get_compounds(name, 'name') 
        
        #Only retain drugs with exactly 1 SMILES string found 
        if len(results) == 1:
            smiles_string = results[0].canonical_smiles 
            smiles_dict[name] = smiles_string 
        sleep(1) 
    
    #Update dataframe with SMILES data 
    smiles_list=[]
    for j in list(df['ingredients_names']):
        if j in list(smiles_dict.keys()):
            smiles_list.append(smiles_dict[j])
        else:
            smiles_list.append(0)
    df['smiles'] = smiles_list
    
    #Subset dataframe to relevant columns and only drugs which were found in PUBCHEM with single SMILES string 
    df = df[['ingredients_names','smiles','pt_meddra_id','pt_meddra_term']].copy() 
    df=df[df['smiles']!=0].copy()

    return df
    
def initial_process(df):

    #Subset to single-ingredient drugs
    df=df[df['num_ingredients']==1].copy()
    df=get_smiles_string(df)
    #Remove duplicated SMILES strings (i.e., SMILES strings with multiple associated drug names)
    #while keeping all possible PT-ADRs
    df.drop('ingredients_names', inplace=True, axis=1)
    df.drop_duplicates(inplace=True)
    df.reset_index(inplace=True, drop=True)
    df.shape
    
    return df

processed_bw_df=initial_process(bw_df)
processed_ar_df=initial_process(ar_df)

meddra_df = pd.read_csv('hlt_to_llt_meddra.csv') #Proprietary meddra file 
#Subset to HLT-PT rows
meddra_df=meddra_df[meddra_df['concept_class_id_desc'].isin(['HLT','PT'])].copy()
meddra_df=meddra_df[meddra_df['concept_class_id_anc'].isin(['HLT','PT'])].copy()
meddra_df.reset_index(inplace=True, drop=True)

def pt_to_hlt(df):
    
    hlt_df = pd.merge(meddra_df, df, right_on='pt_meddra_id',left_on='concept_code_desc', how='inner')
    
    #drop pt's and duplicates 
    hlt_df.drop(['concept_class_id_desc','concept_name_desc','concept_code_desc',
            'concept_class_id_anc','pt_meddra_id','pt_meddra_term'], inplace=True, axis=1)
    hlt_df.drop_duplicates(inplace=True)
    
    return hlt_df

bw_hlt_df = pt_to_hlt(processed_bw_df)
ar_hlt_df = pt_to_hlt(processed_ar_df)

#Combine boxed warnings and adverse reactions dataframes
combined_df = pd.concat([bw_hlt_df, ar_hlt_df])
combined_df.drop_duplicates(inplace=True)
combined_df.reset_index(inplace=True, drop=True)

#Save data
combined_df.to_csv('../data/hlt_finalized/combined_onsides_hlt.csv', index=False)

#Plot distribution of HLTs per SMILES string for combined ONSIDES dataset 
counts = list(combined_df.groupby('smiles').count()['concept_name_anc'])
sns.histplot(counts, bins=20)
plt.title('ADR Distribution')
plt.ylabel('ADRs')
plt.xlabel('SMILES Strings')
plt.savefig('combined_hlt_per_smiles_distribution.png',dpi=900)

#Plot distribution of SMILES per HLT for combined ONSIDES dataset 
sns.set_theme(style="white", palette=None) #to be removed
counts = list(combined_df.groupby('concept_name_anc').count()['smiles'])
sns.histplot(counts, bins=30)
plt.title('SMILES Distribution')
plt.xlabel('ADRs')
plt.ylabel('SMILES Strings')
plt.savefig('combined_smiles_per_hlt_distribution.png',dpi=900)

def get_df(an_adr,df):
    adr_binary_list = []
    full_smiles_list = []
    for string in list(set(df['smiles'])):
        idf = df[df['smiles']==string].copy()
        full_smiles_list.append(string)
        adrs = list(idf['concept_name_anc']) #HLT
        if adr in adrs:
            adr_binary_list.append(1)
        else:
            adr_binary_list.append(0)
            
    final_df = pd.DataFrame({'smiles':full_smiles_list,
                             adr:adr_binary_list})
    final_df.to_csv('../data/combined_adr_data/'+adr.replace(' ','_')+'_binary_df.csv',index=False)
    return final_df

adr_list=['Death and sudden death',
'Ventricular arrhythmias and cardiac arrest',
'Renal failure and impairment',
'Poisoning and toxicity',
'Nausea and vomiting symptoms',
'Cardiac signs and symptoms NEC',
'Sepsis, bacteraemia, viraemia and fungaemia NEC', 
'Heart failure signs and symptoms',
'Heart failures NEC', 
'Central nervous system haemorrhages and cerebrovascular accidents']

for adr in adr_list:
    adr_df = get_df(adr, combined_df)