# OnSIDES-INTL Database Generation Walkthrough

Here, we generate databases mirroring the OnSIDES database (which extracts ADE data from US FDA SPL drug labels) from UK (EMC), EU (EMA), and Japan (PMDA) drug labels. 

While we follow a similar ADE extraction/prediction philosophy to OnSIDES, as the raw label are formatted in a slightly different manner for each nation/region, the technical workflow is slightly adjusted to each nation. As such, we will describe the process of generating the databases for each individual database. Please skip to the details for the specific database you are interested in. 

If you are interested in how the OnSIDES database extracted from US FDA drug labels is generated, please refer to [OnSIDES](https://github.com/tatonetti-lab/onsides/blob/main/DATABASE.md)

- [OnSIDES-UK](onsides_uk/DATABASE_UK.md)
- [OnSIDES-EU](onsides_eu/DATABASE_EU.md)
- [OnSIDES-JP](onsides_uk/DATABASE_JP.md)

general notes : 
- each `data` subfolder in each of the onsides-intl folders (onsides-eu/jp/uk) houses all of the intermediate data generated during the process of database generation.
- each `notebooks` subfolder contains the code required to construct the databases from scratch, mirroring the src code.
- each `src` subfolder contains the python code to construct the databases from scratch

technical notes : 
- all of the code should be able to run on a standard laptop locally, with the exception of the OnSIDES prediction model (which utilizes a GPU).