import logging
from os import PathLike
from pathlib import Path

import numpy as np
import torch
import tqdm.auto as tqdm
from torch import nn
from transformers import AutoModel, AutoTokenizer

logger = logging.getLogger(__name__)


class ClinicalBertClassifier(nn.Module):
    def __init__(self, pretrained_model_path: PathLike, dropout=0.5):
        super().__init__()
        self.bert = AutoModel.from_pretrained(pretrained_model_path)
        self.dropout = nn.Dropout(dropout)
        self.linear = nn.Linear(768, 2)
        self.relu = nn.ReLU()

    def forward(self, input_id, mask):
        _, pooled_output = self.bert(
            input_ids=input_id, attention_mask=mask, return_dict=False
        )
        dropout_output = self.dropout(pooled_output)
        linear_output = self.linear(dropout_output)
        final_layer = self.relu(linear_output)
        return final_layer


def evaluate(
    model: ClinicalBertClassifier,
    tokenizer_path: Path,
    texts: list[str],
    max_length: int,
    batch_size: int,
) -> list[float]:
    model.eval()
    if torch.cuda.is_available():
        device = torch.device("cuda")
        model = model.cuda()
    else:
        device = torch.device("cpu")

    dataset = Dataset(texts, tokenizer_path, max_length=max_length)
    dataloader = torch.utils.data.DataLoader(dataset, batch_size=batch_size)

    total_acc_test = 0
    outputs = list()

    with torch.no_grad():
        for test_input, test_label in tqdm.tqdm(dataloader):
            test_label = test_label.to(device)
            mask = test_input["attention_mask"].to(device)
            input_id = test_input["input_ids"].squeeze(1).to(device)

            output = model(input_id, mask)
            outputs.append(output)

            acc = (output.argmax(dim=1) == test_label).sum().item()
            total_acc_test += acc

    print(f"Test Accuracy: {total_acc_test / len(texts): .4f}")
    # TODO: Format the outputs properly
    npoutputs = [x.cpu().detach().numpy() for x in outputs]
    predictions = np.vstack(npoutputs)
    print(f"Predictions have shape: {predictions.shape}")
    return predictions.ravel().tolist()


class Dataset(torch.utils.data.Dataset):
    def __init__(self, texts: list[str], tokenizer_path: Path, max_length: int = 128):
        self.labels = [0 for _ in texts]

        logger.info(f"Loading tokenizer from {tokenizer_path}...")
        self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_path)

        logger.info("Tokenizing texts...")
        self.texts = [
            self.tokenizer(
                text,
                padding="max_length",
                max_length=max_length,
                truncation=True,
                return_tensors="pt",
            )
            for text in texts
        ]

    def classes(self):
        return self.labels

    def __len__(self):
        return len(self.labels)

    def get_batch_labels(self, idx):
        return np.array(self.labels[idx])

    def get_batch_texts(self, idx):
        return self.texts[idx]

    def __getitem__(self, idx):
        batch_texts = self.get_batch_texts(idx)
        batch_y = self.get_batch_labels(idx)
        return batch_texts, batch_y
