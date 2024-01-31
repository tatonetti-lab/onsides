'''
This script is used for evaluating the best-performing model on either the validation set or the test set. 
This assumes a binary target. 
Author : JK
'''

from sklearn.metrics import accuracy_score, roc_auc_score, average_precision_score, roc_curve, precision_recall_curve, f1_score
from scipy.special import softmax
from sklearn.metrics import confusion_matrix
from sklearn.preprocessing import label_binarize
from itertools import cycle
import matplotlib.pyplot as plt 
import numpy as np
import pandas as pd
import seaborn as sns 
import pickle 
import math
from sklearn.model_selection import train_test_split

def get_metrics(raw_pred, y_true, output_dir,  seed, trainval_csv, suffix=''):

    y_pred = np.argmax(raw_pred, axis=1)
    ac = accuracy_score(y_true, y_pred)
    f1_micro = f1_score(y_true, y_pred, average='micro')
    f1_macro = f1_score(y_true, y_pred, average='macro')
    f1_weighted = f1_score(y_true, y_pred, average='weighted')

    softmax_array = softmax(raw_pred, axis=1) 
    print('raw_pred',raw_pred)
    print('softmaxarray', softmax_array)

    raw_df = pd.DataFrame({'y_pred':y_pred,
                            'y_true':y_true})
    for class_label in range(raw_pred.shape[1]): 
        raw_df['raw_class_'+str(class_label)] = list(raw_pred[:,class_label])
        raw_df['softmax_class_'+str(class_label)] = list(softmax_array[:,class_label])    
    raw_df.to_csv(output_dir+'raw_predictions_'+suffix+'.csv', index=False)

    classes = list(range(raw_pred.shape[1]))
    bin_true = label_binarize(y_true, classes=classes)
    eval_df = pd.DataFrame({'Accuracy':[ac]})
    au_roc = round(roc_auc_score(y_true, softmax_array[:,1]),4)
    eval_df['auroc'] = au_roc
    pred_pos_dict, actual_pos_dict = {},{}
    for class_label in range(raw_pred.shape[1]):
        npp = len([a for a in y_pred if a == class_label])
        ap = len([a for a in y_true if a == class_label])
        pred_pos_dict[class_label] = npp
        actual_pos_dict[class_label] = ap
        eval_df['n_pred_pos_class_'+str(class_label)] = npp
        eval_df['n_actual_pos_class_'+str(class_label)] = ap
    
    eval_df['f1_micro'] = f1_micro
    eval_df['f1_macro'] = f1_macro
    eval_df['f1_weighted'] = f1_weighted 
    eval_df.to_csv(output_dir+'eval_metrics_'+suffix+'.csv', index=False)

    return ac, au_roc, pred_pos_dict, actual_pos_dict, f1_micro, f1_macro, f1_weighted

