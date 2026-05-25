import streamlit as st
import json
import os
from openai import OpenAI
from agents.extractor import extract_profile
from agents.matcher import match_scholarships
from agents.drafter import draft_essay
from agents.timeline import generate_timeline

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Scholarship Copilot",
    page_icon="🎓",
    layout="wide"
)

# ── Suggestion 3 — Missing API key handling ────────────────────────────────────
api_key = os.environ.get("OPENAI_API_KEY", "")
if not api_key:
    try:
        api_key = st.secrets.get("OPENAI_API_KEY", "")
    except Exception:
        pass

if not api_key:
    st.error("⚠️ Missing OPENAI_API_KEY. Please add it to your Codespace secrets and restart.")
    st.stop()

# ── Session state init (all in-memory, cleared on tab close) ───────────────────
if "profile" not in st.session_state:
    st.session_state.profile = None
if "matches" not in st.session_state:
    st.session_state.matches = []
if "draft" not in st.session_state:
    st.session_state.draft = ""
if "selected_scholarship" not in st.session_state:
    st.session_state.selected_scholarship = None
if "step" not in st.session_state:
    st.session_state.step = 1

# ── OpenAI client ──────────────────────────────────────────────────────────────
@st.cache_resource
def get_client():
    return OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

# ── Load scholarship data ──────────────────────────────────────────────────────
@st.cache_data
def load_scholarships():
    with open("data/scholarships.json", "r") as f:
        return json.load(f)

client = get_client()
scholarships = load_scholarships()

# ── Suggestion 4 — Step progress indicator ────────────────────────────────────
STEPS = {
    1: "📝 Profile Input",
    2: "👤 Profile Review",
    3: "🎯 Scholarship Matches",
    4: "✍️ Essay Draft"
}

st.title("🎓 Scholarship Copilot")
st.caption("Your AI-powered grant and application assistant — session only, nothing is saved.")

# Progress bar
progress_value = (st.session_state.step - 1) / (len(STEPS) - 1)
st.progress(progress_value)

cols = st.columns(len(STEPS))
for i, (num, label) in enumerate(STEPS.items()):
    with cols[i]:
        if num < st.session_state.step:
            st.markdown(f"<p style='text-align:center; color:#6C63FF;'>✅ {label}</p>", unsafe_allow_html=True)
        elif num == st.session_state.step:
            st.markdown(f"<p style='text-align:center; font-weight:bold;'>▶️ {label}</p>", unsafe_allow_html=True)
        else:
            st.markdown(f"<p style='text-align:center; color:gray;'>⬜ {label}</p>", unsafe_allow_html=True)

st.divider()

# ── STEP 1: Profile Input ──────────────────────────────────────────────────────
with st.expander("Step 1 — Tell us about yourself", expanded=(st.session_state.step == 1)):
    st.markdown("Paste your resume, a short bio, or just describe yourself below.")
    user_input = st.text_area(
        "Your profile",
        height=200,
        placeholder="Example: I'm a 3rd-year BS Information Technology student at Asia Pacific College with a GPA of 91. I know React, Node.js, and Python. I served as president of our IT student organization and I'm interested in pursuing graduate school focused on AI..."
    )

    if st.button("🔍 Extract my profile", type="primary"):
        if user_input.strip():
            with st.spinner("Step 1 of 3 — Analyzing your profile..."):
                st.session_state.profile = extract_profile(user_input, client)

            if "error" in st.session_state.profile:
                st.error(f"❌ {st.session_state.profile['error']}")
                st.session_state.profile = None
            else:
                st.session_state.step = 2
                st.rerun()
        else:
            st.warning("Please enter some information about yourself first.")

# ── STEP 2: Profile Review + Matching ─────────────────────────────────────────
if st.session_state.profile and "error" not in st.session_state.profile:
    with st.expander("Step 2 — Your extracted profile", expanded=(st.session_state.step == 2)):
        p = st.session_state.profile

        # Suggestion 3 — Empty extraction warnings
        if not p.get("major"):
            st.warning("⚠️ Could not confidently determine your major. Matching may be less accurate.")
        if not p.get("gpa"):
            st.warning("⚠️ GPA not detected. Some scholarships with GPA requirements may still appear.")

        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**Name:** {p.get('name') or 'Not detected'}")
            st.markdown(f"**Major:** {p.get('major') or 'Not detected'}")
            st.markdown(f"**Year level:** {p.get('year_level') or 'Not detected'}")
            st.markdown(f"**GPA:** {p.get('gpa') or 'Not detected'}")
        with col2:
            st.markdown(f"**Level seeking:** {p.get('level_seeking', 'undergraduate').capitalize()}")
            st.markdown(f"**Skills:** {', '.join(p.get('skills', [])) or 'None detected'}")
            st.markdown(f"**Leadership:** {', '.join(p.get('leadership', [])) or 'None detected'}")

        st.info(f"**Goals:** {p.get('goals') or 'Not detected'}")

        if st.button("🎯 Find matching scholarships", type="primary"):
            with st.spinner("Step 2 of 3 — Matching scholarships..."):
                st.session_state.matches = match_scholarships(
                    st.session_state.profile, scholarships
                )
                st.session_state.step = 3
                st.rerun()

# ── STEP 3: Scholarship Matches ────────────────────────────────────────────────
if st.session_state.matches:
    with st.expander("Step 3 — Your scholarship matches", expanded=(st.session_state.step == 3)):
        st.markdown(f"Found **{len(st.session_state.matches)}** matching scholarships:")

        for i, s in enumerate(st.session_state.matches):
            score = s["match_score"]
            score_color = "🟢" if score >= 5 else "🟡" if score >= 3 else "🔴"

            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"### {s['name']}")
                    st.caption(f"{s['provider']} · {s['type'].capitalize()} · {', '.join(s['level']).capitalize()}")
                    st.markdown(f"**Benefits:** {s['benefits']}")
                    st.markdown(f"**Deadline:** {s['deadline']}")
                    st.markdown(f"**Match reasons:** {' · '.join(s['match_reasons'])}")
                    if s.get("link") and s["link"].startswith("http"):
                        st.markdown(f"[🔗 View scholarship]({s['link']})")
                with col2:
                    st.metric("Match score", f"{score_color} {score}/7")
                    if st.button("Draft my essay", key=f"draft_{i}"):
                        st.session_state.selected_scholarship = s
                        st.session_state.step = 4
                        with st.spinner("Step 3 of 3 — Drafting your personalized essay..."):
                            st.session_state.draft = draft_essay(
                                st.session_state.profile, s, client
                            )
                        st.rerun()

# ── STEP 4: Essay Draft + Calendar ────────────────────────────────────────────
if st.session_state.draft and st.session_state.selected_scholarship:
    s = st.session_state.selected_scholarship
    with st.expander("Step 4 — Your personalized essay draft", expanded=(st.session_state.step == 4)):
        st.markdown(f"#### Draft for: {s['name']}")
        st.markdown(f"*Prompt: {s['essay_prompt']}*")
        st.divider()

        # Show error inline if drafting failed
        if st.session_state.draft.startswith("Essay generation failed"):
            st.error(f"❌ {st.session_state.draft}")
        else:
            edited_draft = st.text_area(
                "Edit your draft below:",
                value=st.session_state.draft,
                height=300
            )

            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="📄 Download essay draft (.txt)",
                    data=edited_draft,
                    file_name=f"essay_{s['id']}.txt",
                    mime="text/plain"
                )
            with col2:
                ics_bytes = generate_timeline(s)
                st.download_button(
                    label="📅 Download application timeline (.ics)",
                    data=ics_bytes,
                    file_name=f"timeline_{s['id']}.ics",
                    mime="text/calendar"
                )

            st.info("💡 This draft is a starting point. Edit it to reflect your authentic voice before submitting.")

    st.divider()
    st.caption("🔒 Privacy notice: No personal information entered in this session is stored or transmitted beyond OpenAI's API. All data clears when you close this tab.")