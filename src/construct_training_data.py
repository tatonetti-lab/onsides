"""
construct_training_data.py

Using the manual annotations from Demmer-Fushman et al. Scientific Data
construct a training set for use in training a classifier.

For each mentioned MedDRA term, the classifier will predict whether or not
the term will be manually annotated as an adverse event for the drug.

@author Nicholas Tatonetti, Tatonetti Lab, Columbia University
"""

import os
import sys
import csv
import argparse

def get_args(addl_args = None):

    parser = argparse.ArgumentParser()
    parser.add_argument('--method', type=int, required=True)
    parser.add_argument('--nwords', help='The number of words to grab from either side of the event mention to generate the training example', type=int, default=64)
    parser.add_argument('--section', help='Designate which section of the label to parse. Options are AR (adverse reactions), BW (boxed warnings), or WP (warnings and precautions)', type=str, default='AR')

    if not addl_args is None and type(addl_args) is list:
        for addl_arg in addl_args:
            parser.add_argument(*addl_arg['args'], **addl_arg['kwargs'])

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

    suffix = None
    section_display_name = None
    if args.section == 'AR':
        # ADVERSE REACTIONS
        suffix = 'adverse_reactions.txt'
        section_display_name = 'ADVERSE REACTIONS'
    elif args.section == 'BW':
        # BLACK BOX WARNINGS
        suffix = 'boxed_warnings.txt'
        section_display_name = 'BOXED WARNINGS'
    elif args.section == 'WP':
        # WARNINGS AND PRECAUTIONS
        suffix = 'warnings_and_precautions.txt'
        section_display_name = 'WARNINGS AND PRECAUTIONS'
    else:
        raise Exception(f"ERROR: Unknown section specificed: {args.section}")

    return args, sub_event, sub_nonsense, prepend_event, suffix, section_display_name

def load_meddra():
    # load preferred terms and lower level terms
    meddra_fn = './data/meddra_llt_pt_map.txt'
    meddra_fh = open(meddra_fn)
    reader = csv.reader(meddra_fh, delimiter='|')
    header = next(reader)

    llts = dict()

    for row in reader:
        data = dict(zip(header, row))
        llts[data['llt_concept_code']] = data['llt_concept_name'].lower()

    meddra_fh.close()

    return llts

def get_annotations(drug, section_display_name):

    final_ref_fn = './data/200_manual_annotations_csv/FinalReferenceStandard200Labels.csv'
    final_ref_fh = open(final_ref_fn)
    reader = csv.reader(final_ref_fh, delimiter='|')
    header = next(reader)

    pts_annotated = set()
    llts_annotated = set()
    string_annotated = set()

    for row in reader:
        data = dict(zip(header, row))

        if not data['Drug Name'] == drug:
            continue

        if not data['Section Display Name'] == section_display_name:
            continue

        pts_annotated.add(data['PT ID'])
        llts_annotated.add(data['LLT ID'])
        string_annotated.add(data['Matching String'].lower())

    final_ref_fh.close()

    return pts_annotated, llts_annotated, string_annotated

def generate_examples(ar_text, llt, nwords, sub_event, sub_nonsense, prepend_event):
    parts = ar_text.split(llt)

    size_of_llt = len(llt.split())

    # NOTE: BERT has a limit of 512 tokens, words that are not in BERTs
    # NOTE: dictionary are split into subwords and tokenized. So the actual
    # NOTE: number of tokens is more than the number of words. We initially
    # NOTE: used ~128.
    size_of_parts = nwords - size_of_llt

    if len(parts) == 1:
        raise Exception("Parts has length of 1 which shouldn't be possible.")

    strings = list()
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
        strings.append(example_string)

    return strings

def main():

    args, sub_event, sub_nonsense, prepend_event, suffix, section_display_name = get_args()

    llts = load_meddra()

    # derive a drug list from the training and testing data provided
    train_drugs = set([fn.split('_')[0] for fn in os.listdir('./data/200_training_set') if fn.find(suffix) != -1])
    test_drugs = set([fn.split('_')[0] for fn in os.listdir('./data/200_test_set') if fn.find(suffix) != -1])

    all_drugs = sorted(train_drugs | test_drugs)
    print(f"Found {len(all_drugs)} total drugs with *{suffix} files.")

    # generate reference data for a specific drug

    # drug = 'ADCETRIS'

    total_num_neg = 0
    total_num_pos = 0

    outfn = f'./data/ref{args.method}_nwords{args.nwords}_clinical_bert_reference_set_{args.section}.txt'
    outfh = open(outfn, 'w')
    writer = csv.writer(outfh)
    writer.writerow(['drug', 'llt_id', 'llt', 'class', 'string'])

    for drug in all_drugs:
        print(f"Generating reference data for: {drug}")

        pts_annotated, llts_annotated, string_annotated = get_annotations(drug, section_display_name)

        print(f"\tPreferred terms annotated: {len(pts_annotated)}")
        print(f"\tLower level terms annotated: {len(llts_annotated)}")
        print(f"\tIntersection of terms with local meddra map: {len(string_annotated & set(llts.values()))}")

        # load text from the desired (e.g. ADVERSE REACTIONS) section
        ar_file_path = f'./data/200_training_set/{drug}_{suffix}'
        if os.path.exists(ar_file_path):
            ar_fh = open(ar_file_path)
        else:
            ar_file_path = f'./data/200_test_set/{drug}_{suffix}'
            if os.path.exists(ar_file_path):
                ar_fh = open(ar_file_path)
            else:
                raise Exception("Couldn't file adverse reactions file in either the training or testing set.")

        ar_text = ' '.join(ar_fh.read().split()).lower()

        print(f"\tNumber of words in {section_display_name} text: {len(ar_text.split())}")

        # find all the llts that are mentioned in the text

        llts_mentioned = set()
        string_mentioned = set()

        num_pos = 0
        num_neg = 0

        for llt_id, llt in llts.items():
            if ar_text.find(llt) != -1:
                llts_mentioned.add(llt_id)
                string_mentioned.add(llt)

                example_strings = generate_examples(ar_text, llt, args.nwords, sub_event, sub_nonsense, prepend_event)

                # check if this event was annotated from the gold standard
                if llt_id in llts_annotated:
                    string_class = 'is_event'
                    num_pos += len(example_strings)
                else:
                    string_class = 'not_event'
                    num_neg += len(example_strings)

                # NOTE: was using the matching string to match between the two,
                # NOTE: but really should be using the LLT MedDRA identifier (above)
                # NOTE: keeping this in here so we know what we did initially - NPT 4/19/22

                # if llt in string_annotated:
                #     string_class = 'is_event'
                #     num_pos += 1
                # else:
                #     string_class = 'not_event'
                #     num_neg += 1

                for example_string in example_strings:
                    writer.writerow([drug, llt_id, llt, string_class, example_string])


        print(f"\tNumber of terms mentioned in text: {len(llts_mentioned)}")

        print(f"\tNumber of positive events: {len(string_annotated & string_mentioned)}")
        print(f"\tNumber of negative events: {len(string_mentioned - string_annotated)}")

        print(f"\tNumber of positive training examples: {num_pos}")
        print(f"\tNumber of negative training examples: {num_neg}")

        # print(string_annotated - string_mentioned)
        # print(llts_annotated)

        total_num_pos += num_pos
        total_num_neg += num_neg

    print(f"Finished generating reference set")
    print(f" Total Pos: {total_num_pos}")
    print(f" Total Neg: {total_num_neg}")

    outfh.close()

if __name__ == '__main__':
    main()
