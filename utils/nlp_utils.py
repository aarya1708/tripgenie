import spacy
import json
import os
import requests
import unicodedata
from dotenv import load_dotenv
load_dotenv()
# Load spaCy NER
nlp_spacy = spacy.load("en_core_web_sm")

HF_MODEL_URL = "https://api-inference.huggingface.co/models/aarya1708/tripgenie-intent-classifier"
HF_TOKEN = os.getenv("HF_API_TOKEN")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GEONAMES_USERNAME = os.getenv("OPEN_ROUTER_API_KEY")

def normalize_text(text):
    # Normalize Unicode (NFKD separates accents from base characters)
    text = unicodedata.normalize('NFKD', text)
    # Remove accents by filtering out combining characters
    text = ''.join(c for c in text if not unicodedata.combining(c))
    # Convert to lowercase
    return text.lower()

def predict_intent(text):
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "inputs": text
    }

    try:
        response = requests.post(HF_MODEL_URL, headers=headers, json=payload)
        response.raise_for_status()
        result = response.json()

        if isinstance(result, list) and len(result) > 0:
            return result[0].get("label", "unknown")
        else:
            print("⚠️ Unexpected model response:", result)
            return "unknown"

    except Exception as e:
        print("❌ Error in intent prediction:", e)
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
    # Try GeoNames first to detect if any token is a valid location
    tokens = text.split()
    for token in tokens:
        url = f"http://api.geonames.org/searchJSON?q={token}&maxRows=1&username={GEONAMES_USERNAME}"
        try:
            resp = requests.get(url, timeout=5)
            data = resp.json()
            # print(data['geonames'][0]['name'])
            if data.get("totalResultsCount", 0) > 0:
                candidate_location = data["geonames"][0]["name"]
                # print(candidate_location)
                # Validate with Google
                # print(token)

                if token.lower() == normalize_text(candidate_location):
                    return candidate_location
            else:
                print("noooooooooooo")
        except Exception as e:
            print("GeoNames detection error:", e)

    # Fallback to spaCy
    doc = nlp_spacy(text)
    for ent in doc.ents:
        if ent.label_ in ["GPE", "LOC", "ORG"]:
            print("hi")
            return ent.text

    return None

def analyze_text(text):
    return {
        "intent": predict_intent(text),
        "location": extract_location(text)
    }
