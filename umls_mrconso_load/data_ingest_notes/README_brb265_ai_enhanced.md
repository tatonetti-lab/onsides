# etl 02/26/2026

## Objective
Extract `MRCONSO.RRF` from UMLS 2025AB full release without using MetamorphoSys GUI.

Working directory:

/mnt/data/import/umls/2025AB-full

---

## Step 1 — Extract raw META payload from `.nlm` archives

cd /mnt/data/import/umls/2025AB-full

mkdir meta_raw
cd meta_raw

jar xf ../2025ab-1-meta.nlm
jar xf ../2025ab-2-meta.nlm

This produced:

meta_raw/2025AB/META/

Containing split gzip components:

MRCONSO.RRF.aa.gz
MRCONSO.RRF.ab.gz
MRCONSO.RRF.ac.gz

---

## Step 2 — Assemble and decompress MRCONSO

Working directory:

/mnt/data/import/umls/2025AB-full/meta_raw/2025AB/META

Command:

# Build MRCONSO.RRF (single text file)
cat MRCONSO.RRF.*.gz | gunzip -c > MRCONSO.RRF

# sanity
ls -lh MRCONSO.RRF
head -n 3 MRCONSO.RRF | cat -A

Result:

MRCONSO.RRF  (2,249,632,549 bytes)

---

## Step 3 — Create stable target directory

From META directory:

mkdir ../../../mrconso
mv ./MRCONSO.RRF ../../../mrconso

Final location:

/mnt/data/import/umls/2025AB-full/mrconso/MRCONSO.RRF

Directory state:

drwxrwsr-x mrconso/
-rw-rw-r-- MRCONSO.RRF 2249632549 bytes

---

## Final Layout

2025AB-full/
├── meta_raw/
│   └── 2025AB/META/ (gz components remain here)
├── mrconso/
│   └── MRCONSO.RRF
├── 2025ab-1-meta.nlm
├── 2025ab-2-meta.nlm
└── mmsys/

---

## Notes

• Extraction performed via direct `jar xf`, bypassing MetamorphoSys  
• MRCONSO reconstructed from split gzip stream (.aa/.ab/.ac)  
• No filtering applied (full multilingual MRCONSO retained)  
• Ready for Postgres COPY load  