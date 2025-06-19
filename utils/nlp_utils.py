# import spacy
import json
import os
import requests
import unicodedata
from dotenv import load_dotenv
from transformers import pipeline

load_dotenv()

# Load spaCy NER
# nlp_spacy = spacy.load("en_core_web_sm")

# Use Hugging Face Inference API for classification
MODEL_PATH = "aarya1708/tripgenie-intent-classifier"
# HF_TOKEN = os.getenv("HF_TOKEN")  # optional, if rate limited

classifier = pipeline(
    "text-classification",
    model=MODEL_PATH,
    # token=HF_TOKEN  # remove if not using private model or no token
)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEONAMES_USERNAME = os.getenv("GEONAMES_USERNAME")

def normalize_text(text):
    text = unicodedata.normalize('NFKD', text)
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return text.lower()

def predict_intent(text):
    try:
        result = classifier(text)[0]
        return result["label"]
    except Exception as e:
        print("Hugging Face API error:", e)
        return "unknown"

def validate_location_with_google(place_name):
    url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
    params = {
        "query": place_name,
        "key": GOOGLE_API_KEY
    }
    try:
        response = requests.get(url, params=params)
        results = response.json().get("results", [])
        if results:
            return results[0].get("formatted_address")
    except Exception as e:
        print("Google validation error:", e)
    return None

def extract_location(text):
    # Try GeoNames first
    tokens = text.split()
    for token in tokens:
        url = f"http://api.geonames.org/searchJSON?q={token}&maxRows=1&username={GEONAMES_USERNAME}"
        try:
            resp = requests.get(url, timeout=5)
            data = resp.json()
            if data.get("totalResultsCount", 0) > 0:
                candidate_location = data["geonames"][0]["name"]
                if token.lower() == normalize_text(candidate_location):
                    return candidate_location
        except Exception as e:
            print("GeoNames detection error:", e)

    # Fallback to spaCy NER
    # doc = nlp_spacy(text)
    # for ent in doc.ents:
    #     if ent.label_ in ["GPE", "LOC", "ORG"]:
    #         return ent.text

    return None

def analyze_text(text):
    return {
        "intent": predict_intent(text),
        "location": extract_location(text)
    }

# Example usage (uncomment to test)
# print(analyze_text("find me cafes in pune"))
