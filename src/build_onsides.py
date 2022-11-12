"""
build_onsides.py

Script to implement and run the SQL template at load_onsides_db.sql given the
connection details and paramters.

@author Nicholas P. Tatonetti, PhD
"""

import os
import sys
import csv
import gzip
import json
import pickle
import argparse
import datetime

import pandas as pd

from tqdm import tqdm
from datetime import datetime
from collections import defaultdict

section_names = {
    'AR': 'adverse_reactions',
    'BW': 'boxed_warnings'
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--vocab', help='Path to the OMOP Common Data Model Vocabularies', type=str, required=True)
    parser.add_argument('--release', help="Which release version to build the database files for.", type=str, required=True)
    parser.add_argument('--skip-missing', help="Skip missing ata files instead of halting.", action="store_true", default=False)

    args = parser.parse_args()

    if not os.path.exists('releases'):
        os.mkdir('releases')

    release_version_path = os.path.join('releases', args.release)
    if not os.path.exists(release_version_path):
        os.mkdir(release_version_path)

    release_version_date_path = os.path.join(release_version_path, datetime.now().strftime('%Y%m%d'))
    if not os.path.exists(release_version_date_path):
        os.mkdir(release_version_date_path)

    log_fh = open('./logs/build_onsides.log', 'w')

    ###
    # Step 0. Load the concept and concept_ancestor tables
    ###
    print("Loading the OMOP CDM tables...")
    concept = dict()
    if not os.path.exists(os.path.join(args.vocab, 'CONCEPT.csv')):
        raise Exception(f"ERROR: The vocabulary directory {args.vocab} doesn't contain a CONCEPT.csv file.")

    if os.path.exists(os.path.join(args.vocab, 'CONCEPT.pkl')):
        pfh = open(os.path.join(args.vocab, 'CONCEPT.pkl'), 'rb')
        concept = pickle.load(pfh)
        pfh.close()
    else:
        fh = open(os.path.join(args.vocab, 'CONCEPT.csv'))
        reader = csv.reader(fh, delimiter='\t')
        header = next(reader)
        for row in tqdm(reader):
            data = dict(zip(header, row))
            if not data['vocabulary_id'] in ('RxNorm', 'MedDRA'):
                continue

            concept[data['concept_id']] = data
        fh.close()

        pfh = open(os.path.join(args.vocab, 'CONCEPT.pkl'), 'wb')
        pickle.dump(concept, pfh)
        pfh.close()

    concept_ancestor = defaultdict(dict)
    concept_descendant = defaultdict(dict)
    if not os.path.exists(os.path.join(args.vocab, 'CONCEPT_ANCESTOR.csv')):
        raise Exception(f"ERROR: The vocabulary directory {args.vocab} doesn't contain a CONCEPT_ANCESTOR.csv file.")

    if os.path.exists(os.path.join(args.vocab, 'CONCEPT_ANCESTOR.pkl')):
        pfh = open(os.path.join(args.vocab, 'CONCEPT_ANCESTOR.pkl'), 'rb')
        concept_ancestor, concept_descendant = pickle.load(pfh)
        pfh.close()
    else:
        fh = open(os.path.join(args.vocab, 'CONCEPT_ANCESTOR.csv'))
        reader = csv.reader(fh, delimiter='\t')
        header = next(reader)
        for row in tqdm(reader):
            data = dict(zip(header, row))
            if not data['ancestor_concept_id'] in concept:
                continue
            if not data['descendant_concept_id'] in concept:
                continue

            concept_descendant[data['ancestor_concept_id']][data['descendant_concept_id']] = {'min_levels': data['min_levels_of_separation'], 'max_levels': data['max_levels_of_separation']}
            concept_ancestor[data['descendant_concept_id']][data['ancestor_concept_id']] = {'min_levels': data['min_levels_of_separation'], 'max_levels': data['max_levels_of_separation']}
        fh.close()

        pfh = open(os.path.join(args.vocab, 'CONCEPT_ANCESTOR.pkl'), 'wb')
        pickle.dump((concept_ancestor, concept_descendant), pfh)
        pfh.close()

    #####
    # 1. Transform the latest mapping files from pipe delim into csv and gzipped
    #####

    fh = open('./spl.json')
    spl_status = json.loads(fh.read())
    fh.close()

    print(f"Writing latest mappings files to release directory...")
    latest_dfs = dict()

    for file in spl_status['mappings'].keys():

        if not file in ('rxnorm_mappings.zip', 'dm_spl_zip_files_meta_data.zip'):
            continue

        latest = sorted([date for date, info in spl_status['mappings'][file].items() if info['status'] == 'completed'])[-1]

        df = pd.read_csv(spl_status['mappings'][file][latest]['extracted_path'], sep='|')
        latest_dfs[file.replace('.zip', '')] = df
        # print(df.head())

        rfn = os.path.join(release_version_date_path, file.replace('.zip', '.csv.gz'))
        if not os.path.exists(rfn):
            df.to_csv(rfn, index=False)
            print(f"  Wrote {rfn}")
        else:
            print(f"  File {rfn} already exists")

    #####
    # 2. Create deriviative tables and data files
    #####

    print(f"Building map from set_id to rx_cui...")
    setid_rxcui_map = latest_dfs['rxnorm_mappings'].groupby(['SETID', 'RXCUI']).count().reset_index()[['SETID', 'RXCUI']]
    rfn = os.path.join(release_version_date_path, "rxcui_setid_map.csv.gz")

    if not os.path.exists(rfn):
        setid_rxcui_map.to_csv(rfn, index=False)
        print(f"  Wrote {rfn}")
    else:
        print(f"  File {rfn} already exists")

    setid2rxcui = defaultdict(set)

    fh = gzip.open(rfn, 'rt')
    reader = csv.reader(fh)
    header = next(reader)
    for setid, rxcui in reader:
        setid2rxcui[setid].add(rxcui)
    fh.close()

    ofn = os.path.join(release_version_date_path, 'rxnorm_product_to_ingredient.csv.gz')
    rxnorm2ingredients = defaultdict(set)
    # if not os.path.exists(ofn):
    print("Writing out map from products to their ingredients.")
    ofh = gzip.open(ofn, 'wt')
    writer = csv.writer(ofh)
    writer.writerow(['product_rx_cui', 'product_name', 'product_omop_concept_id', 'ingredient_rx_cui', 'ingredient_name', 'ingredient_omop_concept_id'])
    for concept_id, concept_data in concept.items():

        if concept_data['vocabulary_id'] != 'RxNorm':
            continue

        concept_row = [concept_data['concept_code'], concept_data['concept_name'], concept_data['concept_id']]
        for ancestor_id in concept_ancestor[concept_id]:

            if concept[ancestor_id]['vocabulary_id'] != 'RxNorm':
                continue

            if ancestor_id == concept_id:
                continue

            if concept[ancestor_id]['concept_class_id'] != 'Ingredient':
                continue

            ancestor_row = [concept[ancestor_id]['concept_code'], concept[ancestor_id]['concept_name'], concept[ancestor_id]['concept_id']]
            rxnorm2ingredients[concept_data['concept_code']].add(concept[ancestor_id]['concept_id'])
            writer.writerow(concept_row + ancestor_row)
    ofh.close()

    print("Writing out map from labels to their product ingredients.")
    ofn = os.path.join(release_version_date_path, 'ingredients.csv.gz')
    ofh = gzip.open(ofn, 'wt')
    writer = csv.writer(ofh)
    writer.writerow(['set_id', 'ingredient_rx_cui', 'ingredient_name', 'ingredient_omop_concept_id'])

    for setid in setid2rxcui.keys():
        for rxcui in setid2rxcui[setid]:
            if not rxcui in rxnorm2ingredients:
                #print(f"No ingredients found for rxcui {rxcui}")
                continue

            for ingredient_id in rxnorm2ingredients[rxcui]:
                if not ingredient_id in concept:
                    print(f"No concept found for ingredient rxcui {ingredient_id}")
                    continue

                writer.writerow([setid, concept[ingredient_id]['concept_code'], concept[ingredient_id]['concept_name'], concept[ingredient_id]['concept_id']])
    ofh.close()

    #####
    # 3. Collate the compiled files into a single matrix for each section
    #####

    print(f"Loading the parsed SPL labels...")
    spl_path = os.path.join('./data', 'spl', 'rx')

    label_dirs = [d for d in os.listdir(spl_path) if os.path.isdir(os.path.join(spl_path, d))]

    print(f"Found {len(label_dirs)} labels directories.")

    section_compiled_files = defaultdict(list)

    for label_dir in label_dirs:

        compiled_path = os.path.join(spl_path, label_dir, 'compiled')
        version_path = os.path.join(spl_path, label_dir, 'compiled', args.release)
        if not os.path.exists(compiled_path) or not os.path.exists(version_path):
            print(f"WARNING: No compiled subdirectory for {label_dir}. Has create_onsides_datafiles.py been executed?")
            if not args.skip_missing:
                raise Exception("Missing data error.")
            continue

        compiled_files = [f for f in os.listdir(version_path) if f.endswith('.csv.gz')]

        if len(compiled_files) == 0:
            print(f"WARNING: No compiled files available.")
            if not args.skip_missing:
                raise Exception("Missing data error.")
            continue

        print(f"{label_dir}: the following sections have files available:")
        for compiled_file in compiled_files:
            section = compiled_file.split('.')[0]
            print(f"\t{section}")
            section_compiled_files[section].append(os.path.join(version_path, compiled_file))

    print("Building active labels dictionary.")
    active_spl_versions = dict()
    for index, row in tqdm(latest_dfs['dm_spl_zip_files_meta_data'].iterrows()):
        active_spl_versions[row['SETID']] = row['SPL_VERSION']

    for section, compiled_files in section_compiled_files.items():

        print(f"Collating each of the compiled files for section: {section}")

        ofn = os.path.join(release_version_date_path, section_names[section] + "_all_labels.csv.gz")
        ofh = gzip.open(ofn, 'wt')
        writer = csv.writer(ofh)
        header = ['section','zip_id','label_id','set_id','spl_version','pt_meddra_id','pt_meddra_term','pred0','pred1']
        writer.writerow(header)

        ofn2 = os.path.join(release_version_date_path, section_names[section] + "_active_labels.csv.gz")
        ofh2 = gzip.open(ofn2, 'wt')
        writer2 = csv.writer(ofh2)
        header2 = ['set_id','spl_version','pt_meddra_id','pt_meddra_term','num_ingredients','ingredients_rxcuis','ingredients_names']
        writer2.writerow(header2)

        section_by_ingredient = defaultdict(int)
        section_by_ingredient_labels = defaultdict(set)
        section_by_ingredient_meddra_terms = dict()
        section_by_ingredient_drug_names = dict()

        for compiled_file in compiled_files:

            rfh = gzip.open(compiled_file, 'rt')
            reader = csv.reader(rfh)
            _ = next(reader)

            print(f"  Processing {compiled_file}...")
            for row in tqdm(reader):
                data = dict(zip(header, row[1:]))

                # add to all labels file
                writer.writerow(row[1:])


                # add to active labels if it is the current version

                if not data['set_id'] in active_spl_versions:
                    log_fh.write(f"{datetime.now()} WARNING: SetID = {data['set_id']} does not have an active_spl_version available.\n")

                if data['set_id'] in active_spl_versions and int(active_spl_versions[data['set_id']]) == int(data['spl_version']):
                    ingredients = set()
                    for product_rxcui in setid2rxcui[data['set_id']]:
                        for ingredient_concept_id in rxnorm2ingredients[product_rxcui]:
                            ingredients.add( (concept[ingredient_concept_id]['concept_code'], concept[ingredient_concept_id]['concept_name']) )

                    ingredients = sorted(ingredients)
                    if len(ingredients) > 0:
                        ingredients_rxcuis, ingredients_names = zip(*ingredients)
                    else:
                        ingredients_rxcuis = list()
                        ingredients_names = list()

                    ingredients_rxcuis_str = ', '.join(ingredients_rxcuis)
                    ingredients_names_str = ', '.join(ingredients_names)

                    writer2.writerow([data['set_id'], data['spl_version'], data['pt_meddra_id'], data['pt_meddra_term'], len(ingredients_rxcuis), ingredients_rxcuis_str, ingredients_names_str])

                    # save for writing the grouped by ingredients file
                    section_by_ingredient[(ingredients_rxcuis_str, data['pt_meddra_id'])] += 1
                    section_by_ingredient_labels[ingredients_rxcuis_str].add(data['set_id'])
                    section_by_ingredient_meddra_terms[data['pt_meddra_id']] = data['pt_meddra_term']
                    section_by_ingredient_drug_names[ingredients_rxcuis_str] = ingredients_names_str

        ofh.close()
        ofh2.close()

        print(f"  Writing out {section} grouped by ingredients.")
        ofn = os.path.join(release_version_date_path, section_names[section] + ".csv.gz")
        ofh = gzip.open(ofn, 'wt')
        writer = csv.writer(ofh)
        header = ['ingredients_rxcuis', 'ingredients_names', 'num_ingredients', 'pt_meddra_id', 'pt_meddra_term', 'percent_labels', 'num_labels']
        writer.writerow(header)

        for ingredients_rxcuis_str, pt_meddra_id in tqdm(section_by_ingredient.keys()):
            num_labels = section_by_ingredient[ingredients_rxcuis_str]
            ingredients_names_str = section_by_ingredient_drug_names[ingredients_rxcuis_str]
            num_ingredients = len(ingredients_rxcuis_str.split(', '))
            pt_meddra_term = section_by_ingredient_meddra_terms[pt_meddra_id]
            percent_labels = float(section_by_ingredient[(ingredients_rxcuis_str, pt_meddra_id)])/float(num_labels)

            writer.writerow([ingredients_rxcuis_str, ingredients_names_str, num_ingredients, pt_meddra_id, pt_meddra_term, percent_labels, num_labels])

        ofh.close()

        print(f"  Wrote collated {section} to {ofn}.")
        print(f"  Wrote active labels only collated {section} to {ofn2}.")

    log_fh.close()

if __name__ == '__main__':
    main()
