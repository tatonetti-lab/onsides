import os
import sys
import torch
import random
import argparse
import pandas as pd
import numpy as np

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--model', type=str, required=True)

    args = parser.parse_args()

    model_filepath = args.model
    model_file = os.path.split(model_filepath)[-1]

    print(f"Loading model from {model_file}")
    fnnoext = os.path.split(model_file)[-1].split('.')[0]

    if not len(fnnoext.split('_')) in (6, 8):
        raise Exception("Model filename not in format expected: {prefix}_{refset}_{np_random_seed}_{random_state}_{EPOCHS}_{LR}.pth or {prefix}_{refset}_{np_random_seed}_{random_state}_{EPOCHS}_{LR}_{MAX_LENGTH}_{BATCH_SIZE}.pth")

    refset = int(fnnoext.split('_')[1])
    np_random_seed = int(fnnoext.split('_')[2])
    random_state = int(fnnoext.split('_')[3])
    EPOCHS = int(fnnoext.split('_')[4])
    LR = fnnoext.split('_')[5]

    if len(fnnoext.split('_')) == 8:
        max_length = int(fnnoext.split('_')[6])
        batch_size = int(fnnoext.split('_')[7])
    else:
        max_length = 128
        batch_size = 128

    prefix = fnnoext.split('_')[0]

    print(f" prefix: {prefix}")
    print(f" refset: {refset}")
    print(f" np_random_seed: {np_random_seed}")
    print(f" random_state: {random_state}")
    print(f" EPOCHS: {EPOCHS}")
    print(f" LR: {LR}")
    print(f" max_length: {max_length}")
    print(f" batch_size: {batch_size}")

    sys.path.append(os.path.abspath("./src"))
    import fit_clinicalbert as cb

    model = cb.ClinicalBertClassifier()
    model.load_state_dict(torch.load(model_filepath))

    # loading and re-splitting the data
    datapath = f'./data/ref{refset}_clinical_bert_reference_set.txt'
    df = pd.read_csv(datapath)

    # randomly select by drug/label
    druglist = sorted(set(df['drug']))

    random.seed(np_random_seed)
    random.shuffle(druglist)

    drugs_train, drugs_val, drugs_test = np.split(druglist, [int(0.8*len(druglist)), int(0.9*len(druglist))])

    print(f"Split labels in train, val, test by drug:")
    print(len(drugs_train), len(drugs_val), len(drugs_test))

    df_train = df[df['drug'].isin(drugs_train)]
    df_val = df[df['drug'].isin(drugs_val)]
    df_test = df[df['drug'].isin(drugs_test)]

    print(len(df_train), len(df_val), len(df_test))

    print(f"Evaluating testing data...")
    outputs = cb.evaluate(model, df_test, max_length, batch_size)
    npoutputs = [x.cpu().detach().numpy() for x in outputs]
    predictions = np.vstack(npoutputs)

    file_parameters = f'{refset}_{np_random_seed}_{random_state}_{EPOCHS}_{LR}_{max_length}_{batch_size}'

    np.savetxt(f'./results/{prefix}-test_{file_parameters}.csv', predictions, delimiter=',')

    print(f"Evaluating validation data...")
    outputs = cb.evaluate(model, df_val, max_length, batch_size)
    npoutputs = [x.cpu().detach().numpy() for x in outputs]
    predictions = np.vstack(npoutputs)

    np.savetxt(f'./results/{prefix}-valid_{file_parameters}.csv', predictions, delimiter=',')

    print(f"Evaluating training data...")
    outputs = cb.evaluate(model, df_train, max_length, batch_size)
    npoutputs = [x.cpu().detach().numpy() for x in outputs]
    predictions = np.vstack(npoutputs)

    np.savetxt(f'./results/{prefix}-train_{file_parameters}.csv', predictions, delimiter=',')
