"""
Parse the train_xml and gold_xml files into a training and testing set
for exploring and evaluating normalization models.

train_xml was downloaded from https://bionlp.nlm.nih.gov/tac2017adversereactions/
gold_xml can be obtained by emailing the TAC organizers.

@author Nicholas Tatonetti, 2022

NOTES
=====
This is the first step of the process. Next is to perform preprocessing:

"""

import os
import sys
import csv
import nltk
import string
import argparse

import xml.etree.ElementTree as ET

_XML_PATH = './data/%s_xml'

def main(split):

    xml_files = [os.path.join(_XML_PATH % split, f) for f in os.listdir(_XML_PATH % split) if f.endswith('.xml')]
    f = xml_files[0]

    maps = set()

    for f in xml_files:

        abbrev_f = f + '-abbrev.txt'

        abbreviations = dict()
        if not os.path.exists(abbrev_f):
            print("WARNING: No abbreviations file found for %s. Use Ab3p to extract abbreviations (see Step 1).")
        else:
            fh = open(abbrev_f)
            reader = csv.reader(fh, delimiter='|')
            for abbrev, expanded_term, score in reader:
                abbrev = abbrev.strip().lower()
                abbreviations[abbrev] = expanded_term.lower()
            fh.close()

        tree = ET.parse(f)
        root = tree.getroot()

        reaction = root.find('Reactions')
        for child in reaction:
            norm = child.find('Normalization')
            # print(norm)
            if norm.get('flag') == 'unmapped':
                continue
            # print(child.get('str'), norm.get('meddra_pt'), norm.get('meddra_pt_id'), norm.get('meddra_llt'), norm.get('meddra_llt_id'))
            # writer.writerow([child.get('str'), norm.get('meddra_pt'), norm.get('meddra_pt_id'), norm.get('meddra_llt'), norm.get('meddra_llt_id')])

            raw_string = child.get('str').lower()
            is_abbreviation = raw_string in abbreviations
            expanded_term = abbreviations[raw_string] if is_abbreviation else ''
            maps.add((os.path.split(f)[-1], child.get('str'), norm.get('meddra_pt_id'), is_abbreviation, expanded_term))

    ofh = open('./data/normalization/%s_xml_normalization_map_step2.txt' % split, 'w')
    writer = csv.writer(ofh)
    writer.writerow(['source_xml', 'string_found', 'meddra_pt_id', 'is_abbreviation', 'expanded_term'])
    writer.writerows(list(maps))
    ofh.close()

if __name__ == '__main__':
    main('train')
    main('gold')
