ONSIDES_DIR=/data1/home/zietzm/projects/onsides

uv run python \
    ${ONSIDES_DIR}/src/construct_training_data.py \
    --method 14 \
    --nwords 125 \
    --section ALL \
    --prop-before 0.125

uv run python \
    ${ONSIDES_DIR}/src/analyze_results.py \
    --model ${ONSIDES_DIR}/models/bestepoch-bydrug-PMB_14-ALL-125-all_222_24_25_1e-06_256_32.pth \
    --network ${ONSIDES_DIR}/models/microsoft/BiomedNLP-PubMedBERT-base-uncased-abstract \
    --skip-train
