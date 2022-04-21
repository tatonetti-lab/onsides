"""
compile_results.py
Convert raw results files and reference data into a nice data frame for analysis
and plotting.

@author Nicholas Tatonetti, Tatonetti Lab, Columbia University
"""

import os
import csv
import sys
import argparse
import pandas as pd

from fit_clinicalbert import split_train_val_test

section_display_names = {
    'AR': 'ADVERSE REACTIONS',
    'BW': 'BOXED WARNINGS',
    'WP': 'WARNINGS AND PRECAUTIONS'
}

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--results', type=str, required=True, nargs='+', help='Path to results file(s) to generate the data tables from.')
    parser.add_argument('--examples', help='Path to the example file that corresponds to the results file (e.g. the reference set file).', type=str, required=True)

    args = parser.parse_args()

    # check the inputs
    for resultspath in args.results:
        fnnoext = os.path.split(resultspath)[-1].split('.')[0]
        if len(fnnoext.split('_')) != 8:
            raise Exception("ERROR: Results filename ({resultspath}) not in format expected: {prefix}_{refset}_{np_random_seed}_{random_state}_{EPOCHS}_{LR}_{max_length}_{batch_size}.pth")

    if len(set([rp.replace('test', '').replace('valid', '').replace('train', '') for rp in args.results])) > 1:
        raise Exception("ERROR: Results files should match in all paramters besides the split (train/valid/test).")

    # since the files are the same except for the split, we grab all the parameters
    # from the first file in the list.
    fnnoext = os.path.split(args.results[0])[-1].split('.')[0]
    prefix = fnnoext.split('_')[0]
    prefix_nosplit = '-'.join(prefix.split('-')[:-1])
    refset = fnnoext.split('_')[1]
    refmethod, refsection, refnwords = refset.split('-')

    np_random_seed = int(fnnoext.split('_')[2])
    random_state = int(fnnoext.split('_')[3])
    EPOCHS = int(fnnoext.split('_')[4])
    LR = fnnoext.split('_')[5]
    max_length = fnnoext.split('_')[6]
    batch_size = fnnoext.split('_')[7]

    examplespath = args.examples
    dfex = pd.read_csv(examplespath)

    print(f"Loding reference examples file...", flush=True)
    print(f" ex.shape (before split): {dfex.shape}")

    df_ref = dict()
    df_ref['train'], df_ref['valid'], df_ref['test'] = split_train_val_test(dfex, np_random_seed)

    dataframes = list()
    for resultspath in args.results:
        fnnoext = os.path.split(resultspath)[-1].split('.')[0]
        prefix = fnnoext.split('_')[0]
        split = prefix.split('-')[3]

        print(f"Processing {resultspath}...")
        print(f" prefix: {prefix}")
        print(f" split: {split}")
        print(f" refset: {refset}")
        print(f" np_random_seed: {np_random_seed}")
        print(f" random_state: {random_state}")
        print(f" EPOCHS: {EPOCHS}")
        print(f" LR: {LR}")
        print(f" max_length: {max_length}")
        print(f" batch_size: {batch_size}")

        res = pd.read_csv(resultspath, header=None, names=['Pred0', 'Pred1'])

        print(f"Loading results file...", flush=True)
        print(f" res.shape: {res.shape}")

        ex = df_ref[split]

        if ex.shape[0] != res.shape[0]:
            raise Exception("ERROR: Results file and examples file have different numbers of rows.")

        print(f"Concatenating (colwise) results file to examples file...", flush=True)
        for col in ex.columns:
            if col == 'string':
                continue
            res[col] = list(ex[col])

        print(f"Grouping predictions by drug label and adverse event term, and taking the mean prediction score...", flush=True)
        df_grouped = res.groupby(by=['drug', 'llt_id', 'class']).mean().reset_index()

        # For drug, event pairs that couldn't be scored we add them with 0's
        # otherwise we would way overestimate our total recall
        refset_fn = './data/200_manual_annotations_csv/FinalReferenceStandard200Labels.csv'
        refset_fh = open(refset_fn)
        reader = csv.reader(refset_fh, delimiter='|')
        header = next(reader)

        gold_standard = set()

        uniq_drugs = set(df_grouped['drug'])

        for row in reader:
            data = dict(zip(header, row))

            if data['LLT ID'] == '':
                continue

            if data['Section Display Name'] != section_display_names[refsection]:
                # print(data['Section Display Name'])
                continue

            if not data['Drug Name'] in uniq_drugs:
                continue

            try:
                gold_standard.add((data['Drug Name'], int(data['LLT ID'])))
            except ValueError:
                raise Exception(f"Failed on row: {data}")

        refset_fh.close()
        print(f"Loaded manually annotated examples for drug, event pairs: {len(gold_standard)}")

        df_grouped['scored'] = 'scored'

        scored_pairs = set()
        for index, row in df_grouped.iterrows():
            scored_pairs.add((row['drug'], int(row['llt_id'])))

        data_to_append = list()
        #print(len(scored_pairs))
        #print(list(scored_pairs)[:10])

        #print(len(gold_standard))
        #print(list(gold_standard)[:10])

        print(f"Found {len(gold_standard-scored_pairs)} drug, event pairs that were not scored.")
        #print(list(gold_standard-scored_pairs)[:10])

        for d, e in (gold_standard-scored_pairs):
            data_to_append.append((d, e, 0.0, 0.0, 'is_event', 'not_scored'))

        drugs, llt_ids, pred1s, pred0s, classes, scoreds = zip(*data_to_append)

        df_grouped = pd.concat([df_grouped,pd.DataFrame({
            'drug': drugs,
            'llt_id': llt_ids,
            'Pred1': pred1s,
            'Pred0': pred0s,
            'class': classes,
            'scored': scoreds})], ignore_index=True, sort=False)



        print(f"Adding column to indicate split ({split})")
        df_grouped['split'] = split

        print(f"Final grouped dataframe has size: {df_grouped.shape}")

        dataframes.append(df_grouped)

    print(f"Concatenating data frames for each split...")
    df_concat = dataframes[0]
    for df in dataframes[1:]:
        df_concat = pd.concat([df_concat, df], ignore_index=True)

    df_concat["llt_id"] = [int(llt_id) for llt_id in df_concat["llt_id"]]
    # print(df_concat.dtypes)
    grouped_filename = f"grouped-{prefix_nosplit}_{refset}_{np_random_seed}_{random_state}_{EPOCHS}_{LR}_{max_length}_{batch_size}.csv"
    print(f"Saving concatenated data frame {df_concat.shape} to file: {grouped_filename}")
    df_concat.to_csv(os.path.join('./results/', grouped_filename))