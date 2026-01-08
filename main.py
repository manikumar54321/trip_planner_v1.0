# ==============================
# AI TRIP PLANNER – FINAL STABLE VERSION
# ==============================

import streamlit as st
import requests, json, random
import google.generativeai as genai
import folium
from streamlit_folium import st_folium
from fpdf import FPDF
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut, GeocoderServiceError

# ------------------------------
# SESSION STATE (NO FADING)
# ------------------------------
for key in ["trip", "coords", "famous_places"]:
    if key not in st.session_state:
        st.session_state[key] = None if key != "famous_places" else []

# ------------------------------
# CONFIG
# ------------------------------
st.set_page_config("Trip Planner AI", "🧭", layout="wide")

genai.configure(api_key="AIzaSyAYVRnGkPAPQiuscWX1r8KM5kOi5Dl39E8")
model = genai.GenerativeModel("gemini-2.5-flash")

HEADERS = {"User-Agent": "TripPlannerAI/1.0"}

# ------------------------------
# CSS
# ------------------------------
st.markdown("""
<style>
.stApp { background: linear-gradient(135deg,#0f2027,#203a43,#2c5364); color:white; }
section[data-testid="stSidebar"] { background: rgba(10,25,30,0.95); }
.card {
    background: rgba(255,255,255,0.08);
    border-radius:20px;
    padding:25px;
    margin:15px 0;
}
.title {
    font-size:44px;
    font-weight:900;
    background: linear-gradient(90deg,#00c6ff,#0072ff);
    -webkit-background-clip:text;
    -webkit-text-fill-color:transparent;
}
.stButton>button {
    background: linear-gradient(90deg,#00c6ff,#0072ff);
    color:white;
    border-radius:14px;
    padding:12px 24px;
}
</style>
""", unsafe_allow_html=True)

# ------------------------------
# IMAGE FUNCTION (FIXED)
# ------------------------------
def get_place_images(place, count=3):
    images = []
    for _ in range(count):
        sig = random.randint(1, 10_000_000)
        images.append(
            f"https://source.unsplash.com/800x600/?{place},travel&sig={sig}"
        )
    return images

# ------------------------------
# GEO + FAMOUS PLACES
# ------------------------------
def get_location_and_famous_places(place_name, limit=6):
    geolocator = Nominatim(user_agent="trip_planner_ai")
    try:
        location = geolocator.geocode(place_name, timeout=10)
        if not location:
            return None, None, []

        lat, lon = location.latitude, location.longitude

        query = f"""
        [out:json];
        (
          node["tourism"="attraction"](around:15000,{lat},{lon});
          way["tourism"="attraction"](around:15000,{lat},{lon});
        );
        out tags center 20;
        """

        r = requests.post(
            "https://overpass-api.de/api/interpreter",
            data=query,
            headers=HEADERS,
            timeout=20
        )

        places = []
        for el in r.json().get("elements", []):
            name = el.get("tags", {}).get("name")
            if name:
                places.append(name)

        return lat, lon, places[:limit]

    except (GeocoderTimedOut, GeocoderServiceError, requests.RequestException):
        return None, None, []

# ------------------------------
# GEMINI (SAFE JSON)
# ------------------------------
def generate_trip_plan(destination, days, budget, style, famous_places):
    prompt = f"""
Return ONLY valid JSON. No explanation.

Format:
{{
  "itinerary": {{
    "Day 1": ["item","item"]
  }},
  "hotels": [],
  "food": [],
  "tips": []
}}

Destination: {destination}
Days: {days}
Budget: {budget}
Style: {style}
Famous Places: {famous_places}
"""

    raw = model.generate_content(prompt).text.strip()
    if raw.startswith("```"):
        raw = raw.replace("```json", "").replace("```", "").strip()

    data = json.loads(raw[raw.find("{"):raw.rfind("}") + 1])
    if "itinerary" not in data:
        raise ValueError("Invalid AI response")
    return data

# ------------------------------
# PDF
# ------------------------------
def export_pdf(trip):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200,10,"AI Trip Planner",ln=True)
    for day, items in trip["itinerary"].items():
        pdf.cell(200,10,day,ln=True)
        for i in items:
            pdf.cell(200,8,f"- {i}",ln=True)
    pdf.output("trip_plan.pdf")

# ------------------------------
# SIDEBAR
# ------------------------------
st.sidebar.markdown("## 🧭 Trip Planner AI")
destination = st.sidebar.text_input("📍 Destination", "Sasaram Bihar")
days = st.sidebar.slider("🗓 Days", 1, 14, 2)
budget = st.sidebar.selectbox("💰 Budget", ["Low","Medium","Luxury"])
style = st.sidebar.multiselect(
    "🎯 Travel Style",
    ["Adventure","Relax","Family","Solo","Couple"]
)
generate = st.sidebar.button("🚀 Generate Trip")

# ------------------------------
# MAIN UI
# ------------------------------
st.markdown("<div class='title'>🧠 AI Trip Planner</div>", unsafe_allow_html=True)

# ------------------------------
# GENERATE
# ------------------------------
if generate:
    with st.spinner("📍 Locating destination..."):
        lat, lon, famous = get_location_and_famous_places(destination)
        if lat is None:
            st.error("❌ Location not found")
            st.stop()
        st.session_state.coords = (lat, lon)
        st.session_state.famous_places = famous

    with st.spinner("🤖 Planning trip with AI..."):
        st.session_state.trip = generate_trip_plan(
            destination, days, budget, style, famous
        )

# ------------------------------
# DISPLAY
# ------------------------------
if st.session_state.trip:
    trip = st.session_state.trip
    lat, lon = st.session_state.coords
    famous_places = st.session_state.famous_places

    # Destination Images
    st.markdown("<div class='card'><h3>📸 Destination Images</h3></div>", unsafe_allow_html=True)
    cols = st.columns(3)
    for col, img in zip(cols, get_place_images(destination)):
        col.image(img, use_container_width=True)

    # Itinerary
    for day, plan in trip["itinerary"].items():
        st.markdown(f"<div class='card'><h3>{day}</h3></div>", unsafe_allow_html=True)
        st.write(plan)

    # Famous Places Images
    st.markdown("<div class='card'><h3>🏛️ Famous Places</h3></div>", unsafe_allow_html=True)
    for place in famous_places:
        st.markdown(f"### 📍 {place}")
        cols = st.columns(3)
        for col, img in zip(cols, get_place_images(place)):
            col.image(img, use_container_width=True)

    # Map
    st.markdown("<div class='card'><h3>🗺️ Map</h3></div>", unsafe_allow_html=True)
    m = folium.Map(location=[lat, lon], zoom_start=12)
    folium.Marker([lat, lon], popup=destination).add_to(m)
    st_folium(m, height=400)

    # PDF
    if st.button("📄 Download Trip PDF"):
        export_pdf(trip)
        st.success("PDF Generated ✔")
