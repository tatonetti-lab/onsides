"""
construct_application_data.py

Generate applicationd data for all drug labels (~45k) in the same format as the
reference data were generated.

For each mentioned MedDRA term, we grab the nearest ~60 words on either side
and construct a sentence. The trained model will then predict whether the
mentioned term is a drug side effect.

@author Nicholas Tatonetti, Tatonetti Lab, Columbia University
"""

import os
import sys
import csv
import tqdm
import random
import argparse

from construct_training_data import get_args
from construct_training_data import load_meddra
from construct_training_data import generate_examples

def main():

    addl_args = [
        {
            'args': ['--dir'],
            'kwargs': {
                'help': 'Path to the directory that contains the parsed SPL files.',
                'type': str,
                'required': True
            }
        }
    ]

    random.seed(222)

    args, sub_event, sub_nonsense, prepend_event, sections, random_sampled_words = get_args(addl_args)

    llts = load_meddra()

    file_prefix = os.path.split(args.dir)[-1]

    print(f"Found {len(all_drugs)} total drugs")

    outfn = f'./data/{file_prefix}_method{args.method}_nwords{args.nwords}_clinical_bert_application_set_{args.section}.txt'
    print(f" Application data will be written to {outfn}")

    outfh = open(outfn, 'w')
    writer = csv.writer(outfh)
    writer.writerow(['section', 'drug', 'llt_id', 'llt', 'string'])

    for section in sections:
        suffix = section_suffices[section]
        section_display_name = section_display_names[section]
        print(f"Parsing section: {section_dislay_name} ({section})")

        # derive a drug list from the training and testing data provided
        all_drugs = set([fn.split('_')[0] for fn in os.listdir(args.dir) if fn.endswith(suffix)])
        
        for drug in tqdm.tqdm(all_drugs):
            #print(f"Generating application data for: {drug}")

            # load text from adverse events section
            ar_file_path = os.path.join(args.dir, f'{drug}_{suffix}')
            if not os.path.exists(ar_file_path):
                raise Exception(f"Did not file an adverse event file for {ar_file_path}")

            ar_fh = open(ar_file_path)
            ar_text = ' '.join(ar_fh.read().split()).lower()

            #print(f"\tNumber of words in ADVERSE EVENTS text: {len(ar_text.split())}")

            # find all the llts that are mentioned in the text

            llts_mentioned = set()
            string_mentioned = set()

            for llt_id, llt in llts.items():
                if ar_text.find(llt) != -1:
                    llts_mentioned.add(llt_id)
                    string_mentioned.add(llt)

                    example_strings = generate_examples(ar_text, llt, args.nwords, sub_event, sub_nonsense, prepend_event, random_sampled_words, args.prop_before)

                    for example_string in example_strings:
                        writer.writerow([drug, llt_id, llt, example_string])

    outfh.close()

if __name__ == '__main__':
    main()
