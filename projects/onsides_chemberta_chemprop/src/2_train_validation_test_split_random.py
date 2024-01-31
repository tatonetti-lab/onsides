'''
This script splits the model input data into train / validation / test sets at random.
Author : JK
'''
import os 
import random
import pandas as pd
from sklearn.model_selection import train_test_split

random_seed_list = [0, 300, 1000]

def create_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

output_dir = 'combined_onsides_tvt_data/'
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
    
    adr_df = pd.read_csv('combined_adr_data/'+adr.replace(' ','_')+'_binary_df.csv')
    adr_dir = output_dir+adr.replace(' ','_')+'/'
    create_dir(adr_dir)
    
    for seed in random_seed_list:

        X_orig = adr_df['smiles']
        y_orig = adr_df[adr] 
        X, X_test, y, y_test = train_test_split(X_orig, y_orig, stratify=y_orig, test_size=0.15, random_state=seed) 

        test_df = pd.DataFrame({'smiles': X_test, adr: y_test})

        X_train, X_val, y_train, y_val = train_test_split(X, y, stratify=y, test_size=0.1765, random_state=seed) 
        train_df = pd.DataFrame({'smiles': X_train, adr: y_train})
        val_df = pd.DataFrame({'smiles': X_val, adr: y_val}) 

        #Save dataset
        test_df.to_csv(adr_dir +adr.replace(' ','_')+'_test_rs'+str(seed)+'.csv', index=False)
        train_df.to_csv(adr_dir+adr.replace(' ','_')+'_train_rs'+str(seed)+'.csv', index=False)
        val_df.to_csv(adr_dir+adr.replace(' ','_')+'_val_rs'+str(seed)+'.csv', index=False)
        
        #Permuted Dataset for Baseline Comparison 
        if seed == 1000:

            for df in [train_df, val_df, test_df]:
                df[adr+'_shuffled'] = df[adr_col].sample(frac=1).values
                df.drop(adr_col, axis=1, inplace=True)
                
            #Save dataset
            test_df.to_csv(adr_dir +adr.replace(' ','_')+'_test_rs'+str(seed)+'_shuffled.csv', index=False)
            train_df.to_csv(adr_dir+adr.replace(' ','_')+'_train_rs'+str(seed)+'_shuffled.csv', index=False)
            val_df.to_csv(adr_dir+adr.replace(' ','_')+'_val_rs'+str(seed)+'_shuffled.csv', index=False)