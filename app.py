import streamlit as st
import requests
from PIL import Image
import json
import re
import base64
import io

st.set_page_config(page_title="EcoSort AI - Waste Segregation Assistant", page_icon="♻️", layout="centered")

# ---------- STYLING ----------
st.markdown("""
<style>
.main-title {font-size: 2.2rem; font-weight: 800; color: #1b5e20; margin-bottom:0;}
.subtitle {color: #4caf50; font-size: 1.05rem; margin-top:0;}
.result-card {padding: 1.2rem; border-radius: 12px; margin-top: 1rem;}
.recyclable {background-color: #e3f2fd; border-left: 6px solid #1976d2;}
.compostable {background-color: #e8f5e9; border-left: 6px solid #388e3c;}
.hazardous {background-color: #ffebee; border-left: 6px solid #d32f2f;}
.landfill {background-color: #f5f5f5; border-left: 6px solid #757575;}
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">♻️ EcoSort AI</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Snap a photo of any waste item — get instant, AI-powered disposal guidance.</p>', unsafe_allow_html=True)
st.divider()

# ---------- SESSION STATE (Eco Points & Impact Tracker) ----------
if "eco_points" not in st.session_state:
    st.session_state.eco_points = 0
if "items_scanned" not in st.session_state:
    st.session_state.items_scanned = 0
if "co2_saved" not in st.session_state:
    st.session_state.co2_saved = 0.0
if "history" not in st.session_state:
    st.session_state.history = []

# ---------- API KEY & SETTINGS ----------
with st.sidebar:
    st.header("⚙️ Setup")
    api_key = st.text_input("Gemini API Key", type="password", help="Get a free key at aistudio.google.com/apikey")
    language = st.selectbox("🌐 Disposal instructions language", ["English", "Hindi", "Telugu"])
    st.markdown("---")
    st.markdown("### 🏆 Your Eco Impact")
    col_a, col_b = st.columns(2)
    col_a.metric("Eco Points", st.session_state.eco_points)
    col_b.metric("Items Scanned", st.session_state.items_scanned)
    st.metric("Est. CO₂ Impact Avoided", f"{st.session_state.co2_saved:.1f} kg")
    if st.session_state.history:
        with st.expander("📜 Scan History"):
            for h in reversed(st.session_state.history):
                st.write(f"• {h}")
    st.markdown("---")
    st.markdown("### About")
    st.write("EcoSort AI uses Google Gemini's vision model to identify waste items and provide accurate, India-context disposal instructions in multiple languages — helping reduce landfill overload and improve recycling rates at the household level.")
    st.markdown("**Theme:** Clean & Green Technology")
    st.markdown("**Built for:** Idea2Impact Hackathon 2026")

CATEGORY_STYLE = {
    "Recyclable": ("recyclable", "🔵"),
    "Compostable": ("compostable", "🟢"),
    "Hazardous": ("hazardous", "🔴"),
    "Landfill": ("landfill", "⚪"),
}

def analyze_waste(image, key, language="English"):
    key = key.strip()  # remove accidental whitespace/newlines from pasted key

    # Convert image to base64 JPEG
    buffered = io.BytesIO()
    rgb_image = image.convert("RGB")
    rgb_image.save(buffered, format="JPEG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")

    prompt = f"""You are a waste management expert for Indian households. Look at this image of a waste item and respond ONLY with valid JSON (no markdown, no extra text) in exactly this format:

{{
  "item_name": "short name of the item",
  "category": "Recyclable" or "Compostable" or "Hazardous" or "Landfill",
  "confidence": "High/Medium/Low",
  "explanation": "1-2 sentence explanation of why it belongs in this category, written in {language}",
  "disposal_steps": ["step 1 in {language}", "step 2 in {language}", "step 3 in {language}"],
  "environmental_tip": "one practical tip related to this item, written in {language}",
  "co2_impact_kg": 0.5,
  "eco_points": 10
}}

For co2_impact_kg: estimate the approximate kg of CO2-equivalent emissions avoided by disposing of this item correctly instead of sending it to a landfill (realistic small estimate, e.g. 0.05 to 2.0 depending on item type).
For eco_points: award 5 for Landfill items (still tried), 10 for Recyclable/Compostable, 15 for Hazardous (extra care needed). Return only the number.
All text fields (explanation, disposal_steps, environmental_tip) must be written in {language}, but item_name and category should stay in English."""

   url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent"
   headers = {"x-goog-api-key": key, "Content-Type": "application/json"}
   payload = {
       "contents": [{
           "parts": [
               {"text": prompt},
               {"inline_data": {"mime_type": "image/jpeg", "data": img_base64}}
           ]
       }]
   }
   response = requests.post(url, headers=headers, json=payload, timeout=30)
   response.raise_for_status()
    data = response.json()
    text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    # Strip markdown code fences if present
    text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    return json.loads(text)

# ---------- MAIN UI ----------
tab1, tab2 = st.tabs(["📷 Upload Photo", "📖 How it works"])

with tab1:
    uploaded_file = st.file_uploader("Upload a photo of the waste item", type=["jpg", "jpeg", "png"])
    camera_photo = st.camera_input("...or take a photo directly")

    image_input = uploaded_file if uploaded_file else camera_photo

    if image_input:
        image = Image.open(image_input)
        st.image(image, caption="Your item", width=300)

        if not api_key:
            st.warning("⚠️ Please enter your Gemini API key in the sidebar to analyze this item.")
        else:
            if st.button("🔍 Analyze & Get Disposal Guidance", type="primary"):
                with st.spinner("AI is analyzing the item..."):
                    try:
                        result = analyze_waste(image, api_key, language)
                        css_class, emoji = CATEGORY_STYLE.get(result["category"], ("landfill", "⚪"))

                        st.markdown(f"""
                        <div class="result-card {css_class}">
                        <h3>{emoji} {result['item_name']} — {result['category']}</h3>
                        <p><b>Confidence:</b> {result['confidence']}</p>
                        <p>{result['explanation']}</p>
                        </div>
                        """, unsafe_allow_html=True)

                        st.subheader("✅ How to dispose of it")
                        for i, step in enumerate(result["disposal_steps"], 1):
                            st.write(f"{i}. {step}")

                        st.info(f"🌱 **Eco Tip:** {result['environmental_tip']}")

                        co2 = float(result.get("co2_impact_kg", 0.3))
                        points = int(result.get("eco_points", 10))
                        col1, col2 = st.columns(2)
                        col1.success(f"🌍 CO₂ impact avoided: **{co2} kg**")
                        col2.success(f"🏆 Eco Points earned: **+{points}**")

                        # Update session gamification stats
                        st.session_state.eco_points += points
                        st.session_state.items_scanned += 1
                        st.session_state.co2_saved += co2
                        st.session_state.history.append(f"{result['item_name']} → {result['category']} (+{points} pts)")

                        st.balloons()

                    except json.JSONDecodeError:
                        st.error("Couldn't parse the AI's response. Please try again with a clearer photo.")
                    except Exception as e:
                        st.error(f"Something went wrong: {e}")

with tab2:
    st.markdown("""
    ### The Problem
    Most households in India don't segregate waste correctly — recyclables end up in landfills,
    hazardous items (batteries, e-waste) get mixed with regular trash, and compostable waste is wasted
    as a resource. This worsens landfill overflow and pollution.

    ### The AI Solution
    EcoSort AI uses **Google Gemini's multimodal vision model** to:
    1. Identify the waste item from a photo
    2. Classify it into Recyclable / Compostable / Hazardous / Landfill
    3. Give clear, step-by-step disposal instructions
    4. Share a practical sustainability tip

    ### Why AI is central (not decorative)
    The core function — identifying an unknown physical object, reasoning about its correct
    disposal pathway, translating guidance into the user's language, and estimating CO₂ impact —
    is entirely performed by the vision-language model. Without AI, this app cannot function;
    there's no hardcoded rule engine behind it.

    ### Extra Features
    - 🌐 **Multilingual guidance** — English, Hindi, or Telugu, so instructions reach every household
    - 🏆 **Eco-Points gamification** — every scan earns points, encouraging repeated correct disposal habits
    - 🌍 **CO₂ impact estimate** — shows the real environmental value of each correct disposal decision
    - 📜 **Session impact tracker** — total items scanned and cumulative CO₂ avoided, visible in the sidebar
    """)

st.divider()
st.caption("Built for Idea2Impact Online Hackathon 2026 · Theme: Clean & Green Technology")
