"""
fit_clinicalbert.py

Use clinical bert to classify terms as events or not_events.

@author Nicholas Tatonetti, Tatonetti Lab (heavily inspired by https://towardsdatascience.com/text-classification-with-bert-in-pytorch-887965e5820f)
"""

import torch
import random
from torch import nn
from torch.optim import Adam
from transformers import AutoTokenizer, AutoModel

import argparse
import numpy as np
import pandas as pd
from tqdm import tqdm

labels = {'not_event': 0, 'is_event': 1}
_PRETRAINED_PATH_ = "./models/Bio_ClinicalBERT"

print(f"Loading ClinicalBERT tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(_PRETRAINED_PATH_)

class Dataset(torch.utils.data.Dataset):

    def __init__(self, df, examples_only=False, _max_length=128):

        if not examples_only:
            self.labels = [labels[label] for label in df['class']]
        else:
            self.labels = [0 for _ in range(len(df))]

        self.texts = [tokenizer(text,
                                padding='max_length',
                                max_length=_max_length,
                                truncation=True,
                                return_tensors="pt") for text in df['string']]

    def classes(self):
        return self.labels

    def __len__(self):
        return len(self.labels)

    def get_batch_labels(self, idx):
        # Fetch a batch of labels
        return np.array(self.labels[idx])

    def get_batch_texts(self, idx):
        return self.texts[idx]

    def __getitem__(self, idx):

        batch_texts = self.get_batch_texts(idx)
        batch_y = self.get_batch_labels(idx)

        return batch_texts, batch_y

class ClinicalBertClassifier(nn.Module):

    def __init__(self, dropout=0.5):

        super(ClinicalBertClassifier, self).__init__()

        self.bert = AutoModel.from_pretrained(_PRETRAINED_PATH_)
        self.dropout = nn.Dropout(dropout)
        self.linear = nn.Linear(768, 2)
        self.relu = nn.ReLU()

    def forward(self, input_id, mask):

        _, pooled_output = self.bert(input_ids=input_id, attention_mask=mask, return_dict=False)
        dropout_output = self.dropout(pooled_output)
        linear_output = self.linear(dropout_output)
        final_layer = self.relu(linear_output)

        return final_layer

def train(model, train_data, val_data, learning_rate, epochs, model_filename):

    train, val = Dataset(train_data), Dataset(val_data)

    train_dataloader = torch.utils.data.DataLoader(train, batch_size=128, shuffle=True)
    val_dataloader = torch.utils.data.DataLoader(val, batch_size=128)

    use_cuda = torch.cuda.is_available()
    device = torch.device("cuda" if use_cuda else "cpu")

    print(f"Using device: {device}")

    criterion = nn.CrossEntropyLoss()
    optimizer = Adam(model.parameters(), lr=learning_rate)

    if use_cuda:
        model = model.cuda()
        criterion = criterion.cuda()

    best_val_acc = 0.0

    for epoch_num in range(epochs):

        total_acc_train = 0
        total_loss_train = 0

        for train_input, train_label in tqdm(train_dataloader):

            train_label = train_label.to(device)
            mask = train_input['attention_mask'].to(device)
            input_id = train_input['input_ids'].squeeze(1).to(device)

            output = model(input_id, mask)

            batch_loss = criterion(output, train_label)
            total_loss_train += batch_loss.item()

            acc = (output.argmax(dim=1) == train_label).sum().item()
            total_acc_train += acc

            model.zero_grad()
            batch_loss.backward()
            optimizer.step()

        total_acc_val = 0
        total_loss_val = 0

        with torch.no_grad():

            for val_input, val_label in val_dataloader:

                val_label = val_label.to(device)
                mask = val_input['attention_mask'].to(device)
                input_id = val_input['input_ids'].squeeze(1).to(device)

                output = model(input_id, mask)

                batch_loss = criterion(output, val_label)
                total_loss_val += batch_loss.item()

                acc = (output.argmax(dim=1) == val_label).sum().item()
                total_acc_val += acc

                if acc > best_val_acc:
                    best_val_acc = acc
                    torch.save(model.state_dict(), model_filename)


        print(f'Epochs: {epoch_num + 1} | Train Loss: {total_loss_train / len(train_data): .4f} \
                | Train Accuracy: {total_acc_train / len(train_data): .4f} \
                | Val Loss: {total_loss_val / len(val_data): .4f} \
                | Val Accuracy: {total_acc_val / len(val_data): .4f}')

def evaluate(model, test_data, examples_only=False):

    test = Dataset(test_data, examples_only)

    test_dataloader = torch.utils.data.DataLoader(test, batch_size=128)

    use_cuda = torch.cuda.is_available()
    device = torch.device("cuda" if use_cuda else "cpu")

    if use_cuda:

        model = model.cuda()

    total_acc_test = 0
    outputs = list()

    with torch.no_grad():

        for test_input, test_label in tqdm(test_dataloader):

              test_label = test_label.to(device)
              mask = test_input['attention_mask'].to(device)
              input_id = test_input['input_ids'].squeeze(1).to(device)

              output = model(input_id, mask)
              outputs.append(output)

              acc = (output.argmax(dim=1) == test_label).sum().item()
              total_acc_test += acc

    if not examples_only:
        print(f'Test Accuracy: {total_acc_test / len(test_data): .4f}')
    
    return outputs

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('--ref', help="relative or full path to the reference set", type=str, required=True)

    args = parser.parse_args()

    print(f"Loading reference data...")

    # datapath = './data/clinical_bert_reference_set.txt'
    datapath = args.ref
    df = pd.read_csv(datapath)
    print(df.head())
    print(len(df))

    print("Splitting data into training, validation, and testing...")
    refset = int(args.ref.split('ref')[1].split('_')[0])
    np_random_seed = 222
    random_state = 24
    np.random.seed(np_random_seed)

    # randomly select by row
    #df_train, df_val, df_test = np.split(df.sample(frac=1, random_state=random_state),
    #                                     [int(0.8*len(df)), int(0.9*len(df))])

    # randomly select by drug/label
    druglist = sorted(set(df['drug']))

    random.seed(np_random_seed)
    random.shuffle(druglist)

    drugs_train, drugs_val, drugs_test = np.split(druglist, [int(0.8*len(druglist)), int(0.9*len(druglist))])

    print(f"Split labels in train, val, test by drug:")
    print(len(drugs_train), len(drugs_val), len(drugs_test))

    df_train = df[df['drug'].isin(drugs_train)]
    df_val = df[df['drug'].isin(drugs_val)]
    df_test = df[df['drug'].isin(drugs_test)]

    print(f"Resulting dataframes have sizes:")
    print(len(df_train), len(df_val), len(df_test))

    EPOCHS = 25
    model = ClinicalBertClassifier()
    LR = 1e-6

    print("Fitting the model...")
    model_filename = f'./models/final-bydrug_{refset}_{np_random_seed}_{random_state}_{EPOCHS}_{LR}_BestEpoch.pth'

    train(model, df_train, df_val, LR, EPOCHS, model_filename)

    print("Saving the model to file...")

    torch.save(model.state_dict(), f'./models/final-bydrug_{refset}_{np_random_seed}_{random_state}_{EPOCHS}_{LR}.pth')

    print("Loading the model from file...")

    loaded_model = ClinicalBertClassifier()
    loaded_model.load_state_dict(torch.load(f'./models/final-bydrug_{refset}_{np_random_seed}_{random_state}_{EPOCHS}_{LR}.pth'))

    print("Evaluating the model on the held out test set...")
    evaluate(loaded_model, df_test)
