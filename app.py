import streamlit as st
import json
import os
from openai import OpenAI
from agents.extractor import extract_profile
from agents.matcher import match_scholarships
from agents.timeline import generate_timeline, generate_application_steps

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Scholarship Copilot",
    page_icon="🎓",
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
        "⚠️ Missing OPENAI_API_KEY. "
        "Please add it to your Codespace secrets and restart."
    )
    st.stop()

# ── Session state (all in-memory, cleared on tab close) ───────────────────────
if "profile" not in st.session_state:
    st.session_state.profile = None
if "matches" not in st.session_state:
    st.session_state.matches = []
if "match_source" not in st.session_state:
    st.session_state.match_source = None
if "selected_scholarship" not in st.session_state:
    st.session_state.selected_scholarship = None
if "step" not in st.session_state:
    st.session_state.step = 1

# ── OpenAI client ──────────────────────────────────────────────────────────────
@st.cache_resource
def get_client():
    return OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

# ── Load scholarship fallback data ─────────────────────────────────────────────
@st.cache_data
def load_scholarships():
    with open("data/scholarships.json", "r") as f:
        return json.load(f)

scholarships = load_scholarships()

# ── Step progress indicator ────────────────────────────────────────────────────
STEPS = {
    1: "📝 Your Profile",
    2: "🎯 Matches",
    3: "📊 Best Match",
    4: "📋 Action Plan",
}

st.title("🎓 Scholarship Copilot")
st.caption(
    "Your AI-powered grant and application assistant "
    "— session only, nothing is saved."
)

progress_value = (st.session_state.step - 1) / (len(STEPS) - 1)
st.progress(progress_value)

cols = st.columns(len(STEPS))
for i, (num, label) in enumerate(STEPS.items()):
    with cols[i]:
        if num < st.session_state.step:
            st.markdown(
                f"<p style='text-align:center; color:#6C63FF;'>"
                f"✅ {label}</p>",
                unsafe_allow_html=True,
            )
        elif num == st.session_state.step:
            st.markdown(
                f"<p style='text-align:center; font-weight:bold;'>"
                f"▶️ {label}</p>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<p style='text-align:center; color:gray;'>"
                f"⬜ {label}</p>",
                unsafe_allow_html=True,
            )

st.divider()

# ── STEP 1: Structured profile form ───────────────────────────────────────────
with st.expander(
    "Step 1 — Tell us about yourself",
    expanded=(st.session_state.step == 1)
):
    st.markdown("Fill in the sections below so we can find your best matches.")

    # Section A — Personal Info
    st.markdown("#### 🧑 Personal Information")
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input("Full name", placeholder="Juan dela Cruz")
        school = st.text_input(
            "School / University",
            placeholder="Asia Pacific College"
        )
    with col2:
        year_level = st.selectbox(
            "Year level",
            ["", "1st Year", "2nd Year", "3rd Year", "4th Year", "Graduate"],
        )
        level_seeking = st.selectbox(
            "Scholarship level",
            ["undergraduate", "graduate"],
        )

    st.divider()

    # Section B — Academic Info
    st.markdown("#### 📚 Academic Information")
    col3, col4 = st.columns(2)
    with col3:
        major = st.text_input(
            "Degree / Major",
            placeholder="BS Information Technology"
        )
    with col4:
        gpa_input = st.number_input(
            "GPA (100-point scale)",
            min_value=0.0,
            max_value=100.0,
            value=0.0,
            step=0.1,
            format="%.2f",
        )
        gpa = gpa_input if gpa_input > 0 else None

    st.divider()

    # Section C — Skills
    st.markdown("#### 💻 Technical Skills")
    st.caption("Select all that apply.")
    skill_options = [
        "Python", "JavaScript", "React", "Node.js", "Java",
        "SQL", "HTML/CSS", "C/C++", "PHP", "Machine Learning",
        "Data Analysis", "Mobile Development", "Cloud Computing",
        "Cybersecurity", "UI/UX Design",
    ]
    selected_skills = st.multiselect(
        "Skills",
        skill_options,
        placeholder="Choose your skills..."
    )
    other_skills = st.text_input(
        "Other skills not listed above",
        placeholder="e.g. Flutter, Docker, Figma"
    )
    if other_skills.strip():
        extra = [s.strip() for s in other_skills.split(",") if s.strip()]
        all_skills = selected_skills + extra
    else:
        all_skills = selected_skills

    st.divider()

    # Section D — Leadership & Goals
    st.markdown("#### 🏆 Leadership & Goals")
    leadership = st.text_area(
        "Leadership roles or community involvement",
        placeholder=(
            "e.g. President of IT Student Organization, "
            "volunteer tutor, hackathon organizer..."
        ),
        height=80,
    )
    goals = st.selectbox(
        "Primary scholarship goal",
        [
            "",
            "Fund my undergraduate tuition",
            "Cover living expenses while studying",
            "Study abroad for a semester",
            "Fund a full graduate degree",
            "Access an international research opportunity",
        ],
    )

    st.divider()

    if st.button("🔍 Find my scholarships", type="primary"):
        # Validation
        missing = []
        if not major.strip():
            missing.append("Degree / Major")
        if not year_level:
            missing.append("Year level")
        if not goals:
            missing.append("Primary scholarship goal")

        if missing:
            st.warning(
                f"Please fill in the following fields: "
                f"{', '.join(missing)}"
            )
        else:
            form_data = {
                "name": name,
                "school": school,
                "year_level": year_level,
                "level_seeking": level_seeking,
                "major": major,
                "gpa": gpa,
                "skills": all_skills,
                "leadership": leadership,
                "goals": goals,
            }
            with st.spinner("Searching for your best scholarship matches..."):
                st.session_state.profile = extract_profile(form_data)

                # GPA warning
                if not st.session_state.profile.get("gpa"):
                    st.warning(
                        "⚠️ No GPA entered. "
                        "Some scholarships with GPA requirements "
                        "may still appear — check eligibility carefully."
                    )

                results, source = match_scholarships(
                    st.session_state.profile, scholarships
                )
                st.session_state.matches = results
                st.session_state.match_source = source
                st.session_state.step = 2
                st.rerun()

# ── STEP 2: Top 3 Scholarship Matches ─────────────────────────────────────────
if st.session_state.matches:
    with st.expander(
        "Step 2 — Your top scholarship matches",
        expanded=(st.session_state.step == 2)
    ):
        # Source banner
        if st.session_state.match_source == "live":
            st.success(
                "🌐 Live results — sourced from real-time "
                "web search via Tavily."
            )
        else:
            st.warning(
                "📁 Showing curated local results — "
                "live search unavailable. "
                "Results are from the built-in scholarship database."
            )

        st.markdown(
            f"Here are your **top {len(st.session_state.matches)} "
            f"matches** based on your profile:"
        )

        for i, s in enumerate(st.session_state.matches):
            score = s["match_score"]
            score_color = (
                "🟢" if score >= 5
                else "🟡" if score >= 3
                else "🔴"
            )
            badge = "🏅 Best Match" if i == 0 else f"#{i + 1}"

            with st.container(border=True):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"### {badge} — {s['name']}")
                    st.caption(
                        f"{s['provider']} · "
                        f"{s['type'].capitalize()} · "
                        f"{', '.join(s['level']).capitalize()}"
                    )
                    st.markdown(f"**Benefits:** {s['benefits']}")
                    st.markdown(f"**Deadline:** {s['deadline']}")
                    st.markdown(
                        f"**Why you match:** "
                        f"{' · '.join(s['match_reasons'])}"
                    )
                    if s.get("link") and s["link"].startswith("http"):
                        st.markdown(f"[🔗 View scholarship]({s['link']})")
                with col2:
                    st.metric(
                        "Match score",
                        f"{score_color} {score}/8"
                    )
                    if i == 0:
                        if st.button(
                            "📊 View full dashboard",
                            key=f"dashboard_{i}",
                            type="primary"
                        ):
                            st.session_state.selected_scholarship = s
                            st.session_state.step = 3
                            st.rerun()
                    else:
                        if st.button(
                            "📋 View action plan",
                            key=f"action_{i}"
                        ):
                            st.session_state.selected_scholarship = s
                            st.session_state.step = 4
                            st.rerun()

# ── STEP 3: Best Match Dashboard ──────────────────────────────────────────────
if (
    st.session_state.selected_scholarship
    and st.session_state.step >= 3
):
    s = st.session_state.selected_scholarship
    p = st.session_state.profile

    with st.expander(
        "Step 3 — Why this is your best match",
        expanded=(st.session_state.step == 3)
    ):
        st.markdown(f"## 🏅 {s['name']}")
        st.caption(f"{s['provider']} · {s['type'].capitalize()}")

        st.divider()

        # Compatibility breakdown
        st.markdown("### 🔍 Compatibility Breakdown")

        col1, col2 = st.columns(2)
        with col1:
            # GPA check
            user_gpa = p.get("gpa") or 0
            req_gpa = s.get("gpa_required") or 0
            if user_gpa and user_gpa >= req_gpa:
                st.success(
                    f"✅ **GPA** — Your GPA of {user_gpa} meets "
                    f"the {req_gpa} minimum requirement."
                )
            elif user_gpa and user_gpa < req_gpa:
                st.error(
                    f"❌ **GPA** — Your GPA of {user_gpa} is below "
                    f"the {req_gpa} minimum. You may still apply "
                    f"but check official eligibility."
                )
            else:
                st.info(
                    "ℹ️ **GPA** — No GPA entered. "
                    "Verify eligibility on the official website."
                )

            # Major check
            user_major = (p.get("major") or "").lower()
            majors_lower = [m.lower() for m in s.get("majors", [])]
            if "all" in majors_lower:
                st.success(
                    f"✅ **Major** — This scholarship is open "
                    f"to all majors including {p.get('major')}."
                )
            elif any(
                user_major in m or m in user_major
                for m in majors_lower
            ):
                st.success(
                    f"✅ **Major** — Your major ({p.get('major')}) "
                    f"is a priority field for this scholarship."
                )
            else:
                st.warning(
                    f"⚠️ **Major** — Your major ({p.get('major')}) "
                    f"may not be a primary target. "
                    f"Verify on the official page."
                )

        with col2:
            # Level check
            user_level = p.get("level_seeking") or "undergraduate"
            if user_level in s.get("level", []):
                st.success(
                    f"✅ **Level** — This scholarship is available "
                    f"for {user_level} students."
                )
            else:
                st.error(
                    f"❌ **Level** — This scholarship may not be "
                    f"available for {user_level} students. "
                    f"Verify eligibility."
                )

            # Leadership check
            user_leadership = p.get("leadership") or ""
            leadership_ids = [
                "sm-foundation-it", "apc-leadership", "chevening"
            ]
            if user_leadership and s.get("id") in leadership_ids:
                st.success(
                    "✅ **Leadership** — Your leadership experience "
                    "is a strong asset for this scholarship."
                )
            elif user_leadership:
                st.info(
                    "ℹ️ **Leadership** — You have leadership "
                    "experience which may strengthen your application."
                )
            else:
                st.warning(
                    "⚠️ **Leadership** — No leadership experience "
                    "entered. Consider adding any roles, even informal ones."
                )

        st.divider()

        # Scholarship details
        st.markdown("### 📋 Scholarship Details")
        detail_col1, detail_col2 = st.columns(2)
        with detail_col1:
            st.markdown(f"**Benefits:** {s['benefits']}")
            st.markdown(f"**Deadline:** {s['deadline']}")
            st.markdown(
                f"**Type:** {s['type'].capitalize()} scholarship"
            )
        with detail_col2:
            st.markdown(f"**Core values:** {s['core_values']}")
            if s.get("link") and s["link"].startswith("http"):
                st.markdown(f"[🔗 Official website]({s['link']})")

        st.divider()

        # Essay prompt highlight
        st.markdown("### ✍️ Essay Prompt to Prepare For")
        st.info(f'"{s["essay_prompt"]}"')

        st.divider()

        if st.button(
            "📋 Generate my step-by-step action plan",
            type="primary"
        ):
            st.session_state.step = 4
            st.rerun()

# ── STEP 4: Step-by-Step Action Plan + Calendar ────────────────────────────────
if (
    st.session_state.selected_scholarship
    and st.session_state.step == 4
):
    s = st.session_state.selected_scholarship

    with st.expander(
        "Step 4 — Your application action plan",
        expanded=True
    ):
        st.markdown(f"## 📋 Action Plan: {s['name']}")
        st.caption(
            "Follow these steps to complete your application. "
            "Download the calendar file to set reminders."
        )
        st.divider()

        steps = generate_application_steps(s)
        for step in steps:
            with st.container(border=True):
                st.markdown(
                    f"### {step['icon']} Step {step['number']} "
                    f"— {step['title']}"
                )
                st.markdown(step["description"])

        st.divider()

        # Calendar download
        st.markdown("### 📅 Add milestones to your calendar")
        st.caption(
            "Download the .ics file and open it to import all "
            "4 application milestones directly into your calendar "
            "(Apple Calendar, Google Calendar, Outlook, or any "
            "standard calendar app)."
        )

        ics_bytes = generate_timeline(s)
        st.download_button(
            label="📅 Download application timeline (.ics)",
            data=ics_bytes,
            file_name=f"timeline_{s['id']}.ics",
            mime="text/calendar",
            type="primary",
        )

    st.divider()
    st.caption(
        "🔒 Privacy notice: No personal information entered in "
        "this session is stored or transmitted beyond OpenAI's API. "
        "All data clears when you close this tab."
    )