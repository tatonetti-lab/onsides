"""
construct_application_data.py

Generate application data for all drug labels (~45k) in the same format as the
reference data were generated.

For each mentioned MedDRA term, we grab the nearest ~60 words on either side
and construct a sentence. The trained model will then predict whether the
mentioned term is a drug side effect.

@author Nicholas Tatonetti, Tatonetti Lab, Columbia University
"""

import os
import sys
import csv
import gzip
import tqdm
import json
import time
import random
import argparse

from construct_training_data import get_args
from construct_training_data import load_meddra
from construct_training_data import generate_example
from construct_training_data import section_suffices
from construct_training_data import section_display_names

def main():

    addl_args = [
        {
            'args': ['--dir'],
            'kwargs': {
                'help': 'Path to the directory that contains the parsed SPL files.',
                'type': str,
                'required': True
            }
        },
        {
            'args': ['--medtype'],
            'kwargs': {
                'help': 'otc (over-the-counter) or rx (prescription).',
                'type': str,
                'required': True
            }
        }
    ]

    random.seed(222)

    args, sub_event, sub_nonsense, prepend_event, prepend_source, sections, random_sampled_words = get_args(addl_args)

    llts = load_meddra()
    # if DeepCADRME has been run on these labels, load them here
    deepcadrme = None

    #condensed_name = os.path.split(args.dir)[-1].replace('_','').replace('-','')
    file_prefix = f'sentences-{args.medtype}'

    outfn = os.path.join(args.dir, f'{file_prefix}_method{args.method}_nwords{args.nwords}_clinical_bert_application_set_{args.section}.txt.gz')
    print(f"Application data will be written to {outfn}")

    if os.path.exists(outfn):
        print(f"Feature sentences file already exists at this path. Quitting.")
        sys.exit(0)

    outfh = gzip.open(outfn, 'wt')
    writer = csv.writer(outfh)
    #writer.writerow(['section', 'drug', 'llt_id', 'llt', 'string'])
    # drug = SetID
    writer.writerow(['section', 'drug', 'label_id', 'set_id', 'meddra_id', 'pt_meddra_id', 'source_method', 'pt_meddra_term', 'found_term', 'string'])

    for section in sections:

        section_display_name = section_display_names[section]
        print(f"Parsing section: {section_display_name} ({section})")

        # derive a drug list from the training and testing data provided
        labels_dir_path = None
        if args.medtype == 'rx':
            labels_dir_path = os.path.join(args.dir, 'prescription')
        elif args.medtype == 'otc':
            labels_dir_path = os.path.join(args.dir, 'otc')
        else:
            raise Exception("ERROR: Unexpected medtype provided {args.medtype}, must be either rx or otc.")

        all_drugs = set([fn.replace('.json', '') for fn in os.listdir(labels_dir_path) if fn.endswith('json')])
        print(f"Found {len(all_drugs)} parsed label json files at {labels_dir_path}")

        for drug in tqdm.tqdm(all_drugs):
            #print(f"Generating application data for: {drug}")

            # load text from adverse events section
            json_file_path = os.path.join(labels_dir_path, f'{drug}.json')
            if not os.path.exists(json_file_path):
                raise Exception(f"ERROR: Did not find a parsed adverse event file for {json_file_path}.")

            json_fh = open(json_file_path)
            label_data = json.loads(json_fh.read())
            json_fh.close()

            if not section in label_data['sections']:
                # no text was parsed for this section, move on
                continue

            ar_text = ' '.join(label_data['sections'][section].split()).lower()

            # find all the adverse event terms that are mentioned in the text

            # 1) exact string matches to the meddra term (either PT or LLT)
            # NOTE: llts has both PTs and LLTs because of the structure of the file
            found_terms = list()
            start_time = time.time()
            for meddra_id, (llt_meddra_term, pt_meddra_term, pt_meddra_id) in llts.items():
                #print(f"{meddra_id}, {llt_meddra_term}, {pt_meddra_term}")
                # Method using string splits, Takes approx 0.2s
                if ar_text.find(llt_meddra_term) == -1:
                    continue

                li = ar_text.split(llt_meddra_term)
                start_pos = 0
                for i in range(len(li)-1):
                    # the occurrence of the word is at the end of the previous string
                    start_pos = start_pos + len(li[i])
                    found_terms.append((llt_meddra_term, meddra_id, start_pos, len(llt_meddra_term), pt_meddra_id, pt_meddra_term, 'exact'))


            # print(f"\tFound {len(found_terms)} terms using exact string matches. Took {time.time()-start_time}s.")
            exact_term_list = list(zip(*found_terms))[0]

            if not deepcadrme is None:
                # 2) DeepCADRME mentions, normalized to meddra terms (PT only)
                #    If DeepCADRME found string is exact match for a term (PT or LLT)
                #    then we skip that. It will be handled by the exact matches done above
                drugname = drug
                start_time = time.time()
                if not drugname in deepcadrme:
                    print(f'WARNING: No DeepCADRME output found for {drugname}.')
                else:
                    for term, start, length, match_method, pt_meddra_id, pt_meddra_term in deepcadrme[drugname]:
                        if term in exact_term_list and start.find(',') == -1:
                            # we don't need deepcadrme for this one, we will use the exact string matches
                            continue

                        found_terms.append((term, pt_meddra_id, start_pos, length, pt_meddra_id, pt_meddra_term, 'deepcadrme'))
                # print(f"\tFound {len(found_terms)} terms using both exact and DeepCADRME. Took {time.time()-start_time}s.")

            for found_term, meddra_id, start_pos, length, pt_meddra_id, pt_meddra_term, source_method in found_terms:

                label_text = ar_text
                if source_method == 'deepcadrme':
                    label_text = deepcadrme_ar_text

                # This is for reference methods 12+
                source = None
                if prepend_source:
                    source = source_method

                example_string = generate_example(label_text, found_term, start_pos, length, args.nwords, sub_event, sub_nonsense, prepend_event, random_sampled_words, args.prop_before, source)

                writer.writerow([section, drug, label_data['label_id'], label_data['set_id'], meddra_id, pt_meddra_id, source_method, pt_meddra_term, found_term, example_string])

            ################################################################################
            # This was the previous method we used to do this that only relied on exact
            # string matches. We have refactored the code to allow for different methods of
            # identifying terms. -NPT 9/14/22
            ################################################################################
            # llts_mentioned = set()
            # string_mentioned = set()
            # for llt_id, llt in llts.items():
            #     if ar_text.find(llt) != -1:
            #         llts_mentioned.add(llt_id)
            #         string_mentioned.add(llt)
            #
            #         example_strings = generate_examples(ar_text, llt, args.nwords, sub_event, sub_nonsense, prepend_event, random_sampled_words, args.prop_before)
            #
            #         for example_string in example_strings:
            #             writer.writerow([section, drug, llt_id, llt, example_string])
            ################################################################################

    outfh.close()

if __name__ == '__main__':
    main()
