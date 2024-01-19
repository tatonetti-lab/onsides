# Python imports

import argparse
from pathlib import Path
import logging
from IPython.core.display import HTML

# Third-party imports
import torch
import pandas as pd
from scipy.special import softmax
import numpy as np
import matplotlib.pyplot as plt
import shap
from tqdm import tqdm

# Project imports
import fit_clinicalbert as cb
from database import run_query


def get_predict_fn(model, device, batch_size=32):
    """Return OnSIDES prediction function

    Args:
        model: Model object
        device: Device identifier to run model on
        batch_size (int, optional): Model batch size. Defaults to 32.
    """
    def predict_fn(string_list):
        string_tokens_input_ids = []
        string_tokens_masks = []
        for string in string_list:
            tokens = cb.Dataset.tokenizer(string,
                                          padding='max_length',
                                          max_length=256,
                                          truncation=True,
                                          return_tensors="pt")

            input_ids = tokens['input_ids'].to(device)
            mask = tokens['attention_mask'].to(device)

            string_tokens_input_ids.append(input_ids)
            string_tokens_masks.append(mask)

        string_tokens_input_ids = torch.cat(string_tokens_input_ids, dim=0)
        string_tokens_masks = torch.cat(string_tokens_masks, dim=0)

        preds = []
        for batch_i in range(0, len(string_list), batch_size):
            batch_string_tokens_input_ids = string_tokens_input_ids[
                batch_i:batch_i + batch_size]
            batch_string_tokens_masks = string_tokens_masks[batch_i:batch_i +
                                                            batch_size]

            batch_preds = model(
                batch_string_tokens_input_ids,
                batch_string_tokens_masks).cpu().detach().numpy()
            preds.append(batch_preds)

        preds = np.concatenate(preds)
        preds = softmax(preds, axis=1)

        return preds

    return predict_fn


def shap_explanation(string_list, model, device, dest):
    """ Explain SHAP predictions with local and global plots.

    Args:
        string_list (list(str)): Drug label strings to pass as input
        model (torch.Model): Torch model object
        device (_type_): Device identifier to run model on
        dest (str): Destination folder to save explanation output files
    """
    predict_fn = get_predict_fn(model, device, batch_size=32)
    explainer = shap.Explainer(
        predict_fn, masker=shap.maskers.Text(tokenizer=cb.Dataset.tokenizer))

    shap_values = explainer(string_list)

    # Local Text
    shap_html = HTML(shap.plots.text(shap_values[0, :, 1], display=False)).data
    with open(dest / 'shap_text_local.html', 'w') as f:
        f.write(shap_html)

    # Local Box
    shap.plots.bar(shap_values[0, :, 1], show=False)
    plt.tight_layout()
    plt.savefig(dest / 'shap_box_local.png')
    plt.clf()

    # Global Box

    shap.plots.bar(shap_values[:, :, 1].mean(0), show=False)
    plt.tight_layout()
    plt.savefig(dest / 'shap_box_global.png')
    plt.clf()



def list_meddra_socs():
    """Get a list of MedDRA SOCs concepts from an OMOP database.

    Returns:
        pandas.DataFrame: A dataframe containing MedDRA SOC concepts
    """    

    q = f"""
    SELECT
        c.concept_id, c.concept_name
    FROM concept c
    WHERE c.vocabulary_id = 'MedDRA'
        AND c.concept_class_id = 'SOC'
    """

    meddra_socs = run_query(q)

    return meddra_socs


def get_meddra_class(meddra_concept_id):
    """Get a list of MedDRA preferred terms from an ancestor concept

    Args:
        meddra_concept_id (_type_): Ancestor MedDRA concept ID

    Returns:
        pandas.DataFrame: A dataframe containing MedDRA preferred term concepts
    """    

    q = f"""
        SELECT
            c.*
        FROM concept base_c
        JOIN concept_ancestor ca
            ON ca.ancestor_concept_id = base_c.concept_id
        JOIN concept c
            ON c.concept_id = ca.descendant_concept_id
        WHERE base_c.concept_id = {meddra_concept_id}
            AND base_c.vocabulary_id = 'MedDRA'
            AND c.vocabulary_id = 'MedDRA'
            AND c.concept_class_id = 'PT'
        """

    meddra_concepts = run_query(q)
    meddra_concepts['concept_code'] = meddra_concepts['concept_code'].astype(
        int)

    return meddra_concepts


def main(test_samples_path, network_path, model_path, dest):
    dest = Path(dest)
    if not Path.exists(dest):
        Path.mkdir(dest, exist_ok=True)

    device = torch.device('cuda:0')

    # initailize Dataset.tokenizer
    logging.info('Initializing dataset tokenizer')
    cb.Dataset.set_tokenizer(network_path)

    logging.info('Loading clinical bert')
    model = cb.ClinicalBertClassifier(network_path)
    model.load_state_dict(torch.load(model_path))
    model = model.to(device)

    model.eval()
    torch.no_grad()

    # get random test samples
    test_samples = pd.read_csv(test_samples_path)

    socs = list_meddra_socs()
    pbar = tqdm(list(socs.iterrows()))
    for _, soc in pbar:
        soc_concept_id = soc['concept_id']
        soc_concept_name = soc['concept_name']
        pbar.set_description(f"SOC: {soc_concept_name}")
        meddra_concepts = get_meddra_class(soc_concept_id)
        meddra_concept_codes = meddra_concepts['concept_code']

        soc_test_samples = test_samples[
            (test_samples['class'] == 'is_event')
            & (test_samples['pt_meddra_id'].isin(meddra_concept_codes))
            & (test_samples['tac'] == 'test')]
        

        if len(soc_test_samples) > 0:
            sample_size = min(50, len(soc_test_samples))
            soc_test_samples = soc_test_samples.sample(sample_size)['string']

            sub_dest = Path(dest) / soc_concept_name
            if not Path.exists(sub_dest):
                Path.mkdir(sub_dest, exist_ok=True)
            shap_explanation(soc_test_samples, model, device, sub_dest)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Explain output of an LSTM model")
    parser.add_argument(metavar="test_samples", dest="test_samples_path", help="Path to training/test data")
    parser.add_argument("network_path", help="Path to network used for tokenization")
    parser.add_argument("model_path", help="Path to PyTorch model file")
    parser.add_argument("-d",
                        "--dest",
                        default="output",
                        help="Path to save output")

    args = parser.parse_args()

    main(args.test_samples_path, args.network_path, args.model_path, args.dest)
