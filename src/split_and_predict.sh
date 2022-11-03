# Bash script to split the example sentences files into 100MB chunks
# and run predict.py on each part individually.
# E.g.
# bash src/split_and_predict.sh data/spl/rx/dm_spl_release_human_rx_part5 14 125 AR 0 ./models/final-bydrug-PMB_14-AR-125-all_222_24_25_1e-05_256_32.pth final-bydrug-PMB-sentences-rx_app14-AR-125-all_ref14-AR_222_24_25_1e-05_256_32.csv.gz

labels_dir=$1
method=$2
nwords=$3
section=$4
gpu=$5
model=$6
output=$7

echo "labels_dir =" $labels_dir
echo "method =" $method
echo "nwords =" $nwords
echo "section =" $section
echo "gpu =" $gpu
echo "model =" $model
echo "output =" $output

echo "Splitting the large files for faster processing..."
echo "  Changing directory to " $labels_dir
cd $labels_dir
echo "  Making splits subdirectory"
mkdir -p splits
echo "  Unzipping the features file"
gunzip sentences-rx_method$method\_nwords$nwords\_clinical_bert_application_set_$section.txt.gz
echo "  Splitting files into 100MB chunks"
tail -n +2 sentences-rx_method$method\_nwords$nwords\_clinical_bert_application_set_$section.txt | gsplit -d -C 100m - --filter='sh -c "{ head -n1 sentences-rx_method'$method'_nwords'$nwords'_clinical_bert_application_set_'$section'.txt; cat; } > $FILE"' splits/sentences-rx_method$method\_nwords$nwords\_clinical_bert_application_set_$section\_split
echo "  Rezipping the features file"
gzip sentences-rx_method$method\_nwords$nwords\_clinical_bert_application_set_$section.txt
cd -

echo "Running predict.py on each split..."
for f in $labels_dir/splits/*
do
  echo "  " CUDA_VISIBLE_DEVICES=$gpu python3 src/predict.py --model $model --examples $f
  CUDA_VISIBLE_DEVICES=$gpu python3 src/predict.py --model $model --examples $f
done

echo "Recombining the results and archiving..."
echo "  Changing directory to " $labels_dir
cd $labels_dir
echo "  Concatenating the csv.gz files together"
zcat splits/*.csv.gz | gzip > $output
echo "  Removing the split files"
rm -rf splits
cd -

echo "Finished."
