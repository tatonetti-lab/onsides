"""
Using the manual annotations from Demmer-Fushman et al. Scientific Data
construct a training set for use in training a classifier.

For each metnioned MedDRA term, the classifier will predict whether or not
the term will be manually annoated as an adverse event for the drug.

"""

import os
import sys
import csv

def main():

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
    train_drugs = set([fn.split('_')[0] for fn in os.listdir('./data/200_training_set') if fn.find('adverse_reactions.txt') != -1])
    test_drugs = set([fn.split('_')[0] for fn in os.listdir('./data/200_test_set') if fn.find('adverse_reactions.txt') != -1])

    all_drugs = train_drugs | test_drugs
    print(f"Found {len(all_drugs)} total drugs")

    # generate reference data for a specific drug

    # drug = 'ADCETRIS'

    total_num_neg = 0
    total_num_pos = 0

    for drug in all_drugs:
        print(f"Generating refernece data for: {drug}")

        outfn = './data/clinical_bert_reference_set.txt'
        outfh = open(outfn, 'w')
        writer = csv.writer(outfh)
        writer.writerow(['drug', 'llt_id', 'llt', 'class', 'string'])


        # ADVERSE REACTIONS Section
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

            if not data['Section Display Name'] == 'ADVERSE REACTIONS':
                continue

            pts_annotated.add(data['PT ID'])
            llts_annotated.add(data['LLT ID'])
            string_annotated.add(data['Matching String'].lower())

        final_ref_fh.close()

        print(f"\tPreferred terms annotated: {len(pts_annotated)}")
        print(f"\tLower level terms annotated: {len(llts_annotated)}")
        print(f"\tIntersection of terms with local meddra map: {len(string_annotated & set(llts.values()))}")

        # load text from adverse events section
        ar_file_path = './data/200_training_set/%s_adverse_reactions.txt' % drug
        if os.path.exists(ar_file_path):
            ar_fh = open(ar_file_path)
        else:
            ar_file_path = './data/200_test_set/%s_adverse_reactions.txt' % drug
            if os.path.exists(ar_file_path):
                ar_fh = open(ar_file_path)
            else:
                raise Exception("Couldn't file adverse reactions file in either the training or testing set.")

        ar_text = ' '.join(ar_fh.read().split()).lower()
        print(f"\tNumber of words in ADVERSE EVENTS text: {len(ar_text.split())}")

        # find all the llts that are mentioned in the text

        llts_mentioned = set()
        string_mentioned = set()

        num_pos = 0
        num_neg = 0

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
                    example_string = llt + ' ' + ' '.join(parts[i].split()[-1*size_of_parts:] + ['EVENT'] + parts[i+1].split()[:size_of_parts])
                    if llt in string_annotated:
                        string_class = 'is_event'
                        num_pos += 1
                    else:
                        string_class = 'not_event'
                        num_neg += 1

                    writer.writerow([drug, llt_id, llt, string_class, example_string])

                # break


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
