"""
construct_training_data.py

Using the manual annotations from Demmer-Fushman et al. Scientific Data
construct a training set for use in training a classifier.

For each mentioned MedDRA term, the classifier will predict whether or not
the term will be manually annotated as an adverse event for the drug.

@author Nicholas Tatonetti, Tatonetti Lab, Columbia University
"""

import os
import re
import sys
import csv
import time
import random
import argparse
import xml.etree.ElementTree as ET
from collections import defaultdict

section_suffices = {
    'AR': 'adverse_reactions.txt',
    'BW': 'boxed_warnings.txt',
    'WP': 'warnings_and_precautions.txt'
}
section_display_names = {
    'AR': 'ADVERSE REACTIONS',
    'BW': 'BOXED WARNINGS',
    'WP': 'WARNINGS AND PRECAUTIONS'
}
section_names2codes = {
    'ADVERSE REACTIONS': 'AR',
    'BOXED WARNINGS': 'BW',
    'WARNINGS AND PRECAUTIONS': 'WP'
}

section_deepcadrme_names = {
    'AR': 'adverse reactions',
    'BW': 'boxed warnings',
    'WP': 'warnings and precautions'
}

def get_args(addl_args = None):

    parser = argparse.ArgumentParser()
    parser.add_argument('--method', type=int, required=True)
    parser.add_argument('--nwords', help='The number of words to grab from either side total (nwords/2 before and nwords/2 after) of the event mention to generate the training example', type=int, default=125)
    parser.add_argument('--section', help='Designate which section of the label to parse. Options are AR (adverse reactions), BW (boxed warnings), or WP (warnings and precautions)', type=str, default='AR')
    parser.add_argument('--prop-before', type=float, default=0.5, help="Proportion of nwords that should come from before the event term. Default is 0.5 (50%).")

    if not addl_args is None and type(addl_args) is list:
        for addl_arg in addl_args:
            parser.add_argument(*addl_arg['args'], **addl_arg['kwargs'])

    args = parser.parse_args()

    if args.nwords == 3 and args.method != 0:
        raise Exception("ERROR: method must be set to 0 if nwords is set to 3, it is a special case where only the llt is included as the example.")

    if args.nwords < 3:
        raise Exception("ERROR: nwords must be >= 3.")

    sub_event = False
    sub_nonsense = False
    prepend_event = False
    prepend_source = False
    # prepend_section = False
    random_sampled_words = False

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
    elif args.method == 5:
        random_sampled_words = True
    elif args.method == 6:
        # this is method 0 except that all the words are from "BEFORE" the AE term
        sub_event = True
        prepend_event = True
        args.prop_before = 1.0
    elif args.method == 7:
        # this is method 0 except that all the words are from "AFTER" the AE term
        sub_event = True
        prepend_event = True
        args.prop_before = 0.0
    elif args.method == 8:
        sub_event = True
        prepend_event = True
        args.prop_before = 0.125
    elif args.method == 9:
        sub_event = True
        prepend_event = True
        args.prop_before = 0.25
    elif args.method == 10:
        sub_event = True
        prepend_event = True
        args.prop_before = 0.75
    elif args.method == 11:
        sub_event = True
        prepend_event = True
        args.prop_before = 0.875
    elif args.method == 12:
        sub_event = True
        prepend_event = True
        prepend_source = True
    elif args.method == 13:
        sub_event = True
        prepend_event = True
        prepend_source = True
        args.prop_before = 0.25
    elif args.method == 14:
        sub_event = True
        prepend_event = True
        prepend_source = True
        args.prop_before = 0.125
    elif args.method == 15:
        sub_event = True
        prepend_event = True
        prepend_source = True
        args.prop_before = 0.0
    else:
        raise Exception(f"Expected method argument to be an integer value (0-11). Got {args.method}")

    if args.prop_before < 0 or args.prop_before > 1:
        raise Exception(f"ERROR: Unexpected value ({args.prop_before}) provided for --prop-before. Needs to be a float between 0 and 1, inclusive.")


    sections = list()
    if args.section in ('AR', 'BW', 'WP'):
        # ADVERSE REACTIONS
        sections.append(args.section)
    elif args.section == 'ALL':
        # all three sections
        sections.append('AR')
        sections.append('BW')
        sections.append('WP')
    elif args.section == 'ARBW':
        # AR and BW, but not WP
        sections.append('AR')
        sections.append('BW')
    else:
        raise Exception(f"ERROR: Unknown section specificed: {args.section}")

    return args, sub_event, sub_nonsense, prepend_event, prepend_source, sections, random_sampled_words

def load_meddra():
    # load preferred terms and lower level terms
    meddra_fn = './data/meddra_llt_pt_map.txt'
    meddra_fh = open(meddra_fn)
    reader = csv.reader(meddra_fh, delimiter='|')
    header = next(reader)

    llts = dict()

    # llt_concept_id|llt_concept_name|llt_concept_code|pt_concept_id|pt_concept_name|pt_concept_code
    for row in reader:
        data = dict(zip(header, row))
        llts[data['llt_concept_code']] = (data['llt_concept_name'].lower(), data['pt_concept_name'], data['pt_concept_code'])

    meddra_fh.close()

    return llts

def load_deepcadrme():
    # DeepCADRME has been run on the training and testing set provided by Demmer-Fushman et al.
    # We saved those to a file named ./data/deepcadrme_guess_terms.csv
    # These terms were then mapped using either exact string matches or fuzzy matching
    # to meddra LLTs and PTs. LLTs were then mapped to PTs.
    # Currently this is done in the normalize deepcadrme files jupyter notebook.
    # TODO: Move processing of deepcadrme output to a script.
    # The normalized deepcadrme output is then stored at ./data/Deepcadrme_guess_terms_meddramatch.csv
    deepcadrme_fn = './data/deepcadrme_guess_terms_meddramatch.csv'
    deepcadrme_fh = open(deepcadrme_fn)
    reader = csv.reader(deepcadrme_fh)
    header = next(reader)

    deepcadrme = defaultdict(list)
    for _, xmlfile, term, start, length, match_method, meddra_id, meddra_string in reader:
        drugname = xmlfile.strip('.xml').lower()
        deepcadrme[drugname].append( (term, start, length, match_method, meddra_id, meddra_string) )

    return deepcadrme

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

        if not data['Drug Name'].lower() == drug.lower():
            continue

        if not data['Section Display Name'] == section_display_name:
            continue

        pts_annotated.add(data['PT ID'])
        llts_annotated.add(data['LLT ID'])
        string_annotated.add(data['Matching String'].lower())

    final_ref_fh.close()

    # NOTE: llts_annotated actually contains both PTs and LLTs
    # NOTE: because in the reference csv if the string found was directly mapped
    # NOTE: to a PT then it's in both columns. However, they may not contain
    # NOTE: allof the PTs if only the LLT version of the term was annotated.
    return pts_annotated, llts_annotated, string_annotated

def generate_example(ar_text, term, start_pos, length, nwords, sub_event, sub_nonsense, prepend_event, random_sampled_words, prop_before, source):

    if type(start_pos) == str or type(length) == str:
        if type(start_pos) != str:
            start_pos = str(start_pos)
        if type(length) != str:
            length = str(length)

        # this means we have a split term that was discovered using deepcadrme
        # for these we use the start_pos of all of the first term (start_pos[0])
        # and then the length will be start_pos[-1]+length[-1]
        start_positions = list(map(int, start_pos.split(',')))
        lengths = list(map(int, length.split(',')))
        start_pos = start_positions[0]
        length = (start_positions[-1]+lengths[-1])-start_positions[0]

    # print(f"type(start_pos) = {type(start_pos)}, {start_pos}")
    # print(f"type(length) = {type(length)}, {length}")
    # print(f"type(nwords) = {type(nwords)}, {nwords}")

    term_nwords = len(term.split())
    size_before = max(int((nwords-2*term_nwords)*prop_before), 1)
    size_after = max(int((nwords-2*term_nwords)*(1-prop_before)), 1)

    # print(f"size_before = {size_before}")
    # print(f"size_after = {size_after}")

    EVENT_STRING = term
    if sub_event:
        EVENT_STRING = 'EVENT'
    if sub_nonsense:
        EVENT_STRING = 'YIHFKEHDK'

    # TODO: Implement prepend section option
    START_STRING = ''
    if prepend_event:
        START_STRING = term

    # Prepend source if it is not None type
    if not source is None:
        if source == 'exact':
            START_STRING += ' ' + 'exact'
        elif source == 'deepcadrme':
            START_STRING += ' ' + 'split'
        else:
            raise Exception(f"ERROR: Encountered unexpected source value: {source}. Expected either 'exact' or 'deepcadrme'.")

    if random_sampled_words:
        # method 5 is just a random bag of words
        example_string = ' '.join(random.sample(ar_text.split(), nwords))
    elif nwords == 3:
        # nwords == 3 is a special case where we only include the term and nothing else
        example_string = term
    else:
        # normal scenario
        before_text = ar_text[:start_pos]
        after_text = ar_text[(start_pos+length):]

        before_parts = before_text.split()[-1*size_before:]
        after_parts = after_text.split()[:size_after]

        li = [START_STRING]

        if prop_before > 0:
            li.extend(before_parts)

        li.append(EVENT_STRING)

        if prop_before < 1:
            li.extend(after_parts)

        example_string = ' '.join(li)

    if len(example_string.split()) > (nwords+length):
        raise Exception(f"ERROR: Example string is too long for term={term}, was length {len(example_string.split())}, expected less than {nwords}")

    return example_string


# @deprecated
def generate_examples(ar_text, llt, nwords, sub_event, sub_nonsense, prepend_event, random_sampled_words, prop_before):
    parts = ar_text.split(llt)

    size_of_llt = len(llt.split())

    # NOTE: BERT has a limit of 512 tokens, words that are not in BERTs
    # NOTE: dictionary are split into subwords and tokenized. So the actual
    # NOTE: number of tokens is more than the number of words. We initially
    # NOTE: used ~128.


    # size_of_parts = max(int(nwords/2) - size_of_llt, 1)

    size_before = max(int((nwords-2*size_of_llt)*prop_before), 1)
    size_after = max(int((nwords-2*size_of_llt)*(1-prop_before)), 1)

    # print(f"size_of_parts = {size_of_parts}")
    # print(f"size_before = {size_before}")
    # print(f"size_after = {size_after}")
    # sys.exit(1)

    if len(parts) == 1:
       raise Exception("Parts has length of 1 which shouldn't be possible.")

    strings = list()

    EVENT_STRING = llt
    if sub_event:
        EVENT_STRING = 'EVENT'
    if sub_nonsense:
        EVENT_STRING = 'YIHFKEHDK'

    # TODO: Implement prepend section option (ref12, currently not implemented)
    START_STRING = ''
    if prepend_event:
        START_STRING = llt


    for i in range(len(parts)-1):
        if random_sampled_words:
            # method 5 is just a random bag of words
            example_string = ' '.join(random.sample(ar_text.split(), nwords))
        elif nwords == 3:
            # nwords == 3 is a special case where we only include the llt and nothing else
            example_string = llt
        else:
            # normal scenario
            before_parts = parts[i].split()[-1*size_before:]
            after_parts = parts[i+1].split()[:size_after]

            li = [START_STRING]

            if prop_before > 0:
                li.extend(before_parts)

            li.append(EVENT_STRING)

            if prop_before < 1:
                li.extend(after_parts)

            example_string = ' '.join(li)

        if len(example_string.split()) > (nwords+size_of_llt):
            raise Exception(f"ERROR: Example string is too long for llt={llt}, was length {len(example_string.split())}, expected less than {nwords}")

        strings.append(example_string)

    # A different method of generating the strings that goes beyond the next
    # occurrence of the llt in the overall text. Not tested for its performance yet.
    # for match in re.finditer(llt, ar_text):
    #     start, end = match.span()
    #     example_string = START_STRING + ' ' + ' '.join(ar_text[:start].split()[(-1*size_of_parts):] + [EVENT_STRING] + ar_text[end:].split()[:size_of_parts])
    #     strings.append(example_string)


    return strings

def main():

    random.seed(222)

    args, sub_event, sub_nonsense, prepend_event, prepend_source, sections, random_sampled_words = get_args()

    llts = load_meddra()

    #if we cannot find deepcadrme, load an empty dictionary in place of it(temp. solution, make it a variable you can choose)
    try:
        deepcadrme = load_deepcadrme()
    except:
        deepcadrme = {}    
    
    if not os.path.exists('./data/refs'):
        os.makedirs('./data/refs')
    
    outfn = f'./data/refs/ref{args.method}_nwords{args.nwords}_clinical_bert_reference_set_{args.section}.txt'
    outfh = open(outfn, 'w')
    writer = csv.writer(outfh)

    writer.writerow(['section', 'drug', 'tac', 'meddra_id', 'pt_meddra_id', 'source_method', 'class', 'pt_meddra_term', 'found_term', 'string'])

    total_num_neg = 0
    total_num_pos = 0

    for section in sections:
        suffix = section_suffices[section]
        section_display_name = section_display_names[section]

        # derive a drug list from the training and testing data provided
        train_drugs = set([fn.split('_')[0] for fn in os.listdir('./data/200_training_set') if fn.find(suffix) != -1])
        test_drugs = set([fn.split('_')[0] for fn in os.listdir('./data/200_test_set') if fn.find(suffix) != -1])
        all_drugs = sorted(train_drugs | test_drugs)

        print(f"Found {len(all_drugs)} total drugs with available files.")

        for drug in all_drugs:

            print(f"Generating reference data for: {drug}")

            pts_annotated, llts_annotated, string_annotated = get_annotations(drug, section_display_name)

            set_meddra_terms = set([x[0] for x in llts.values()])

            print(f"\tPreferred terms annotated: {len(pts_annotated)}")
            print(f"\tLower level terms annotated: {len(llts_annotated)}")
            print(f"\tIntersection of terms with local meddra map: {len(string_annotated & set_meddra_terms)}")

            # load text from the desired (e.g. ADVERSE REACTIONS) section

            # use the output of deepcadrme
            ar_file_path = f'./data/deepcadrme/guess_xml/{drug.upper()}.xml'
            # print(ar_file_path)
            deepcadrme_ar_text = None
            if os.path.exists(ar_file_path):
                tree = ET.parse(ar_file_path)
                root = tree.getroot()
                xml_sections = root.findall("./Text/Section[@name='%s']" % section_deepcadrme_names[section])
                if len(xml_sections) != 1:
                    raise Exception("ERROR: Unexpected number of sections named %s. Expected 1 found %s." % (section_deepcadrme_names[section], len(xml_sections)))
                deepcadrme_ar_text = ' '.join(xml_sections[0].text.split()).lower()

            # TODO: Replace the use of these provided files with our method of parsing into
            # TODO: json files using the spl_processor.py script.
            ar_file_path = f'./data/200_training_set/{drug}_{suffix}'
            if os.path.exists(ar_file_path):
                ar_fh = open(ar_file_path)
            else:
                ar_file_path = f'./data/200_test_set/{drug}_{suffix}'
                if os.path.exists(ar_file_path):
                    ar_fh = open(ar_file_path)
                else:
                    raise Exception("Couldn't find adverse reactions file in either the training or testing set.")
            ar_text = ' '.join(ar_fh.read().split()).lower()

            print(f"\tNumber of words in {section_display_name} text: {len(ar_text.split())}")

            # find all the adverse event terms that are mentioned in the text

            start_time = time.time()
            # 1) exact string matches to the meddra term (either PT or LLT)
            # NOTE: llts has both PTs and LLTs because of the structure of the file
            found_terms = list()
            for meddra_id, (llt_meddra_term, pt_meddra_term, pt_meddra_id) in llts.items():
                #print(f"{meddra_id}, {llt_meddra_term}, {pt_meddra_term}")

                # Method using re module. Takes approx 4 seconds.
                # try:
                #     for start_pos in [m.start() for m in re.finditer(llt_meddra_term, ar_text)]:
                #         # we use the PT here so that there are fewere different terms prepended to the example strings
                #         # this should marginally improve performance
                #         found_terms.append((llt_meddra_term, meddra_id, start_pos, len(llt_meddra_term), pt_meddra_term, 'exact'))
                # except re.error as e:
                #     #print(f"WARNING: Encountered re module error: {e}")
                #     pass

                # Method using string splits, Takes approx 0.2s
                if ar_text.find(llt_meddra_term) == -1:
                    continue

                li = ar_text.split(llt_meddra_term)
                start_pos = 0
                for i in range(len(li)-1):
                    # the occurrence of the word is at the end of the previous string
                    start_pos = sum([len(li[j]) for j in range(i+1)]) + i*len(llt_meddra_term)
                    if not llt_meddra_term == ar_text[start_pos:(start_pos+len(llt_meddra_term))]:
                        raise Exception(f" llt_meddra_term: '{llt_meddra_term}', term_in_text: '{ar_text[start_pos:(start_pos+len(llt_meddra_term))]}'")
                    found_terms.append((llt_meddra_term, meddra_id, start_pos, len(llt_meddra_term), pt_meddra_id, pt_meddra_term, 'exact'))


            print(f"\tFound {len(found_terms)} terms using exact string matches. Took {time.time()-start_time}s.")

            exact_term_list = list(zip(*found_terms))[0]

            start_time = time.time()
            # 2) DeepCADRME mentions, normalized to meddra terms (PT only)
            #    If DeepCADRME found string is exact match for a term (PT or LLT)
            #    then we skip that. It will be handled by the exact matches done above
            drugname = drug.lower()
            if not drugname in deepcadrme:
                print(f'WARNING: No DeepCADRME output found for {drugname}.')
            else:
                for term, start, length, match_method, pt_meddra_id, pt_meddra_term in deepcadrme[drugname]:
                    if term in exact_term_list and start.find(',') == -1:
                        # we don't need deepcadrme for this one, we will use the exact string matches
                        continue

                    found_terms.append((term, pt_meddra_id, start_pos, length, pt_meddra_id, pt_meddra_term, 'deepcadrme'))

            print(f"\tFound {len(found_terms)} terms using both exact and DeepCADRME. Took {time.time()-start_time}s.")

            num_pos = 0
            num_pos_exact = 0

            num_neg = 0
            num_neg_exact = 0

            for found_term, meddra_id, start_pos, length, pt_meddra_id, pt_meddra_term, source_method in found_terms:

                if meddra_id in llts_annotated or meddra_id in pts_annotated or pt_meddra_id in pts_annotated:
                    string_class = 'is_event'
                    num_pos += 1
                    if source_method == 'exact':
                        num_pos_exact += 1
                else:
                    string_class = 'not_event'
                    num_neg += 1
                    if source_method == 'exact':
                        num_neg_exact += 1

                label_text = ar_text
                if source_method == 'deepcadrme':
                    label_text = deepcadrme_ar_text

                # This is for reference methods 12+
                source = None
                if prepend_source:
                    source = source_method

                example_string = generate_example(label_text, found_term, start_pos, length, args.nwords, sub_event, sub_nonsense, prepend_event, random_sampled_words, args.prop_before, source)

                tac = None
                if drug in train_drugs:
                    tac = 'train'
                elif drug in test_drugs:
                    tac = 'test'
                else:
                    raise Exception(f"ERROR: Drug {drug} not found in either train_drugs or test_drugs. This shouldn't happen.")

                writer.writerow([section, drug.upper(), tac, meddra_id, pt_meddra_id, source_method, string_class, pt_meddra_term, found_term, example_string])

            ################################################################################
            # This was the previous method we used to do this that only relied on exact
            # string matches. We have refactored the code to allow for different methods of
            # identifying terms. -NPT 9/14/22
            ################################################################################
            # llts_mentioned = set()
            # string_mentioned = set()
            #
            # num_pos = 0
            # num_neg = 0
            #
            # for meddra_id, (meddra_term, pt_meddra_term) in llts.items():
            #     if ar_text.find(meddra_term) != -1:
            #         llts_mentioned.add(meddra_id)
            #         string_mentioned.add(meddra_term)
            #
            #         example_strings = generate_examples(ar_text, meddra_term, args.nwords, sub_event, sub_nonsense, prepend_event, random_sampled_words, args.prop_before)
            #
            #         # check if this event was annotated from the gold standard
            #         # NOTE: llts_annotated contains both PTs and LLTs
            #         if meddra_id in llts_annotated:
            #             string_class = 'is_event'
            #             num_pos += len(example_strings)
            #         else:
            #             string_class = 'not_event'
            #             num_neg += len(example_strings)
            #
            #         for example_string in example_strings:
            #             writer.writerow([section, drug, meddra_id, 'depr_exact', string_class, meddra_term, meddra_term, example_string])
            #
            #
            # print(f"\tNumber of terms mentioned in text: {len(llts_mentioned)}")
            #
            # print(f"\tNumber of positive events: {len(llts_annotated & llts_mentioned)}")
            # print(f"\tNumber of negative events: {len(llts_mentions - llts_annotated)}")
            ################################################################################

            print(f"\tNumber of positive training examples: {num_pos}")
            print(f"\tNumber of negative training examples: {num_neg}")

            print(f"\tNumber of positive training examples (from deepcadrme): {num_pos-num_pos_exact}")
            print(f"\tNumber of negative training examples (from deepcadrme): {num_neg-num_neg_exact}")

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
