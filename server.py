from flask import Flask, request, jsonify 
from datetime import datetime
from utils.nlp_utils import analyze_text
import requests
import time
import os
from dotenv import load_dotenv
load_dotenv()


app = Flask(__name__)

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
OPEN_ROUTER_API_KEY = os.getenv("OPEN_ROUTER_API_KEY")

SESSION_TIMEOUT = 3600  # 1 hour in seconds

user_context = {}         # session state and latest query
active_sessions = {}      # track active user sessions and timestamp
allowed_users = set()     # users who triggered start
pending_location_confirm = {}  # when NLP detects location

@app.route("/message", methods=["POST"])
def handle_message():
    data = request.json
    sender = data.get("sender")
    message = data.get("message", "").strip().lower()

    print(f"📥 Message from {sender}: {message}")

    if message == "end_session":
        user_context.pop(sender, None)
        active_sessions.pop(sender, None)
        if sender in pending_location_confirm:
            pending_location_confirm.pop(sender)
        # feedback collection here
        return jsonify({"reply": "👋 Your TripGenie session has ended. Type 'start' to begin a new one."})

    if message == "start":
        if sender in active_sessions:
            return jsonify({"reply": "⚠️ You're already in an active session. Please continue, or type 'end_session' to start fresh."})
        
        allowed_users.add(sender)
        active_sessions[sender] = time.time()
        user_context[sender] = {"stage": "awaiting_mode_selection"}
        return jsonify({"reply": "👋 Welcome to TripGenie! What would you like to do today?\n1️⃣ Get nearby place suggestions\n2️⃣ Get a 5-day itinerary for a location\n\nPlease reply with 1 or 2."})

    if sender in active_sessions and time.time() - active_sessions[sender] > SESSION_TIMEOUT:
        user_context.pop(sender, None)
        active_sessions.pop(sender, None)
        return jsonify({"reply": "⌛ Your session expired. Please type 'start' again to begin a new session."})

    if sender not in active_sessions:
        return jsonify({"reply": "❗ Please type 'start' to begin your TripGenie session."})

    context = user_context.get(sender, {})

    # Prevent location sharing or free-text messages before choosing 1/2
    if context.get("stage") == "awaiting_mode_selection":
        if data.get("latitude") or data.get("longitude"):
            return jsonify({"reply": "❗ Please select an option first by replying with 1 or 2."})
        elif message not in ["1", "2"]:
            return jsonify({"reply": "❗ Please select one of the options:\n1️⃣ Get nearby place suggestions\n2️⃣ Get a 5-day itinerary"})


    # Handle mode selection
    if context.get("stage") == "awaiting_mode_selection":
        if message == "1":
            user_context[sender] = {
                "stage": "awaiting_location", 
                "mode": "places"
            }
            return jsonify({"reply": "📍 Great! Please share your location to begin."})
        
        elif message == "2":
            user_context[sender] = {
                "stage": "awaiting_itinerary_location", 
                "mode": "itinerary"
            }
            return jsonify({"reply": "🌍 Please type the location you want an itinerary for (e.g. Manali) or share your current location."})
        
        else:
            return jsonify({"reply": "❗ Please reply with 1 or 2 to continue."})

    if sender in pending_location_confirm:
        if message in ["yes", "y"]:
            context = pending_location_confirm.pop(sender)
            latlng = get_latlng_from_place(context["location"])
            if latlng:
                user_context[sender] = {
                    "stage": "awaiting_query",
                    "location": latlng,
                    "mode": "places"
                }
                return jsonify({"reply": "✅ Location confirmed! Now, what would you like to explore? (e.g. restaurants, sightseeing, cafes)"})
                # return get_places_by_intent(sender, context["intent"], latlng, f"{context['query']} in {context['location']}")
            else:
                return jsonify({"reply": "❌ Couldn't confirm location. Please share your current location."})
        
        elif message in ["no", "n"]:
            context = pending_location_confirm.pop(sender)
            return jsonify({"reply": "procedd with the query your last loc will be taken into account. OR share your location again to update to new location"})
            
        else:
            # pending_location_confirm.pop(sender)
            return jsonify({"reply": "write yes or no only"})

    # Handle itinerary location input in words
    if context.get("stage") == "awaiting_itinerary_location":
        if any(char.isdigit() for char in message):  # if coordinates or gibberish
            return jsonify({"reply": "📍 Please send a valid location name (e.g. Manali) or use WhatsApp location sharing."})
        
        else:
            itinerary_location=message
            itinerary = generate_itenary(itinerary_location)

            # Now convert to Part A flow
            user_context[sender] = {"stage": "awaiting_location", "mode": "places"}
            return jsonify({"reply": f"🗺️ Here's your 3-day itinerary for *{message}*:\n\n{itinerary}\n\n---\nNow let's explore places nearby. Please share your current location to begin."})

    # Handle itinerary location input in coordinates
    if context.get("stage") == "awaiting_itinerary_location" and data.get("latitude"):
        lat = data.get("latitude")
        lng = data.get("longitude")
        place_name = reverse_geocode(lat, lng)
        itinerary = generate_itenary(place_name)
        user_context[sender] = {"stage": "awaiting_location", "mode": "places"}
        return jsonify({"reply": f"🗺️ Here's your 3-day itinerary for *{place_name}*:\n\n{itinerary}\n\n---\nNow let's explore places nearby. Please share your current location to begin."})

    # Handle 'more' only for Part A
    if message == "more" and context.get("mode") == "places" and isinstance(context, dict):
        if context.get("last_places"):
            last_query = context.get("query", "restaurant")
            return get_places_by_intent(sender, context.get("intent", "restaurant"), context["location"], last_query)

    # Only allow Part A queries in 'places' mode
    if context.get("mode") == "places":
        if "itinerary" in message:
            return jsonify({"reply": f"For itinerary, please end the session by typing 'end_session' and select option 2 in the new session."})

        result = analyze_text(message)
        intent = result.get("intent")
        location = result.get("location")

        if location:
            pending_location_confirm[sender] = {"intent": intent, "location": location, "query": message}
            return jsonify({"reply": f"📍 I found *{location}* in your message. Use this location? (Yes / No)"})

        if context.get("stage") == "awaiting_query" and context.get("location"):
            if intent in ["restaurant", "sightseeing", "historical_place", "cafe", "museum"]:
                return get_places_by_intent(sender, intent, context["location"], message)
            else:
                return jsonify({"reply": "❓ Sorry, I couldn't understand your request. Please try a different query."})

        if context.get("stage") == "awaiting_location":
            return jsonify({"reply": "📍No prev loc found,  Please share your location to continue."})

    return jsonify({"reply": "❓ I'm not sure what you meant. Please try again or type 'start' to begin."})

@app.route("/location", methods=["POST"]) 
def handle_location():
    data = request.json
    sender = data.get("sender")
    lat = data.get("latitude")
    lng = data.get("longitude")

    print(f"📍 Location from {sender}: {lat}, {lng}")

    if sender not in active_sessions:
        return jsonify({"reply": "❗ Please type 'start' to begin your session."})

    if sender in pending_location_confirm:
        return jsonify({"reply": "Write yes or no only"})

    context = user_context.get(sender, {})

    if context.get("stage") == "awaiting_mode_selection":
        return jsonify({"reply": "❗ Please reply with 1️⃣ or 2️⃣ before sharing your location."})

    if context.get("stage") == "awaiting_itinerary_location":
        place_name = reverse_geocode(lat, lng)
        itinerary = generate_itenary(place_name)
        user_context[sender] = {"stage": "awaiting_location", "mode": "places"}
        return jsonify({"reply": f"🗺️ Here's your 5-day itinerary for *{place_name}*:\n\n{itinerary}\n\n---\nNow let's explore places nearby. Please share your current location to begin."})

    user_context[sender] = {
        "stage": "awaiting_query",
        "location": f"{lat},{lng}",
        "mode": "places"
    }

    return jsonify({"reply": "✅ Location received! Now, what would you like to explore? (e.g. restaurants, sightseeing, cafes)"})

def get_latlng_from_place(place_name):
    try:
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
        params = {
            "query": place_name,
            "key": GOOGLE_API_KEY
        }
        resp = requests.get(url, params=params)
        data = resp.json()
        if data.get("results"):
            location = data["results"][0]["geometry"]["location"]
            return f"{location['lat']},{location['lng']}"
    except Exception as e:
        print("Error getting latlng from place:", e)
    return None

def reverse_geocode(lat, lng):
    try:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "latlng": f"{lat},{lng}",
            "key": GOOGLE_API_KEY
        }
        resp = requests.get(url, params=params)
        data = resp.json()
        if data.get("results"):
            return data["results"][0]["formatted_address"]
    except Exception as e:
        print("Error during reverse geocoding:", e)
    return "your location"

def get_places_by_intent(sender, intent, location_str, user_query=None):
    lat, lng = location_str.split(",") if "," in location_str else (None, None)
    if not lat or not lng:
        return jsonify({"reply": "Invalid location format."})

    try:
        use_text_search = intent == "restaurant" and user_query

        if use_text_search:
            url = "https://maps.googleapis.com/maps/api/place/textsearch/json"
            params = {
                "query": user_query,
                "location": f"{lat},{lng}",
                "radius": 2000,
                "key": GOOGLE_API_KEY
            }
        else:
            place_type = {
                "restaurant": "restaurant",
                "sightseeing": "tourist_attraction",
                "historical_place": "museum",
                "cafe": "cafe",
                "museum": "museum"
            }.get(intent, "restaurant")

            url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
            params = {
                "location": f"{lat},{lng}",
                "radius": 5000,
                "type": place_type,
                "key": GOOGLE_API_KEY
            }

        response = requests.get(url, params=params)
        data = response.json()
        places = data.get("results", [])

        shown_names = user_context.get(sender, {}).get("shown_names", [])
        new_places = [p for p in places if p.get("name") not in shown_names]
        places = new_places[:5] if new_places else places[:5]

        display_name = {
            "restaurant": "restaurants",
            "tourist_attraction": "sightseeing places",
            "museum": "historical places",
            "cafe": "cafes"
        }.get(intent if not use_text_search else "restaurant", intent)

        if not places:
            return jsonify({"reply": f"No nearby {display_name} found."})

        shown_names = [place.get("name") for place in places]
        user_context[sender].update({
            "query": user_query if use_text_search else intent,
            "lat": lat,
            "lng": lng,
            "shown_names": user_context.get(sender, {}).get("shown_names", []) + shown_names,
            "last_places": True,
            "intent": intent
        })

        reply_lines = [f"🔎 *Nearby {display_name}*\n"]

        for i, place in enumerate(places, 1):
            name = place.get("name", "Unknown")
            address = place.get("vicinity") or place.get("formatted_address", "Address not available")
            map_link = f"https://maps.google.com/?q={place['geometry']['location']['lat']},{place['geometry']['location']['lng']}"
            rating = place.get("rating", "N/A")
            open_now = place.get("opening_hours", {}).get("open_now", None)
            status = "Open Now" if open_now else "Closed" if open_now is not None else ""

            reply_lines.append(
                f"{i}. *{name}*\n"
                f"⭐ {rating} | {status}\n"
                f"📍 {address}\n"
                f"🔗 _[📍 View on Map]({map_link})_\n"
            )

        return wrap_reply_with_loop(sender, "\n".join(reply_lines))

    except Exception as e:
        print("❌ Error:", e)
        return jsonify({"reply": "Something went wrong fetching places."})

def wrap_reply_with_loop(sender, main_reply):
    return jsonify({"reply": f"{main_reply}\n\n💬 Ask another query?\n➡️ Type 'more' for more options.\n🚫 Type 'end_session' to finish your session."})

def generate_itenary(location):
    prompt = f"Create a very short and realistic 5-day travel itinerary for a tourist visiting {location}. Include top sightseeing places and food recommendations each day."

    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPEN_ROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "mistralai/mistral-7b-instruct",
                "max_tokens": 5000,
                "messages": [
                    {"role": "system", "content": "You are a travel planner assistant."},
                    {"role": "user", "content": prompt}
                ]
            },
            timeout=20
        )
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        print("Itinerary generation error:", e)
        return "Sorry, we couldn't generate an itinerary at this moment. Please try again later."

if __name__ == "__main__":
    app.run(port=5000, debug=True)
