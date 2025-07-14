from transformers import BertTokenizer, BertForSequenceClassification
import torch
import spacy
import json
import os
import requests
import unicodedata
from dotenv import load_dotenv
import torch.nn.functional as F
load_dotenv()

# Load spaCy NER
nlp_spacy = spacy.load("en_core_web_sm")

# Load tokenizer and model
MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'model', 'intent-model', 'final'))
tokenizer = BertTokenizer.from_pretrained(MODEL_PATH)
model = BertForSequenceClassification.from_pretrained(MODEL_PATH)

# Load label mappings
with open(f"{MODEL_PATH}/id2label.json") as f:
    id2label = json.load(f)
id2label = {int(k): v for k, v in id2label.items()}

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEONAMES_USERNAME = os.getenv("GEONAMES_USERNAME")

def normalize_text(text):
    # Normalize Unicode (NFKD separates accents from base characters)
    text = unicodedata.normalize('NFKD', text)
    # Remove accents by filtering out combining characters
    text = ''.join(c for c in text if not unicodedata.combining(c))
    # Convert to lowercase
    return text.lower()

def predict_intent(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)
    with torch.no_grad():
        outputs = model(**inputs)

    probs = F.softmax(outputs.logits, dim=1)
    predicted_class_id = torch.argmax(outputs.logits, dim=1).item()
    confidence_score = probs[0][predicted_class_id].item()
    # print(confidence_score)
    
    return id2label[predicted_class_id]

def extract_location(text):
    # Try GeoNames first to detect if any token is a valid location
    tokens = text.split()
    for token in tokens:
        #check for bugged location words
        if token.lower() not in ["cafe", "want", "petroll", "kafe", "gaming", "have", "burgers", "coffee"]: 
            url = f"http://api.geonames.org/searchJSON?q={token}&maxRows=2&username={GEONAMES_USERNAME}"
            try:
                resp = requests.get(url, timeout=10)
                data = resp.json()
                # print(data)
                if data.get("totalResultsCount", 0) > 0:
                    candidate_location = data["geonames"][0]["name"]
                    candidate_location2 = data["geonames"][1]["name"]
                    # print(candidate_location)
                    # Validate with Google
                    # print(token)

                    if token.lower() == normalize_text(candidate_location) or token.lower() == normalize_text(candidate_location2):
                        return token
                else:
                    print("Location not found in Geonames")
            except Exception as e:
                print("GeoNames detection error:", e)

    # Fallback to spaCy
    doc = nlp_spacy(text)
    for ent in doc.ents:
        if ent.label_ in ["GPE", "LOC", "ORG"] and ent.text.lower() not in ["cafe", "want", "petroll"]:
            print("Location found in spacy")
            return ent.text

    return None

def analyze_text(text):
    return {
        "intent": predict_intent(text),
        "location": extract_location(text)
    }

# print(analyze_text("paintings near me"))