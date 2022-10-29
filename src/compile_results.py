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

from fit_clinicalbert import split_train_val_test, load_reference_data

from construct_training_data import section_names2codes

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--results', type=str, required=True, nargs='+', help='Path to results file(s) to generate the data tables from.')
    parser.add_argument('--examples', type=str, required=True, help='Path to the example file that corresponds to the results file (e.g. the reference set file).')
    parser.add_argument('--group-function', type=str, default='mean', help="Function to use to aggregate predictions by drug, event across trainnig examples.")
    parser.add_argument('--base-dir', type=str, default='.')

    args = parser.parse_args()
    if not args.group_function in ('mean', 'max', 'median', 'min'):
        raise Exception(f"ERROR: Unexpected value ({args.group_function}) provided for --group-function. Can only be one of mean, max, median, or min")

    # check the inputs
    for resultspath in args.results:
        fnnoext = os.path.splitext(os.path.split(resultspath)[-1])[0]
        if len(fnnoext.split('_')) != 8:
            raise Exception(f"ERROR: Results filename ({resultspath}) not in format expected: {prefix}_{refset}_{np_random_seed}_{split_method}_{EPOCHS}_{LR}_{max_length}_{batch_size}.pth")

    if len(set([rp.replace('test', '').replace('valid', '').replace('train', '') for rp in args.results])) > 1:
        raise Exception("ERROR: Results files should match in all paramters besides the split (train/valid/test).")

    # since the files are the same except for the split, we grab all the parameters
    # from the first file in the list.
    fnnoext = os.path.splitext(os.path.split(resultspath)[-1])[0]
    prefix = fnnoext.split('_')[0]
    prefix_nosplit = '-'.join(prefix.split('-')[:-1])
    refset = fnnoext.split('_')[1]
    refmethod, refsection, refnwords, refsource = refset.split('-')

    valid_section_codes = None
    if refsection == 'ALL':
        valid_section_codes = ('AR', 'BW', 'WP')
    elif refsection == 'ARBW':
        valid_section_codes = ('AR', 'BW')
    else:
        valid_section_codes = (refsection,)

    np_random_seed = int(fnnoext.split('_')[2])
    split_method = fnnoext.split('_')[3]
    EPOCHS = int(fnnoext.split('_')[4])
    LR = fnnoext.split('_')[5]
    max_length = fnnoext.split('_')[6]
    batch_size = fnnoext.split('_')[7]

    dfex = load_reference_data(args.examples, refsource)

    print(f"Loding reference examples file...", flush=True)
    print(f" ex.shape (before split): {dfex.shape}")
    
    df_ref = dict()
    df_ref['train'], df_ref['valid'], df_ref['test'] = split_train_val_test(dfex, np_random_seed, split_method)
    # dfex['drug'] = dfex['drug'].str.lower()

    dataframes = list()
    for resultspath in args.results:
        fnnoext = os.path.splitext(os.path.split(resultspath)[-1])[0]
        prefix = fnnoext.split('_')[0]
        split = prefix.split('-')[3]

        print(f"Processing {resultspath}...")
        print(f" prefix: {prefix}")
        print(f" split: {split}")
        print(f" refset: {refset}")
        print(f" np_random_seed: {np_random_seed}")
        print(f" split_method: {split_method}")
        print(f" EPOCHS: {EPOCHS}")
        print(f" LR: {LR}")
        print(f" max_length: {max_length}")
        print(f" batch_size: {batch_size}")

        res = pd.read_csv(resultspath, header=None, names=['Pred0', 'Pred1'])

        print(f"Loading results file...", flush=True)
        print(f" res.shape: {res.shape}")

        ex = df_ref[split]
        print(f" ex.shape : {ex.shape}")

        if ex.shape[0] != res.shape[0]:
            raise Exception("ERROR: Results file and examples file have different numbers of rows.")

        print(f"Concatenating (colwise) results file to examples file...", flush=True)
        for col in ex.columns:
            if col == 'string':
                continue
            res[col] = list(ex[col])

        print(f"Grouping predictions by drug label and adverse event term, and taking the mean prediction score...", flush=True)

        if not 'section' in res:
            res['section'] = refsection

        groupby_cols = ['section', 'drug', 'pt_meddra_id', 'class']
        # print(res)

        if args.group_function == 'mean':
            df_grouped = res.groupby(by=groupby_cols).mean().reset_index()
        elif args.group_function == 'max':
            df_grouped = res.groupby(by=groupby_cols).max().reset_index()
        elif args.group_function == 'median':
            df_grouped = res.groupby(by=groupby_cols).median().reset_index()
        elif args.group_function == 'min':
            df_grouped = res.groupby(by=groupby_cols).min().reset_index()
        else:
            raise Exception("ERROR. Should not be able to get to this code.")

        df_grouped = df_grouped.drop('meddra_id', axis=1)

        # print(df_grouped)

        # For drug, event pairs that couldn't be scored we add them with 0's
        # otherwise we would way overestimate our total recall
        refset_fn = './data/200_manual_annotations_csv/FinalReferenceStandard200Labels.csv'
        refset_fh = open(refset_fn)
        reader = csv.reader(refset_fh, delimiter='|')
        header = next(reader)

        gold_standard = set()

        uniq_drugs = set(df_grouped['drug'].str.upper())

        for row in reader:
            data = dict(zip(header, row))

            if data['PT ID'] == '':
                continue

            if not section_names2codes[data['Section Display Name']] in valid_section_codes:
                continue

            section_code = section_names2codes[data['Section Display Name']]

            if not data['Drug Name'].upper() in uniq_drugs:
                continue

            try:
                gold_standard.add((section_code, data['Drug Name'].upper(), int(data['PT ID'])))
            except ValueError:
                raise Exception(f"Failed on row: {data}")

        refset_fh.close()
        print(f"Loaded manually annotated examples for drug, event pairs: {len(gold_standard)}")

        df_grouped['scored'] = 'scored'

        scored_pairs = set()
        for index, row in df_grouped.iterrows():
            scored_pairs.add((row['section'], row['drug'].upper(), int(row['pt_meddra_id'])))

        data_to_append = list()
        #print(len(scored_pairs))
        #print(list(scored_pairs)[:10])

        #print(len(gold_standard))
        #print(list(gold_standard)[:10])

        print(f"Found {len(gold_standard-scored_pairs)} drug, event pairs that were not scored.")
        #print(list(gold_standard-scored_pairs)[:10])

        for s, d, e in (gold_standard-scored_pairs):
            data_to_append.append((s, d, e, 0.0, 0.0, 'is_event', 'not_scored'))

        sections, drugs, pt_meddra_ids, pred1s, pred0s, classes, scoreds = zip(*data_to_append)

        df_grouped = pd.concat([df_grouped,pd.DataFrame({
            'section': sections,
            'drug': drugs,
            'pt_meddra_id': pt_meddra_ids,
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

    df_concat["pt_meddra_id"] = [int(meddra_id) for meddra_id in df_concat["pt_meddra_id"]]
    # print(df_concat.dtypes)
    grouped_filename = f"grouped-{args.group_function}-{prefix_nosplit}_{refset}_{np_random_seed}_{split_method}_{EPOCHS}_{LR}_{max_length}_{batch_size}.csv"
    print(f"Saving concatenated data frame {df_concat.shape} to file: {grouped_filename}")
    df_concat.to_csv(os.path.join(args.base_dir, 'results', grouped_filename))
