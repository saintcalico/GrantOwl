import streamlit as st
import json
import os
from openai import OpenAI

# Import modular step views
from views.step1_profile import render_step1
from views.step2_matches import render_step2
from views.step3_dashboard import render_step3
from views.step4_action import render_step4

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="GrantOwl",
    page_icon="GrantOwl.png",  # Custom image logo file configured as the tab icon
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
        "Please add it to your environment secrets and restart."
    )
    st.stop()

# ── Session state ──────────────────────────────────────────────────────────────
# Tracks the structural state across the multi-step pipeline
defaults = {
    "profile": None,
    "matches": [],
    "match_source": None,
    "selected_scholarship": None,
    "rationale": None,
    "tips": None,
    "step": 1,
    "preference_log": []  # Episodic memory array tracking user selections
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

# ── Resource Ingestion & Clients ──────────────────────────────────────────────
@st.cache_resource
def get_client():
    return OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

@st.cache_data
def load_scholarships():
    with open("data/scholarships.json", "r") as f:
        return json.load(f)

client = get_client()
scholarships = load_scholarships()

# ── Header & Rebranded Layout ──────────────────────────────────────────────────
STEPS = {
    1: "Your Profile",
    2: "Matches",
    3: "Best Match",
    4: "Action Plan",
}

# Changed layout ratio from [1, 6] to [1, 4] to give the enlarged logo column more presence
col_logo, col_title = st.columns([1, 4])
with col_logo:
    try:
        # Increased display width to 140 for robust visibility
        st.image("GrantOwl.png", width=140)
    except Exception:
        # Fallback icon container placeholder in case of localized image asset path issues
        st.title("🎓")

with col_title:
    st.write("")  # Vertical alignment padding
    st.markdown("<h1 style='margin-bottom: 0px;'>GrantOwl</h1>", unsafe_allow_html=True)
    st.caption(
        "Your AI-powered scholarship adviser "
        "— session only, completely ephemeral."
    )

# Dynamic timeline tracker metrics
progress_value = (st.session_state.step - 1) / (len(STEPS) - 1)
st.progress(progress_value)

# Update navigation links text colors to integrate beautifully with the new logo palette
step_cols = st.columns(len(STEPS))
for i, (num, label) in enumerate(STEPS.items()):
    with step_cols[i]:
        if num < st.session_state.step:
            st.markdown(
                f"<p style='text-align:center;color:#2C7A7B;font-weight:600;'>"
                f"{label} (Done)</p>",
                unsafe_allow_html=True,
            )
        elif num == st.session_state.step:
            st.markdown(
                f"<p style='text-align:center;font-weight:bold;color:#1A202C;"
                f"border-bottom: 3px solid #2C7A7B; padding-bottom: 5px;'>"
                f"→ {label} (Active)</p>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<p style='text-align:center;color:#718096;'>"
                f"{label}</p>",
                unsafe_allow_html=True,
            )

st.divider()

# ── App Step Routing Layer ─────────────────────────────────────────────────────
render_step1(client, scholarships)
render_step2(client)
render_step3()
render_step4()