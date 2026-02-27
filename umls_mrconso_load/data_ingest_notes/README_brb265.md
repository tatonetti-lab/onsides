# etl 02/26/2026






```sh
#/mnt/data/import/umls/2025AB-full/meta_raw/2025AB/META

 

# Build MRCONSO.RRF (single text file)
cat MRCONSO.RRF.*.gz | gunzip -c > MRCONSO.RRF

# sanity
ls -lh MRCONSO.RRF
head -n 3 MRCONSO.RRF | cat -A

mkdir ../../../mrconso

mv ./MRCONSO.RRF ../../../mrconso

```