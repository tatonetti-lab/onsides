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
import argparse

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument('--method', help='Choose which example generation method to use. See code for details.', type=int, required=True)
    parser.add_argument('--dir', help='Path to the directory that contains the parsed SPL files. The program expects that there will be a file named *_adverse_reactions.txt for each label.', type=str, required=True)

    args = parser.parse_args()

    sub_event = False
    sub_nonsense = False
    prepend_event = False

    if args.method == 0:
        sub_event = True
        prepend_event = True
    elif args.method == 1:
        sub_event = False
        prepend_event = True
    elif args.method == 2:
        sub_event = True
        prepend_event = False
    elif args.method == 3:
        sub_event = False
        prepend_event = False
    elif args.method == 4:
        sub_event = True
        sub_nonsense = True
        prepend_event = False
    else:
        raise Exception(f"Expected method argument to be an integer value (0, 1, 2, 3, or 4). Got {args.method}")

    # load preferred terms and lower level terms
    meddra_fn = './data/meddra_llt_pt_map.txt'
    meddra_fh = open(meddra_fn)
    reader = csv.reader(meddra_fh, delimiter='|')
    header = next(reader)

    llts = dict()

    for row in reader:
        data = dict(zip(header, row))
        llts[data['llt_concept_id']] = data['llt_concept_name'].lower()

    meddra_fh.close()

    # derive a drug list from the training and testing data provided
    all_drugs = set([fn.split('_')[0] for fn in os.listdir(args.dir) if fn.endswith('adverse_reactions.txt')])

    print(f"Found {len(all_drugs)} total drugs")

    outfn = f'./data/ref{args.method}_clinical_bert_application_set.txt'
    print(f" Application data will be written to {outfn}")

    outfh = open(outfn, 'w')
    writer = csv.writer(outfh)
    writer.writerow(['drug', 'llt_id', 'llt', 'string'])

    for drug in tqdm.tqdm(all_drugs):
        #print(f"Generating application data for: {drug}")

        # load text from adverse events section
        ar_file_path = os.path.join(args.dir, f'{drug}_adverse_reactions.txt')
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

                #print(llt)
                #print(len(ar_text.split(llt)))

                parts = ar_text.split(llt)

                size_of_llt = len(llt.split())
                size_of_parts = 64 - size_of_llt

                if len(parts) == 1:
                    raise Exception("Parts has length of 1 which shouldn't be possible.")

                for i in range(len(parts)-1):
                    # print(parts[i].split()[-1*size_of_parts:])
                    EVENT_STRING = llt
                    if sub_event:
                        EVENT_STRING = 'EVENT'
                    if sub_nonsense:
                        EVENT_STRING = 'YIHFKEHDK'

                    START_STRING = ''
                    if prepend_event:
                        START_STRING = llt

                    example_string = START_STRING + ' ' + ' '.join(parts[i].split()[-1*size_of_parts:] + [EVENT_STRING] + parts[i+1].split()[:size_of_parts])

                    writer.writerow([drug, llt_id, llt, example_string])

                # break

        #print(f"\tNumber of terms mentioned in text: {len(llts_mentioned)}")

    #print(f"Finished generating application set.")

    outfh.close()

if __name__ == '__main__':
    main()
