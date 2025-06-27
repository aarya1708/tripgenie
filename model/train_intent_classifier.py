import pandas as pd
import torch
from torch.utils.data import Dataset
from transformers import BertTokenizer, BertForSequenceClassification, Trainer, TrainingArguments
import os
import json
import pickle

# Paths
DATA_PATH = "intent_dataset.csv"
SAVE_DIR = "./intent-model/final"
os.makedirs(SAVE_DIR, exist_ok=True)

# Load data
df = pd.read_csv(DATA_PATH)
# print(df.head)

# Encode labels
unique_labels = sorted(df['label'].unique())
label2id = {label: i for i, label in enumerate(unique_labels)}
id2label = {i: label for label, i in label2id.items()}

# Save mappings
with open(os.path.join(SAVE_DIR, "label_encoder.pkl"), "wb") as f:
    pickle.dump(label2id, f)
with open(os.path.join(SAVE_DIR, "id2label.json"), "w") as f:
    json.dump(id2label, f)

# Tokenizer
tokenizer = BertTokenizer.from_pretrained("bert-base-uncased")

# Dataset
class IntentDataset(Dataset):
    def __init__(self, df):
        self.encodings = tokenizer(df['text'].tolist(), truncation=True, padding=True)
        self.labels = [label2id[label] for label in df['label']]

    def __getitem__(self, idx):
        item = {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}
        item["labels"] = torch.tensor(self.labels[idx])
        return item

    def __len__(self):
        return len(self.labels)

dataset = IntentDataset(df)

# Model
model = BertForSequenceClassification.from_pretrained(
    "bert-base-uncased",
    num_labels=len(label2id),
    id2label=id2label,
    label2id=label2id
)

# Training
training_args = TrainingArguments(
    output_dir=SAVE_DIR,
    num_train_epochs=5,
    per_device_train_batch_size=4,
    logging_dir=f"{SAVE_DIR}/logs",
    logging_steps=1,
    save_strategy="no"
)

trainer = Trainer(
    model=model,
    args=training_args,
    train_dataset=dataset
)

trainer.train()
model.save_pretrained(SAVE_DIR)
tokenizer.save_pretrained(SAVE_DIR)

print("✅ Training complete and model saved!")
