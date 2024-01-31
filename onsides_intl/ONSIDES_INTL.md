# OnSIDES-INTL 

Here, we generate databases mirroring the OnSIDES database (which extracts ADE data from US FDA SPL drug labels) from UK (EMC), EU (EMA), and Japan (PMDA) drug labels. We have also generated uniformly processed drug label text data from these drug labels that can be used as raw, structured data to train a myriad of machine learning models. 

While we follow a similar ADE extraction/prediction philosophy to OnSIDES, as the raw label are formatted in a slightly different manner for each nation/region, the technical workflow is slightly adjusted to each nation. The detailed methods are described in [DATABASE_INTL](./DATABASE_INTL.md). 

If you are interested in how the primary OnSIDES database (FDA drug labels) is generated, please refer to the main [OnSIDES](https://github.com/tatonetti-lab/onsides/blob/main/DATABASE.md) page. 

## Pages

A quick guide to what each file contains. 
- How we've generated each database - [DATABASE_INTL]('./DATABASE_INTL.md')
- How the files in each database are formatted - [SCHEMA_INTL](./SCHEMA_INTL.md)
- How each country standardizes their drug label formats - [LABELSCHEMA_INTL](LABELDATA_INTL.md)
- How the processed drug label XML/CSV data is formatted - [LABELDATA_INTL](LABELDATA_INTL.md)

## Questions 

This portion of OnSIDES is under active development. If you notice any errors, problems, and areas of improvement, we'd love to get in touch + collaborate! Please reach out to Dr. Tatonetti via [email](https://tatonettilab.org/people/) or [X (Twitter)](http://twitter.com/nicktatonetti).