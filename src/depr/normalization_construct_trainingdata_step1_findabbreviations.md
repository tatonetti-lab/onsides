# Perform preprocessing

These preprocessing steps are taken from Ji, et al. BERT-based Ranking for
Biomedical Entity Normalization (https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7233044/pdf/3269841.pdf)
See pp 271 for preprocessing steps

## Abbreviation Resolution
Ab3p is a C++ program for identifying abbreviations in free-text. See https://github.com/ncbi-nlp/Ab3P.

I could only get this to successfully compile on a linux machine. Therefore as a
preliminary step we are going to identify all of the abbreviations mentioned in each of the
xml files and then construct a reference file of abbreviations to use when constructing
the training data. We can incorporate this step of abbreviation identification (and
  then subsequent replacement with the term) into our overall process, likely when
  constructing the training/application data.

To generate the reference file using Ab3p:

```
for f in ~/Projects/onsides/data/train_xml/*.xml
do
  echo "./identify_abbr $f 2>/dev/null | grep '[|]' > $f-abbrev.txt"
done | bash
```

```
for f in ~/Projects/onsides/data/gold_xml/*.xml
do
  echo "./identify_abbr $f 2>/dev/null | grep '[|]' > $f-abbrev.txt"
done | bash
```
