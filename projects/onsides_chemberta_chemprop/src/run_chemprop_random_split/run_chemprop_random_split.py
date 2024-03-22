'''
This script runs Chemprop on a GPU server. Here, it is for the random train-validation-test split version of the input data. It is run by the shell script shell_run_chemprop_random.sh. 
Author : JK
'''


import chemprop
import pandas as pd
import random
import os 
random.seed(0)

adr_list = ['Death and sudden death',
          'Ventricular arrhythmias and cardiac arrest', 'Renal failure and impairment',
          'Poisoning and toxicity', 'Nausea and vomiting symptoms',
          'Cardiac signs and symptoms NEC',
'Sepsis, bacteraemia, viraemia and fungaemia NEC', 
'Heart failure signs and symptoms', 'Heart failures NEC', 
'Central nervous system haemorrhages and cerebrovascular accidents']

all_adr_list = adr_list

def create_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

        
def run_chemprop(adr, n_folds, random_seed, shuffled=False):
    
    adr = adr.replace(' ','_')
    random_seed = str(random_seed)
    
    output_dir = 'combined_chemprop_output_tvt_random/'+adr+'_output/'
    create_dir(output_dir)

    if shuffled == False:
        spec_output_dir = output_dir+adr+'_rs'+random_seed+'_'+str(n_folds)+'f'
        train_input_file = '../../Target_Selection/combined_onsides_tvt_data/'+adr+'/'+adr+'_train_rs'+random_seed+'.csv' 
        val_input_file = '../../Target_Selection/combined_onsides_tvt_data/'+adr+'/'+adr+'_val_rs'+random_seed+'.csv' 
        test_input_file = '../../Target_Selection/combined_onsides_tvt_data/'+adr+'/'+adr+'_test_rs'+random_seed+'.csv' 

        hyp_dir=spec_output_dir + '/config/' 
        create_dir(hyp_dir) 
        hyp_path = hyp_dir+'model.json'  
        hyperopt_arguments = ['--data_path', train_input_file,
            '--dataset_type', 'classification',
            '--num_iters' ,'3',   
            '--config_save_path', hyp_path]
        hyperopt_args = chemprop.args.HyperoptArgs().parse_args(hyperopt_arguments) 
        chemprop.hyperparameter_optimization.hyperopt(args=hyperopt_args) 
        
        arguments = ['--data_path', train_input_file,
                     '--separate_val_path', val_input_file, 
                     '--separate_test_path', test_input_file,
            '--dataset_type', 'classification',
            '--save_dir', spec_output_dir,
            '--num_folds',str(n_folds),
            '--config_path', hyp_path] 
        args = chemprop.args.TrainArgs().parse_args(arguments)
        mean_score, std_score = chemprop.train.cross_validate(args=args, train_func=chemprop.train.run_training)

    else: #Shuffled
        spec_output_dir = output_dir+str(n_folds)+'f_shuffled'
        train_input_file = '../../Target_Selection/combined_onsides_tvt_data/'+adr+'/'+adr+'_train_rs'+random_seed+'_shuffled.csv' 
        val_input_file = '../../Target_Selection/combined_onsides_tvt_data/'+adr+'/'+adr+'_val_rs'+random_seed+'_shuffled.csv' 
        test_input_file = '../../Target_Selection/combined_onsides_tvt_data/'+adr+'/'+adr+'_test_rs'+random_seed+'_shuffled.csv' 
        
        arguments = ['--data_path', train_input_file,
                     '--separate_val_path', val_input_file, 
                     '--separate_test_path', test_input_file,
                    '--dataset_type', 'classification',
                    '--save_dir', spec_output_dir,
                    '--num_folds',str(n_folds)]
        args = chemprop.args.TrainArgs().parse_args(arguments)
        mean_score, std_score = chemprop.train.cross_validate(args=args, train_func=chemprop.train.run_training)


for adr in all_adr_list:
    print(adr)
    for random_seed in [0,300,1000]: 
        run_chemprop(adr,1, random_seed)
    print('main_finished')
    run_chemprop(adr,1,1000,shuffled=True)
    print('shuffled_finished')
