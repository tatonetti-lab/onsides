## Manually Annotated Adverse Drug Event Label Dataset

Following a similar approach to [Denmer-Fushman et al.](https://www.nature.com/articles/sdata20181), we created a dataset of 200 randomly sampled labels for each of the UK, EU, Japan drug labels, and 200 randomly sampled labels for the pediatric sections in the US/UK/EU/Japan drug labels, and manually reviewed and annotated the adverse drug events mentioned in these drug labels. To the best of our knowledge, this dataset is the first pilot dataset containing standardised, manually verified information about adverse reactions from non-FDA drug labels. Here, we will describe the steps taken to generate this data, and the formatting of the files. We hope that this data can be used as a resource to train further models and text mining tools on a larger variety of international drug labels and from other clinical/pharmaceutical text.

For convenience, we additionally have reformatted [Denmer-Fushman et al.](https://www.nature.com/articles/sdata20181) annotations in the format described below. When using these annotated labels, please refer and acknowledge this publication. 

----

### Annotation Method

1. Randomly sample 200 labels from each drug label type. 
2. Next, extract the relevant section of the drug label. For the pediatric warnings, we extract the specific section within the general relevant section. 
    - US : 
        - (General) [Demner-Fushman et al.](https://www.nature.com/articles/sdata20181)
        - (Pediatric) `Use in Specific Populations`
    - UK & EU : 
        - (General) `4.8 Undesirable Effects`
        - (Pediatric) `4.4 Special warnings and precautions for use`
    - Japan : 
        - (General) `11. 副作用`
        - (Pediatric) `9. 特定の背景を有する患者に関する注意`
3. After extracting the section, verify that the specific section contains relevant information. 
    - Many pediatric sections contain a statement similar to "this medication has not been assessed for safety in pediatric patients". We removed these labels, and re-sampled drug labels to construct datasets of 200 labels with relevant information. 
3. We manually reviewed and annotated each drug label section text for any adverse event mentions using [doccano](https://github.com/doccano/doccano), a open-source text annotation tool. 
4. Then, to standardize the data, we map all of the adverse event mentions to Medical Dictionary for Regulatory Activities (MedDRA) terms. 
    - For the Japanese dataset, we mapped the mentions to MedDRA-J, a dictionary mapping MedDRA to Japanese terms.

---

### File Format

All of the files are compiled by-dataset, and in a [JSONL format](https://jsonlines.org/), with each line consisting of an individual drug label. For each drug label, we format it as follows

```
{'label_id': ###, 
 'section_name': ###, 
 'section_text': ###, 
 'adverse_events': ['adverse_event_term', 
                    'mapped_meddra_pt_term',
                    'mapped_meddra_pt_id',
                    'mapped_meddra_llt_term',
                    'mapped_meddra_llt_id',
                    'start_location_in_text',
                    'term_length']}
```

For example, the annotation for X is presented as follows
```
{'label_id': 'XEOMIN',
 'section_name': 'warnings and precautions',
 'section_text': '5 WARNINGS AND PRECAUTIONS\n\n\n\n  EXCERPT:    ...
 'adverse_events': [['dysphagia',
   'Dysphagia',
   10013950.0,
   None,
   None,
   '837',
   '9']...]}
```

If any adverse event mentions do not have a MedDRA PT/LLT code available, the MedDRA code is left as `None`. The MedDRA codes are mapped at either the Lowest Level Terms (LLT) and Preferred Terms (PT) levels. If needed, a LLT to PT map, as used to generate the OnSIDES database, is provided in the [example data directory](https://github.com/tatonetti-lab/onsides/releases/download/v2.0.0/data.zip). 

---

### **Note**

This dataset is not without its limitations. It must be noted that the pediatric adverse reaction mentions are strictly from the "special populations"-like sections from each of the drug labels. Many pediatric adverse reactions have commonalities with adult adverse reactions, and will be mentioned in other sections, making these annotations not wholly comprehensive of all relevant adverse reactions - only the adverse reactions known and considered *specific* to pediatric patients, and those that have been noted in clinical trials on pediatric populations or juvenile animals. 

Additionally, while we have made our best efforts to ensure its accuracy, this has not been validated by a medical professional. Any errors found in the dataset will be noted here, and the latest dataset can be found in this repository. This data is under active development, and we hope to add further annotated datasets to facilitate further methods development in this domain.

If you find an error in the data, or have any suggestions on how to improve this dataset,  please raise an issue in this repository or contact Dr. Tatonetti via [email](https://tatonettilab.org/people/) or [Twitter](http://twitter.com/nicktatonetti).