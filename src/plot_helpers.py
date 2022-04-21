"""
plot_helpers.py

Functions to help with plotting and analysis of results.

@author Nicholas Tatonetti, Tatonetti Lab, Columbia University

"""
import os
import csv
import sys
import random
import pandas as pd
import numpy as np
from sklearn import metrics

def prdata(labels, preds, f1_threshold = None):
    precision, recall, thresholds = metrics.precision_recall_curve(labels, preds)
    numerator = 2 * recall * precision
    denom = recall + precision
    f1_scores = np.divide(numerator, denom, out=np.zeros_like(denom), where=(denom!=0))

    if not f1_threshold is None:
        # if testing, we use the override f1_threshold (usually from validation set)
        tthresh = thresholds[np.argmin(np.abs(thresholds-f1_threshold))]
        max_f1 = f1_scores[np.argmin(np.abs(thresholds-f1_threshold))]
        max_f1_precision = precision[np.argmin(np.abs(thresholds-f1_threshold))]
        max_f1_recall = recall[np.argmin(np.abs(thresholds-f1_threshold))]
        max_f1_thresh = f1_threshold
    else:
        max_f1_thresh = thresholds[np.argmax(f1_scores)]
        max_f1 = np.max(f1_scores)
        max_f1_precision = precision[np.argmax(f1_scores)]
        max_f1_recall = recall[np.argmax(f1_scores)]

    return {
        'precision': precision,
        'recall': recall,
        'max_f1': max_f1,
        'max_f1_threshold': max_f1_thresh,
        'max_f1_precision': max_f1_precision,
        'max_f1_recall': max_f1_recall,
        'pr_auc': metrics.auc(recall, precision)
    }

def rocdata(labels, preds, f1_threshold):
    fpr, tpr, roc_thresholds = metrics.roc_curve(labels, preds)
    max_f1_tpr = tpr[np.argmin(np.abs(roc_thresholds-f1_threshold))]
    max_f1_fpr = fpr[np.argmin(np.abs(roc_thresholds-f1_threshold))]

    return {
        'fpr': fpr,
        'tpr': tpr,
        'max_f1_fpr': max_f1_fpr,
        'max_f1_tpr': max_f1_tpr,
        'roc_auc': metrics.auc(fpr, tpr)
    }
