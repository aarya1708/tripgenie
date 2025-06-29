# 🌍 TripGenie – AI-Powered Travel Assistant on WhatsApp

TripGenie is an AI-powered travel assistant built for WhatsApp that makes discovering places and planning trips seamless through natural, conversational interaction. Users can share their current location via WhatsApp or simply type a place name — the bot intelligently extracts and resolves the location using a custom Named Entity Recognition (NER) pipeline powered by spaCy and GeoNames. Once the location is detected, TripGenie takes in natural language queries like “suggest cafes” or “what are some historical places nearby,” and classifies the intent using a fine-tuned BERT model trained on a self curated travel dataset. The resulting intent is used to query the Google Places API for live results. The bot supports memory-aware conversations with built-in session handling, allowing it to remember the user's last location, recent queries, and seamlessly process follow-ups like “more” or to update location without requiring the user to repeat themselves.

In addition to nearby exploration, TripGenie can generate personalized 4-day itineraries using OpenRouter's API and prompt engineering techniques. After a user provides a location, the bot responds with a complete day-wise plan, then automatically switches back to the nearby search mode for continued assistance. TripGenie is powered by a robust Python (Flask) backend that manages the NLP pipeline, session memory, and external API calls, along with a Node.js-based frontend that connects to WhatsApp. With over 95% intent classification accuracy, intelligent context handling, and real-time responses, TripGenie delivers a smooth, AI-driven travel experience entirely through chat.

---

## ✨ Features

- **AI-powered Conversational Travel Assistant**
- **Two core functionalities:**
  1. 🔍 **Nearby Place Discovery**
  2. 🗓️ **4-Day Itinerary Generator**

---

## 💬 Option 1: Nearby Places

- Accepts **user location** via:
  - WhatsApp’s current location feature
  - Typed location (detected using **NER with spaCy + GeoNames**)
- Accepts **natural language queries** like:
  - “Show me some cafes”
  - “Where are the best historical places?”
- Performs **intent classification** using a custom fine-tuned **BERT model** on a self-curated travel dataset
- Sends classified intent + location to **Google Places API** to fetch accurate results
- Supports **memory-aware conversation**:
  - Remembers previous location and query context
  - Understands follow-up prompts like “more” or “change location”
  - Enables smooth back-and-forth interaction

---

## 🗺️ Option 2: Itinerary Generation

- Accepts a location (both WhatsApp current location and typed)
- Uses **OpenRouter API** with custom prompt engineering
- Generates a **personalized 4-day travel itinerary**
- After itinerary, continues interaction via the Nearby Places module

---

## 🧠 Key Technologies Used

- **Frontend**: WhatsApp + Node.js
- **Backend**: Python (Flask)
- **NLP/NLU Pipeline**:
  - Named Entity Recognition (NER): spaCy + GeoNames
  - Intent Classification: Fine-tuned BERT (95%+ accuracy)
  - Prompt-based Generation: OpenRouter API
- **Data**:
  - Custom travel intent dataset
  - Google Places API integration for live results
- **Memory & Context Handling**:
  - Session-aware conversations
  - Dynamic context tracking for user location and query type

---

## 📸 Screenshots

Photu here

---

## 🚀 How It Works

1. 🧭 User sends a location or typed query
2. 🧠 NLP engine extracts location & classifies query intent
3. 🌐 API call is made to Google Places or OpenRouter
4. 💬 Bot responds with relevant places or a full itinerary
5. 🔄 Bot remembers context for follow-up interactions

---

## 📈 Accuracy & Performance

- ✅ 95%+ intent classification accuracy
- ⚡ Fast real-time response using optimized APIs
- 🧠 Remembers previous context for fluid UX

---

## 📚 Future Improvements

- Add multilingual support (e.g., Hindi, Spanish)
- Feedback-based model retraining (continual learning)
