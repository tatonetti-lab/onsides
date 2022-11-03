"""
manual_review.py

Tool to assist in the manual review of a set of N randomly chosen extracted
adverse event terms. Provide the path to the compiled release file.

NOTE: This works and does help for quick review. However, it is also a bit buggy
NOTE: and can cause the system to lag and behave oddly (because of the keyboard)
NOTE: listening. This needs to be refactored in an upcoming version.

"""

import os
import sys
import csv
import json
import gzip
import termios
import argparse

import pandas as pd

from pynput import keyboard
from collections import defaultdict

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

colors_list = [bcolors.HEADER, bcolors.OKBLUE, bcolors.OKCYAN, bcolors.OKGREEN, bcolors.WARNING, bcolors.FAIL]

def load_meddra():
    fh = open('./data/meddra_llt_pt_map.txt')
    reader = csv.reader(fh, delimiter='|')
    header = next(reader)

    pt2llt = defaultdict(set)
    for row in reader:
        data = dict(zip(header, row))
        pt2llt[data['pt_concept_code']].add(data['llt_concept_name'])

    return pt2llt

def load_json(filename):
    fh = open(filename)
    data = json.loads(fh.read())
    fh.close()
    return data

def save_json(filename, data):
    fh = open(filename, 'w')
    fh.write(json.dumps(data, indent=4))
    fh.close()

def review(ptid, ptterm, orig_text, pt2llt):
    text = orig_text.lower()

    found_terms = set()
    found_positions = list()

    if not ptid in pt2llt:
        raise Exception(f"ERROR: Did not find {ptid} in meddra dictionary.")

    for term in pt2llt[ptid]:
        term = term.lower()

        if text.find(term) == -1:
            continue

        found_terms.add(term)

        li = text.split(term)
        start_pos = 0
        for i in range(len(li)-1):
            # the occurrence of the word is at the end of the previous string
            start_pos = start_pos + len(li[i])
            found_positions.append((start_pos, term))
    found_terms = sorted(found_terms)

    #print(f"Identified preferred term: {ptterm}")
    orig_terms_replaced = set()
    annotated_text = str(orig_text)
    for start_pos, term in found_positions:
        i = found_terms.index(term)
        orig_term = orig_text[start_pos:(start_pos+len(term))]
        print(f"term: {term}, start_pos: {start_pos}; orig_term: {orig_term}")

        if orig_term in orig_terms_replaced:
            continue
        annotated_text = annotated_text.replace(orig_term, f"{colors_list[i%len(colors_list)]}{orig_term}{bcolors.ENDC}")
        orig_terms_replaced.add(orig_term)

    #print(f"Occurrences in text: {len(found_terms)}")

    if len(found_terms) == 0:
        raise Exception(f"ERROR: No mention of {ptid} in text.")

    term_count = defaultdict(int)

    for start_pos, term in sorted(found_positions):
        annotated_lines = annotated_text.split('\n')
        term_line = [i for i, line in enumerate(text.split('\n')) if line.find(term) != -1][term_count[term]]
        term_count[term] += 1
        scan = 0
        input("Press the enter key to continue.")

        while True:
            os.system('clear')
            print(f"Identified preferred term: {ptterm}")
            for i, term in enumerate(found_terms):
                print(f"  lower level term: {colors_list[i%len(colors_list)]}{term}{bcolors.ENDC}")

            print(f"Occurrences in text: {len(found_terms)}\n")
            #startinput("Press Enter to continue.")

            print(f"---------------------------------------------------------------")
            print(f"\nDoes the mention of the {colors_list[i%len(colors_list)]}{term}{bcolors.ENDC} in the following text indicate that this is an adverse drug reaction?\n")
            print(f"---------------------------------------------------------------")
            print('\n'.join(annotated_lines[(term_line-15+scan):(term_line+15+scan)]))
            print(f"---------------------------------------------------------------")
            print("Use the ',' and '.' keys to scan through the text. Respond with 'y' or 'n': ")

            response = None

            with keyboard.Events() as events:
                # Block for as much as possible
                event = events.get(1e6)
                #print(event.key)
                if event.key == keyboard.KeyCode.from_char('y'):
                    response = 'yes'
                    return True
                elif event.key == keyboard.KeyCode.from_char('n'):
                    response = 'no'
                    break
                elif event.key == keyboard.KeyCode.from_char(','):
                    scan -= 1
                    if (term_line-15+scan) < 0:
                        scan += 1
                elif event.key == keyboard.KeyCode.from_char('.'):
                    scan += 1
                    if (term_line+15+scan) >= len(annotated_lines):
                        scan -=1
                elif event.key == keyboard.KeyCode.from_char('m'):
                    scan -= 15
                    if (term_line-15+scan) < 0:
                        scan += 15
                elif event.key == keyboard.KeyCode.from_char('/'):
                    scan += 15
                    if (term_line+15+scan) >= len(annotated_lines):
                        scan -= 15

            #events.join()

    if response is None:
        raise Exception("Response not set.")

    return False

    # print(annotated_text)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', help='Path to the compiled release file.', type=str, required=True)
    parser.add_argument('-n', '--num', help='Number of extracted adverse reactions to review.', type=int, default=10)

    args = parser.parse_args()

    compiled_version_path, filename = os.path.split(args.file)
    compiled_path, version = os.path.split(compiled_version_path)
    labels_dir = os.path.split(compiled_path)[0]
    section = filename.split('.')[0]

    print(f"Initiating manual review of {args.file}")

    review_json_path = os.path.join(labels_dir, 'manual_review.json')
    if os.path.exists(review_json_path):
        review_status = load_json(review_json_path)
    else:
        review_status = {
            "reviews": dict()
        }
        save_json(review_json_path, review_status)

    pt2llt = load_meddra()

    # we sample twice as many as we need so that if we hit one that's already
    # been done, we can still it our number
    df = pd.read_csv(args.file).sample(2*args.num)

    num_reviewed = 0
    for idx, row in df.iterrows():
        key = f"{row['drug']},{row['pt_meddra_id']}"
        if key in review_status["reviews"]:
            # already reviewed
            continue

        label_text = load_json(os.path.join(labels_dir, 'prescription', f"{row['drug']}.json"))
        text = label_text['sections'][section]
        ptid = str(row['pt_meddra_id'])

        # print(f"{bcolors.HEADER}Color Test: HEADER{bcolors.ENDC}")
        # print(f"{bcolors.OKBLUE}Color Test: OKBLUE{bcolors.ENDC}")
        # print(f"{bcolors.OKCYAN}Color Test: OKCYAN{bcolors.ENDC}")
        # print(f"{bcolors.OKGREEN}Color Test: OKGREEN{bcolors.ENDC}")
        # print(f"{bcolors.WARNING}Color Test: WARNING{bcolors.ENDC}")
        # print(f"{bcolors.FAIL}Color Test: HEADER{bcolors.ENDC}")

        #print("*************************")
        #print(f"Label File Name: {row['drug']}")

        if review(ptid, row['pt_meddra_term'], text, pt2llt):
            review_status["reviews"][key] = 'yes'
        else:
            review_status["reviews"][key] = 'no'
        save_json(review_json_path, review_status)

        num_reviewed += 1
        if num_reviewed >= args.num:
            break


    print("Manual review completed. Computing Positive Predictive Value (PPV)...")

    correct = 0
    for key in review_status['reviews'].keys():
        if review_status['reviews'][key] == 'yes':
            correct += 1

    predicted = len(review_status['reviews'].keys())

    print("PPV = %.3f (N = %d)" % (correct/float(predicted), predicted))

    input("Press enter to exit program.")









if __name__ == '__main__':
    main()
