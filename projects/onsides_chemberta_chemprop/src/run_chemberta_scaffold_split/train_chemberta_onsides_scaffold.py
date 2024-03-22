'''
This script trains ChemBERTa (2 different versions) using the SMILES-ADR data from OnSIDES, and then tests on held-out data. It assumes a scaffold train/validation/test split.
For an example shell script to run train_chemberta_onsides_scaffold.py, see s2_scaffoldtvt.sh.
Author : JK
'''

import numpy as np
import pandas as pd
import torch
import random
import math #new
from transformers import AutoTokenizer, AutoModel, BertForSequenceClassification, RobertaForSequenceClassification
from transformers import LongformerForSequenceClassification, BigBirdForSequenceClassification
from transformers import TrainingArguments, Trainer
import time, os, pickle, glob, shutil, sys 
from datetime import datetime
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, roc_auc_score, average_precision_score, f1_score
from scipy.special import softmax
from collections import Counter 
from eval_metrics_multi_updated import get_metrics
start = time.time()
curr_datetime = datetime.now().strftime('%m-%d-%Y_%Hh-%Mm')

#Set seeds
seed=int(sys.argv[2])
np.random.seed(0) 
torch.manual_seed(0)
random.seed(0)

model_used = sys.argv[3] 
batch_size = int(sys.argv[4]) 
max_tokens = int(sys.argv[5]) 
lr_type = sys.argv[6] 
if lr_type == 'lower_lr':
    learning_rate = .000005
elif lr_type == 'default_lr':
    learning_rate = .00005
else: 
    print('Error: Learning Rate Type not recognized')
print('learning rate:',lr_type)
optim_method = sys.argv[7] 
if optim_method == 'f1':
    optim_type = 'eval_f1'
elif optim_method == 'roc':
    optim_type = 'eval_roc_auc'
elif optim_method == 'f1_weighted': 
    optim_type = 'eval_f1_weighted'
else:
    print('Error: optim_type not recognized')


#Directories
adr_name=sys.argv[1] 

input_suffix = sys.argv[9] 
adr=input_suffix.split('/')[1] 
print(adr)

#Input Data 
input_dir = '../data/'+input_suffix+'/'
if 'shuffle' not in adr_name:
    train_data = pd.read_csv(input_dir+adr+'_train_rs'+str(seed)+'.csv')
    val_data = pd.read_csv(input_dir+adr+'_val_rs'+str(seed)+'.csv')
    test_data = pd.read_csv(input_dir+adr+'_test_rs'+str(seed)+'.csv')
    train_data['label'] = train_data[adr.replace('_',' ')]
    val_data['label'] = list(val_data[adr.replace('_',' ')])
    test_data['label'] = test_data[adr.replace('_',' ')]
else:
    train_data = pd.read_csv(input_dir+adr+'_train_rs'+str(seed)+'_shuffled.csv')
    val_data = pd.read_csv(input_dir+adr+'_val_rs'+str(seed)+'_shuffled.csv')
    test_data = pd.read_csv(input_dir+adr+'_test_rs'+str(seed)+'_shuffled.csv')
    shuffle_col = [col for col in train_data.columns if 'shuffle' in col][0]
    #testing
    print(shuffle_col)
    train_data['label'] = train_data[shuffle_col]
    val_data['label'] = val_data[shuffle_col]
    test_data['label'] = test_data[shuffle_col]


output_suffix = adr_name
root_dir = 'model_output/' + output_suffix+ '_output/'  #n03_brca_output/" #Output Directory
model_output_dir = root_dir +adr_name +'_rs'+str(seed)+'_'+model_used+'_'+str(batch_size)+'bsize'+'_'+str(max_tokens)+'max_tokens_'+lr_type+'_'+optim_method+'_optim_'+str(sys.argv[8]) +'e_' +curr_datetime+ '/'
val_best_model_evaluate_dir = model_output_dir + 'val_best_model_evaluate_tmp/'
for directory in [root_dir, model_output_dir, val_best_model_evaluate_dir]:
    os.makedirs(directory, exist_ok=True)
output_file = adr_name+'_output_rs'+str(seed)+'.txt'
meta_df = pd.DataFrame({'tissue':[adr_name]})
eval_metric = optim_type 
num_classes=2


class Dataset(torch.utils.data.Dataset):
    def __init__(self, encodings, labels=None):
        self.encodings = encodings
        self.labels = labels

    def __getitem__(self, idx):
        item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
        if self.labels:
            item["labels"] = torch.tensor(self.labels[idx])
        return item

    def __len__(self):
        return len(self.encodings["input_ids"])

def compute_metrics(eval_pred):
    raw_pred, labels = eval_pred
    score_pred = softmax(raw_pred, axis=1)[:,1]
    binary_pred = np.argmax(raw_pred, axis=1)
    accuracy = accuracy_score(labels, binary_pred)
    roc = roc_auc_score(labels, score_pred) 
    f1 = f1_score(labels, binary_pred, average = 'macro')
    f1_weighted = f1_score(labels, binary_pred, average = 'weighted')
    return {"accuracy": accuracy, "roc_auc": roc, "f1": f1, "f1_weighted":f1_weighted} 


#Model and Tokenizer
if model_used == 'chemberta':
    tokenizer = AutoTokenizer.from_pretrained("seyonec/ChemBERTa-zinc-base-v1")
    model = RobertaForSequenceClassification.from_pretrained("seyonec/ChemBERTa-zinc-base-v1", num_labels=2)
    print('Chemberta model number of parameters:',model.num_parameters())
elif model_used == 'chemberta10M':
    tokenizer = AutoTokenizer.from_pretrained("DeepChem/ChemBERTa-10M-MTR")
    model = RobertaForSequenceClassification.from_pretrained("DeepChem/ChemBERTa-10M-MTR", num_labels=2)
    print('Chemberta10M model number of parameters:',model.num_parameters())
else:
    print('Model not recognized')


#Input Data
X_train = list(train_data['smiles'])
y_train = list(train_data['label'])
X_val = list(val_data['smiles'])
y_val = list(val_data['label'])
X_test = list(test_data['smiles'])
y_test = list(test_data['label'])

X_train_tokenized = tokenizer(X_train, padding=True, truncation=True,max_length=max_tokens)
X_val_tokenized = tokenizer(X_val, padding=True, truncation=True,max_length=max_tokens)
X_test_tokenized=tokenizer(X_test, padding=True, truncation=True, max_length=max_tokens)

train_dataset = Dataset(X_train_tokenized, y_train)
val_dataset = Dataset(X_val_tokenized, y_val)
test_dataset = Dataset(X_test_tokenized,y_test)

#Record Train/Validation Split across Classes 
print('train:', Counter(y_train).most_common())
print('val:', Counter(y_val).most_common())
pos_prop_train = Counter(y_train).most_common()
pos_prop_val = Counter(y_val).most_common()

#steps dependent on train set size
logging_steps = math.ceil((len(y_train) / batch_size)/5) #logs 5x/epoch
save_steps = math.ceil((len(y_train) / batch_size)/10) #10x/epoch
eval_steps = math.ceil((len(y_train) / batch_size)/10) #10x/epoch
#testing
print(len(y_train),logging_steps, save_steps, eval_steps)

#Training Parameters
training_args_dict = {'save_strategy':'steps',
                      'save_steps':save_steps, 
                      'save_total_limit':2,
                      'num_train_epochs':int(sys.argv[8]), 
                      'logging_steps':logging_steps, 
                      'per_device_train_batch_size':batch_size,
                      'per_device_eval_batch_size':batch_size, 
                      'evaluation_strategy':'steps',
                      'eval_steps':eval_steps, 
                      'load_best_model_at_end':True,
                      'metric_for_best_model':eval_metric,
                      'learning_rate':learning_rate,
                      'learning_rate_type':lr_type,
                      'num_classes':num_classes,
                      'optim_type':optim_type} 

#Fine-tuning 
training_args = TrainingArguments(model_output_dir, 
                                  report_to=None,
                                  seed=0, 
                                  save_strategy = training_args_dict['save_strategy'],
                                  save_steps = training_args_dict['save_steps'], #Change depending on the size of the dataset
                                  save_total_limit = training_args_dict['save_total_limit'], #Deletes all but last X checkpoints - sequentially/chronologically
                                  num_train_epochs = training_args_dict['num_train_epochs'], 
                                  logging_steps = training_args_dict['logging_steps'], #logs training_loss every X steps 
                                  per_device_train_batch_size = training_args_dict['per_device_train_batch_size'], #default = 8
				  per_device_eval_batch_size = training_args_dict['per_device_eval_batch_size'], #default = 8
				  evaluation_strategy = training_args_dict['evaluation_strategy'],
                                  eval_steps = training_args_dict['eval_steps'],
                                  load_best_model_at_end = training_args_dict['load_best_model_at_end'], #default = based on training loss, unless specified below 
                                  metric_for_best_model = training_args_dict['metric_for_best_model'],
                                  learning_rate = training_args_dict['learning_rate'])   

print(training_args_dict) 

trainer = Trainer(model=model,
                  args=training_args,
                  train_dataset=train_dataset,
                  eval_dataset=val_dataset, 
                  compute_metrics=compute_metrics)

#Train
trainer.train()

#Track Run-Time (seconds)
end = time.time()
runtime = round((end - start)/60,3)
print('\nElapsed Time: ', runtime, 'Minutes')

#Save Performance Data
history_list = trainer.state.log_history
pickle.dump(history_list, open(model_output_dir+'state_log_history.p','wb'))

#Training - Performance 
train_info = [a for a in history_list if 'loss' in a.keys()]
train_info_dict = {'step':[a['step'] for a in train_info],
                  'training_loss':[a['loss'] for a in train_info],
                  'epoch':[a['epoch'] for a in train_info],
                  'learning_rate':[a['learning_rate'] for a in train_info]}
train_info_df=pd.DataFrame(train_info_dict)

#Evaluation - Performance
e_info = [a for a in history_list if 'eval_loss' in a.keys()]
e_info_dict = {key:[a[key] for a in e_info] for key in e_info[0].keys()}
e_info_df=pd.DataFrame(e_info_dict)
train_info_df.to_csv(model_output_dir+'train_history.csv',index=False)
e_info_df.to_csv(model_output_dir+'eval_history.csv',index=False)
history_df = e_info_df.merge(train_info_df, on=['step','epoch'],how='outer')
history_df.sort_values(by='step',inplace=True)
history_df.to_csv(model_output_dir+'full_history.csv',index=False)

#Identify Best_model 
model_checkpoints = glob.glob(model_output_dir+'checkpoint*')
checkpoint_steps = [int(a.split('-')[-1]) for a in model_checkpoints]
checkpoint_data = [a for a in history_list if ((eval_metric in a.keys()) and (a['step'] in checkpoint_steps))]
eval_full_list = [a[eval_metric] for a in checkpoint_data]
best_checkpoint_steps = [a['step'] for a in checkpoint_data if a[eval_metric] == max(eval_full_list)]

#If multiple checkpoints have the same eval_metric, choose the chronologically later one (trained on more data)
best_model_checkpoint = [a for a in model_checkpoints if str(max(best_checkpoint_steps)) == a.split('-')[-1]][0]
print(best_model_checkpoint)

#Save best_model metadata 
info_for_test_evaluation = {'best_model_checkpoint':best_model_checkpoint,
                            'model_output_dir':model_output_dir}
pickle.dump(info_for_test_evaluation, open(model_output_dir+'info_for_test_evaluation.p','wb')) 

#Print Best Model metrics - Performance on validation set 
print('Validation - Best Model Performance')

if model_used == 'chemberta':
    best_model = RobertaForSequenceClassification.from_pretrained(best_model_checkpoint, num_labels=num_classes, local_files_only=True)
    print('Chemberta eval')
elif model_used == 'chemberta10M':
    best_model = RobertaForSequenceClassification.from_pretrained(best_model_checkpoint, num_labels=num_classes, local_files_only=True)
    print('Chemberta10M eval')
else:
    print('Model not recognized')

best_trainer = Trainer(model=best_model, compute_metrics=compute_metrics,
    args=TrainingArguments(output_dir = val_best_model_evaluate_dir)) 

y_pred, _,_  = best_trainer.predict(Dataset(X_val_tokenized))
ac,   au_roc, pred_pos_dict, actual_pos_dict, f1_micro, f1_macro, f1_weighted  = get_metrics(y_pred, y_val, 
                                                                                          output_dir=model_output_dir, 
                                                                                          seed = seed, trainval_csv =input_dir+input_suffix, 
                                                                                          suffix='val_best_model')

print('\nAU-ROC ', round(au_roc,4))
print('validation evaluation')
print(round(best_trainer.evaluate(val_dataset)['eval_roc_auc'],4))

print('held-out test set evaluation')
test_roc = round(best_trainer.evaluate(test_dataset)['eval_roc_auc'],4)
print(test_roc)

#Update meta_df
meta_df['runtime_min'] = [runtime]
#best model steps
meta_df['best_model_steps'] = [best_model_checkpoint.split('-')[-1]]
meta_df['best_model_dir'] = [best_model_checkpoint]
meta_df['pos_prop_train'] = [pos_prop_train]
meta_df['pos_prop_val'] = [pos_prop_val]
meta_df['save_steps'] = [training_args_dict['save_steps']]
meta_df['num_train_epochs'] = [training_args_dict['num_train_epochs']]
meta_df['logging_steps'] = [training_args_dict['logging_steps']]
meta_df['per_device_train_batch_size'] = [training_args_dict['per_device_train_batch_size']]
meta_df['per_device_eval_batch_size'] = [training_args_dict['per_device_eval_batch_size']]
meta_df['eval_steps'] = [training_args_dict['eval_steps']]
meta_df['learning_rate_type'] = [lr_type]
meta_df['learning_rate'] = [learning_rate]
meta_df['val_accuracy_bestmodel'] = [ac]
meta_df['val_au_roc_bestmodel'] = [au_roc]
meta_df['test_au_roc_bestmodel'] = [test_roc]
meta_df['random_seed'] = [seed]
meta_df['n_pred_pos'] = [pred_pos_dict] 
meta_df['n_actual_pos'] = [actual_pos_dict] 
meta_df['num_classes']=[num_classes]
meta_df['optim_type']=optim_type

#Save meta_df to csv
meta_df.to_csv(model_output_dir+adr_name+'_rs'+str(seed)+'_meta_df.csv',index=False)
meta_df.to_csv('onsides_scaffold_split/'+adr_name+'_rs'+str(seed)+'_meta_df.csv',index=False)

#Delete checkpoint that is not the best model (just the last checkpoint) 
non_best_model_checkpoint = [a for a in model_checkpoints if str(max(best_checkpoint_steps)) != a.split('-')[-1]][0]
shutil.rmtree(non_best_model_checkpoint)
print('Non-Best-Model checkpoint deleted')
