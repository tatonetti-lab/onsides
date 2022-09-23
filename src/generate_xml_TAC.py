# generates xml file for outputs
# make sure the data folder xml_output exists under ./data/
# last edited 09/23/2022

import xml.etree.ElementTree as ET
import pandas as pd
import csv
import argparse

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

def load_meddra2(): 
	# this creates 2 additional dictionaries that will tell you if something is PT/LLT 
	# and also what the PT match to the LLTs are

	meddra_table = pd.read_csv('./data/meddra_llt_pt_map.txt', sep = '|')
	meddra_table.head()

	meddra_table['concept name'] = "LLT"

	meddra_table.loc[meddra_table['llt_concept_code'] == meddra_table['pt_concept_code'] , 'concept name'] = "PT"

	#create dict based on LLT concept code
	dict_meddra_concept= meddra_table.set_index('llt_concept_code').to_dict()['concept name']

	# create dict based on if something is a LLT, we want the PT that goes along with it
	dict_llt_to_pt = meddra_table.set_index('llt_concept_code').to_dict()['pt_concept_code']

	return dict_meddra_concept, dict_llt_to_pt

def generate_subelement(row): # row = row index
	id_reaction = section + str(row[0] + 1) # the id's dont get eval'd so it doesn't matter that much
	id_norm = id_reaction + str(".N") + str(row[0] + 1)
	meddra_pt_id = str(row.llt_id)
	meddra_pt = meddra_dict.get(str(row.llt_id))
	meddra_pt = meddra_pt.lower()

	# pt or llt?
	meddra_type = dict_meddra_concept.get(row.llt_id)

	Reaction = ET.SubElement(Reactions, "Reaction")
	Reaction.set("id", id_reaction) 
	Reaction.set("str", meddra_pt)

	if meddra_type == "LLT":
		pt_match = str(dict_llt_to_pt.get(row.llt_id)) # this gives the id
		
		pt_string = meddra_dict.get(str(pt_match)) # this gives the string version of the pt

		subelement_generated = ET.SubElement(Reaction, "Normalization", id=id_norm, 
											 meddra_pt=pt_string, meddra_pt_id=pt_match,
											meddra_llt_id = meddra_pt_id, meddra_llt = meddra_pt)
	else:
		subelement_generated = ET.SubElement(Reaction, "Normalization", id=id_norm, 
			meddra_pt=meddra_pt, meddra_pt_id=meddra_pt_id)

	return subelement_generated

if __name__ == "__main__": 

	parser = argparse.ArgumentParser()
	parser.add_argument('--results', help="full path to the model results", type=str, required=True)
	parser.add_argument('--threshold', help="threshold for positive result", type=float, default=2.54717718064785)
	parser.add_argument('--section', help="part of label (AR, BW, etc)", type=str, default='AR')
	parser.add_argument('--base-dir', type=str, default='.')

	args = parser.parse_args()

	print(f"Loading data...")

	meddra_dict = load_meddra()
	dict_meddra_concept, dict_llt_to_pt = load_meddra2()


	# PARAMETERS 
	all_df = pd.read_csv(args.results) #pd.read_csv("grouped-mean-bestepoch-bydrug-CB_0-BW-125_222_24_25_1e-06_256_32.csv")
	all_df = all_df[all_df["split"] == "test"] # subset for only test data
	all_df = all_df[all_df["scored"] == "scored"] # subset for only scored
	#all_df = all_df[all_df["class"] == "is_event"] 

	print(all_df.head())

	threshold = args.threshold   # this will need to be changed, as well as the pred0 (should be pred1 i think) -- can change this into a param? 
	section = args.section

	# get vector of different drug names
	diff_drug_names = pd.unique(all_df.drug)

	for drug_name in diff_drug_names: 
		
		# start subsetting data
		current_drug = str(drug_name)
		df = all_df[all_df.drug == current_drug]

		# subset data by the threshold
		df = df[(df['Pred1'] > threshold)]
		
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
		filename = args.base_dir + "/data/xml_output/" + current_drug + ".xml"
		tree.write(filename, xml_declaration=True, encoding='utf-8')


