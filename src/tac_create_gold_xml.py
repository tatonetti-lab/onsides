"""
Generates xml files for the test data which are used as input to the tac_official_eval_script.py.

@authors Cindy Chen, Nicholas Tatonetti, TatonettiLab 2022
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom

import pandas as pd
import argparse
import tqdm
import math
import os

# import labels
labels_200 = pd.read_csv('./data/200_manual_annotations_csv/FinalReferenceStandard200Labels.csv', delimiter = '|',
                        header = 0, index_col=False)

# change column names so it's easier for us
list(labels_200.columns)
labels_200.columns = ['Index', 'Drug_ID', 'Drug_Name', 'Section_LOINC', 'Section_Display_Name',
'MedDRA_PT', 'PT_ID', 'MedDRA_LLT', 'LLT_ID', 'Matching_String',
'UMLS_CUI', 'UMLS_PrefName', 'Flag_1', 'Flag_2']


def generate_subelement(row): # row = row number


    id_reaction = 'AR' + str(int(row[0]) + 1)
    id_norm = id_reaction + str(".N") + str(int(row[0]) + 1)

    if not math.isnan(row.PT_ID):
    	meddra_pt_id = str(int(row.PT_ID))
    else:
    	meddra_pt_id = str(row.PT_ID)
    meddra_pt = str(row.MedDRA_PT).lower()

    Reaction = ET.SubElement(Reactions, "Reaction")
    Reaction.set("id", id_reaction)
    Reaction.set("str", meddra_pt)

    # if row.Drug_Name == 'ACTEMRA' and row.MedDRA_PT.lower().find('alanine') != -1:
    #     print(row)
    #     print(meddra_pt)
    #     print(meddra_pt_id)

    subelement_generated = ET.SubElement(Reaction, "Normalization", id=id_norm, meddra_pt=meddra_pt, meddra_pt_id=meddra_pt_id)
    #Normalization.set("meddra_pt", meddra_pt)
    #Normalization.set("meddra_pt_id", row.llt_id)

    return subelement_generated

# now generate xml

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('--annotations', help="full path to where the manual annotations are", type=str, required=False)
    parser.add_argument('--section', help="part of label (AR, BW, or WP)", type=str, required=True)
    parser.add_argument('--base-dir', type=str, default='.')

    args = parser.parse_args()

    print(f"Loading data...")

    # PARAMETERS
    # TODO: Implement the annotations flag.
    # all_df = pd.read_csv(args.annotations, delimiter = '|', header =0, index_col = False) #pd.read_csv("grouped-mean-bestepoch-bydrug-CB_0-BW-125_222_24_25_1e-06_256_32.csv")
    section = args.section

    if section == "AR":
        all_df = labels_200[labels_200.Section_Display_Name == "ADVERSE REACTIONS"]
    elif section == "BW":
        all_df = labels_200[labels_200.Section_Display_Name == "BOXED WARNINGS"]
    elif section == 'WP':
        all_df = labels_200[labels_200.Section_Display_Name == "WARNINGS AND PRECAUTIONS"]
    else:
        raise Exception(f"Unexpected value provided for section ({section}), expected AR, BW, or WP.")


    # get vector of different drug names
    diff_drug_names = pd.unique(labels_200.Drug_Name)

    for drug_name in tqdm.tqdm(diff_drug_names):

        # start subsetting data
        current_drug = str(drug_name)
        df = all_df[all_df.Drug_Name == current_drug]

        # start to generate xml
        Label = ET.Element("Label")
        Label.set("track", "TAC2017_ADR")
        Label.set("drug", current_drug)

        # the following are placeholders
        Text = ET.SubElement(Label, "Text")
        Section = ET.SubElement(Text, "Section")
        Section.set("id", "S")
        Section.set("name", "adverse reactions")
        Section.set("text", "")

        Section = ET.SubElement(Text, "Section")
        Section.set("id", "S")
        Section.set("name", "adverse reactions")
        Section.set("text", "")

        Section = ET.SubElement(Text, "Section")
        Section.set("id", "S")
        Section.set("name", "adverse reactions")
        Section.set("text", "")

        Mentions = ET.SubElement(Label, "Mentions")
        Mention = ET.SubElement(Mentions, "Mention")
        Mention.set("id", "M")
        Mention.set("section", "")
        Mention.set("type", "AdverseReaction")
        Mention.set("start", "")
        Mention.set("len", "")
        Mention.set("str", "")

        Relations = ET.SubElement(Label, "Relations")
        Relation = ET.SubElement(Relations, "Relation")
        Relation.set("id", "")
        Relation.set("type", "Hypothetical")
        Relation.set("arg1", "")
        Relation.set("arg2", "")
        # end placeholder

        Reactions = ET.SubElement(Label, "Reactions")

        # this is the part that generates the xml
        for row_idx in range(0, len(df)):
            generate_subelement(df.iloc[row_idx])

        tree = ET.ElementTree(Label)

        xmlstr = minidom.parseString(ET.tostring(tree.getroot())).toprettyxml(indent="  ")
        dirpath = args.base_dir + "/data/200_xml/"
        if not os.path.exists(dirpath):
            os.mkdir(dirpath)

        dirpathsec = os.path.join(dirpath, section)
        if not os.path.exists(dirpathsec):
            os.mkdir(dirpathsec)

        filename = os.path.join(dirpathsec, current_drug.upper() + ".xml")
        with open(filename, "w") as f:
            f.write(xmlstr)
        # tree.write(filename, xml_declaration=True, encoding='utf-8')
