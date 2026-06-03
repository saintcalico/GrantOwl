import streamlit as st
import json
import os
from openai import OpenAI

# Import our new modular views
from views.step1_profile import render_step1
from views.step2_matches import render_step2
from views.step3_dashboard import render_step3
from views.step4_action import render_step4

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Iskolar.AI",
    page_icon="Iskolar",
    layout="wide"
)

# ── API key guard ──────────────────────────────────────────────────────────────
api_key = os.environ.get("OPENAI_API_KEY", "")
if not api_key:
    try:
        api_key = st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        pass

if not api_key:
    st.error(
        "Error: Missing OPENAI_API_KEY. "
        "Please add it to your Codespace secrets and restart."
    )
    st.stop()

# ── Session state ──────────────────────────────────────────────────────────────
defaults = {
    "profile": None,
    "matches": [],
    "match_source": None,
    "selected_scholarship": None,
    "rationale": None,
    "tips": None,
    "step": 1,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Clients ────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_client():
    return OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

@st.cache_data
def load_scholarships():
    with open("data/scholarships.json", "r") as f:
        return json.load(f)

client = get_client()
scholarships = load_scholarships()

# ── Header & Progress Indicator ────────────────────────────────────────────────
STEPS = {
    1: "Your Profile",
    2: "Matches",
    3: "Best Match",
    4: "Action Plan",
}

st.title("Iskolar.AI")
st.caption(
    "Your AI-powered scholarship adviser "
    "— session only, nothing is saved."
)

progress_value = (st.session_state.step - 1) / (len(STEPS) - 1)
st.progress(progress_value)

step_cols = st.columns(len(STEPS))
for i, (num, label) in enumerate(STEPS.items()):
    with step_cols[i]:
        if num < st.session_state.step:
            st.markdown(
                f"<p style='text-align:center;color:#6C63FF;'>{label} (Done)</p>",
                unsafe_allow_html=True,
            )
        elif num == st.session_state.step:
            st.markdown(
                f"<p style='text-align:center;font-weight:bold;'>-> {label} (Active)</p>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<p style='text-align:center;color:gray;'>{label}</p>",
                unsafe_allow_html=True,
            )

st.divider()

# ── Routing Layer ──────────────────────────────────────────────────────────────
render_step1(client, scholarships)
render_step2(client)
render_step3()
render_step4()