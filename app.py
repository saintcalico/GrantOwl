import streamlit as st
import json
import os
import plotly.graph_objects as go
from datetime import datetime
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

# ── Session state ──────────────────────────────────────────────────────────────
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

# ── Loaders ────────────────────────────────────────────────────────────────────
@st.cache_resource
def get_client():
    return OpenAI(api_key=os.environ.get("OPENAI_API_KEY", ""))

@st.cache_data
def load_scholarships():
    with open("data/scholarships.json", "r") as f:
        return json.load(f)

scholarships = load_scholarships()

# ── Progress indicator ─────────────────────────────────────────────────────────
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
                f"<p style='text-align:center;color:#6C63FF;'>"
                f"✅ {label}</p>",
                unsafe_allow_html=True,
            )
        elif num == st.session_state.step:
            st.markdown(
                f"<p style='text-align:center;font-weight:bold;'>"
                f"▶️ {label}</p>",
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f"<p style='text-align:center;color:gray;'>"
                f"⬜ {label}</p>",
                unsafe_allow_html=True,
            )

st.divider()

# ── STEP 1: Expanded structured form ──────────────────────────────────────────
with st.expander(
    "Step 1 — Tell us about yourself",
    expanded=(st.session_state.step == 1)
):
    st.markdown(
        "Fill in all sections so the agent can find your most "
        "specific matches."
    )

    # ── Section A: Personal Information ───────────────────────────────────────
    st.markdown("#### 🧑 Personal Information")
    col1, col2 = st.columns(2)
    with col1:
        name = st.text_input(
            "Full name", placeholder="Juan dela Cruz"
        )
        school = st.text_input(
            "School / University",
            placeholder="Asia Pacific College"
        )
        school_type = st.selectbox(
            "School type",
            ["", "Private", "Public", "State University (SUC)"],
        )
    with col2:
        is_filipino_citizen = st.toggle(
            "I am a Filipino citizen", value=True
        )
        region = st.selectbox(
            "Region",
            [
                "",
                "NCR (Metro Manila)",
                "Region I (Ilocos)",
                "Region II (Cagayan Valley)",
                "Region III (Central Luzon)",
                "Region IV-A (CALABARZON)",
                "Region IV-B (MIMAROPA)",
                "Region V (Bicol)",
                "Region VI (Western Visayas)",
                "Region VII (Central Visayas)",
                "Region VIII (Eastern Visayas)",
                "Region IX (Zamboanga Peninsula)",
                "Region X (Northern Mindanao)",
                "Region XI (Davao)",
                "Region XII (SOCCSKSARGEN)",
                "Region XIII (Caraga)",
                "BARMM",
                "CAR (Cordillera)",
            ],
        )
        city = st.text_input(
            "City / Municipality",
            placeholder="e.g. Pasay City"
        )

    st.divider()

    # ── Section B: Academic Information ───────────────────────────────────────
    st.markdown("#### 📚 Academic Information")
    col3, col4 = st.columns(2)
    with col3:
        program_track = st.selectbox(
            "Program track",
            ["", "STEM", "Business", "Arts & Humanities",
             "Education", "Health Sciences"],
        )
        major = st.text_input(
            "Degree / Major",
            placeholder="BS Information Technology"
        )
        level_seeking = st.selectbox(
            "Scholarship level",
            ["undergraduate", "graduate"],
        )
    with col4:
        year_level = st.selectbox(
            "Year level",
            ["", "1st Year", "2nd Year", "3rd Year",
             "4th Year", "Graduate"],
        )
        enrollment_status = st.selectbox(
            "Enrollment status",
            [
                "Currently Enrolled",
                "Incoming Freshman",
                "Graduating",
                "Graduate Applicant",
            ],
        )
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

    # ── Section C: Financial Information ──────────────────────────────────────
    st.markdown("#### 💰 Financial Information")
    st.caption(
        "This is used only to match need-based scholarships. "
        "Nothing is stored."
    )
    col5, col6 = st.columns(2)
    with col5:
        income_bracket = st.selectbox(
            "Monthly household income",
            [
                "",
                "Below ₱15,000",
                "₱15,000 – ₱30,000",
                "₱30,000 – ₱60,000",
                "Above ₱60,000",
            ],
        )
    with col6:
        has_existing_scholarship = st.toggle(
            "I currently have an active scholarship", value=False
        )

    st.divider()

    # ── Section D: Skills ──────────────────────────────────────────────────────
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

    st.divider()

    # ── Section E: Leadership & Extracurricular ────────────────────────────────
    st.markdown("#### 🏆 Leadership & Extracurricular")
    col7, col8 = st.columns(2)
    with col7:
        leadership_roles = st.multiselect(
            "Leadership roles",
            [
                "Student Organization Officer",
                "Class Officer",
                "Athlete (varsity)",
                "Volunteer / Community Worker",
                "Event Organizer",
                "None",
            ],
            placeholder="Select your roles..."
        )
        leadership_text = st.text_area(
            "Describe your leadership or community involvement",
            placeholder=(
                "e.g. President of IT Student Organization, "
                "organized inter-school hackathon..."
            ),
            height=80,
        )
    with col8:
        extracurricular_focus = st.multiselect(
            "Extracurricular focus",
            [
                "Community Service",
                "Research",
                "Sports",
                "Arts & Culture",
                "Tech Competitions",
                "Entrepreneurship",
                "Environmental Advocacy",
            ],
            placeholder="Select your focus areas..."
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
        missing = []
        if not major.strip():
            missing.append("Degree / Major")
        if not program_track:
            missing.append("Program track")
        if not year_level:
            missing.append("Year level")
        if not region:
            missing.append("Region")
        if not goals:
            missing.append("Primary scholarship goal")

        if missing:
            st.warning(
                f"Please fill in: {', '.join(missing)}"
            )
        else:
            form_data = {
                "name": name,
                "school": school,
                "school_type": school_type,
                "is_filipino_citizen": is_filipino_citizen,
                "region": region,
                "city": city,
                "year_level": year_level,
                "level_seeking": level_seeking,
                "program_track": program_track,
                "major": major,
                "gpa": gpa,
                "enrollment_status": enrollment_status,
                "income_bracket": income_bracket,
                "has_existing_scholarship": has_existing_scholarship,
                "skills": selected_skills,
                "other_skills": other_skills,
                "leadership_roles": leadership_roles,
                "leadership": leadership_text,
                "extracurricular_focus": extracurricular_focus,
                "goals": goals,
            }

            with st.spinner(
                "Applying eligibility filters and searching "
                "for your best matches..."
            ):
                st.session_state.profile = extract_profile(form_data)

                if not st.session_state.profile.get("gpa"):
                    st.warning(
                        "⚠️ No GPA entered — scholarships with "
                        "GPA requirements may still appear. "
                        "Verify eligibility carefully."
                    )

                results, source = match_scholarships(
                    st.session_state.profile, scholarships
                )
                st.session_state.matches = results
                st.session_state.match_source = source
                st.session_state.step = 2
                st.rerun()

# ── STEP 2: Top 3 Matches ──────────────────────────────────────────────────────
if st.session_state.matches:
    with st.expander(
        "Step 2 — Your top scholarship matches",
        expanded=(st.session_state.step == 2)
    ):
        if st.session_state.match_source == "live":
            st.success(
                "🌐 Live results — sourced from real-time "
                "web search via Tavily."
            )
        else:
            st.warning(
                "📁 Showing curated local results — "
                "live search unavailable."
            )

        # ── Comparison bar chart: top 3 side by side ──────────────────────────
        if len(st.session_state.matches) > 1:
            st.markdown("### 📊 How your top matches compare")
            names = [
                s["name"][:30] + "..."
                if len(s["name"]) > 30
                else s["name"]
                for s in st.session_state.matches
            ]
            scores = [s["match_score"] for s in st.session_state.matches]
            colors = ["#6C63FF", "#A89CF7", "#D4D0FA"]

            fig_compare = go.Figure(
                go.Bar(
                    x=names,
                    y=scores,
                    marker_color=colors[:len(names)],
                    text=scores,
                    textposition="outside",
                )
            )
            fig_compare.update_layout(
                yaxis_title="Match Score",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#FAFAFA",
                yaxis=dict(range=[0, 10]),
                margin=dict(t=20, b=20),
                height=300,
            )
            st.plotly_chart(fig_compare, use_container_width=True)

        st.markdown(
            f"Found **{len(st.session_state.matches)}** "
            f"matches based on your profile:"
        )

        for i, s in enumerate(st.session_state.matches):
            score = s["match_score"]
            score_color = (
                "🟢" if score >= 5 else "🟡" if score >= 3 else "🔴"
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
                        st.markdown(
                            f"[🔗 View scholarship]({s['link']})"
                        )
                with col2:
                    st.metric(
                        "Match score", f"{score_color} {score}/8"
                    )
                    if i == 0:
                        if st.button(
                            "📊 View full dashboard",
                            key=f"dashboard_{i}",
                            type="primary",
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

        # ── Graph 1: Radar chart — profile vs requirements ─────────────────────
        st.markdown("### 🕸️ Your Profile vs. Scholarship Requirements")

        user_gpa = p.get("gpa") or 0
        req_gpa = s.get("gpa_required") or 0
        user_major = (p.get("major") or "").lower()
        majors_lower = [m.lower() for m in s.get("majors", [])]
        user_skills = p.get("skills") or []
        user_leadership = p.get("leadership_roles") or []
        user_extracurricular = p.get("extracurricular_focus") or []

        # Normalize each dimension to 0–100
        gpa_fit = (
            min((user_gpa / req_gpa) * 100, 100)
            if req_gpa > 0 and user_gpa
            else 80
        )
        major_fit = (
            100
            if "all" in majors_lower
            else 90
            if any(
                user_major in m or m in user_major
                for m in majors_lower
            )
            else 40
        )
        skills_fit = min(len(user_skills) * 15, 100)
        leadership_fit = (
            100
            if len(user_leadership) >= 2
            else 60
            if len(user_leadership) == 1
            else 20
        )
        extracurricular_fit = min(len(user_extracurricular) * 25, 100)

        radar_categories = [
            "GPA Fit", "Major Fit", "Skills",
            "Leadership", "Extracurricular"
        ]
        user_values = [
            gpa_fit, major_fit, skills_fit,
            leadership_fit, extracurricular_fit
        ]
        # Close the polygon
        radar_categories_closed = radar_categories + [radar_categories[0]]
        user_values_closed = user_values + [user_values[0]]
        ideal_values_closed = [100, 100, 100, 100, 100, 100]

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=ideal_values_closed,
            theta=radar_categories_closed,
            fill="toself",
            name="Scholarship Ideal",
            fillcolor="rgba(108,99,255,0.15)",
            line=dict(color="#6C63FF", width=1, dash="dash"),
        ))
        fig_radar.add_trace(go.Scatterpolar(
            r=user_values_closed,
            theta=radar_categories_closed,
            fill="toself",
            name="Your Profile",
            fillcolor="rgba(108,99,255,0.4)",
            line=dict(color="#6C63FF", width=2),
        ))
        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 100],
                    tickfont=dict(color="#FAFAFA"),
                    gridcolor="rgba(255,255,255,0.1)",
                ),
                angularaxis=dict(
                    tickfont=dict(color="#FAFAFA"),
                    gridcolor="rgba(255,255,255,0.1)",
                ),
                bgcolor="rgba(0,0,0,0)",
            ),
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#FAFAFA",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=-0.2,
                xanchor="center",
                x=0.5,
            ),
            margin=dict(t=20, b=40),
            height=380,
        )
        st.plotly_chart(fig_radar, use_container_width=True)

        st.divider()

        # ── Graph 2: Horizontal bar — score breakdown ──────────────────────────
        st.markdown("### 📊 Match Score Breakdown")

        criteria_labels = [
            "GPA Fit", "Major Fit", "Skills",
            "Leadership", "Extracurricular"
        ]
        criteria_values = [
            gpa_fit, major_fit, skills_fit,
            leadership_fit, extracurricular_fit
        ]
        bar_colors = [
            "#6C63FF" if v >= 70
            else "#F6C90E" if v >= 40
            else "#E05C5C"
            for v in criteria_values
        ]

        fig_bar = go.Figure(go.Bar(
            x=criteria_values,
            y=criteria_labels,
            orientation="h",
            marker_color=bar_colors,
            text=[f"{v:.0f}%" for v in criteria_values],
            textposition="outside",
        ))
        fig_bar.update_layout(
            xaxis=dict(range=[0, 120], showgrid=False),
            yaxis=dict(autorange="reversed"),
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#FAFAFA",
            margin=dict(t=10, b=10, l=10, r=60),
            height=280,
        )
        st.plotly_chart(fig_bar, use_container_width=True)

        st.divider()

        # ── Graph 3: Deadline urgency timeline ────────────────────────────────
        st.markdown("### ⏳ Time Until Deadline")

        deadline_str = s.get("deadline", "")
        try:
            deadline_dt = datetime.strptime(deadline_str, "%Y-%m-%d")
            days_left = (deadline_dt - datetime.now()).days
            days_left = max(days_left, 0)
            total_days = 180
            progress_pct = min(
                (total_days - days_left) / total_days, 1.0
            )
            urgency_color = (
                "#E05C5C" if days_left < 21
                else "#F6C90E" if days_left < 42
                else "#6C63FF"
            )
            urgency_label = (
                f"🔴 {days_left} days left — Act now!"
                if days_left < 21
                else f"🟡 {days_left} days left — Start preparing"
                if days_left < 42
                else f"🟢 {days_left} days left — Good time to start"
            )

            fig_timeline = go.Figure(go.Bar(
                x=[progress_pct * 100],
                y=["Deadline"],
                orientation="h",
                marker_color=urgency_color,
                text=[urgency_label],
                textposition="inside",
                insidetextanchor="middle",
            ))
            fig_timeline.add_trace(go.Bar(
                x=[(1 - progress_pct) * 100],
                y=["Deadline"],
                orientation="h",
                marker_color="rgba(255,255,255,0.08)",
                showlegend=False,
                hoverinfo="skip",
            ))
            fig_timeline.update_layout(
                barmode="stack",
                xaxis=dict(range=[0, 100], showgrid=False,
                           showticklabels=False),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#FAFAFA",
                margin=dict(t=10, b=10, l=10, r=10),
                height=100,
                showlegend=False,
            )
            st.plotly_chart(fig_timeline, use_container_width=True)
            st.caption(
                f"Deadline: **{deadline_dt.strftime('%B %d, %Y')}**"
            )

        except ValueError:
            st.info(
                "ℹ️ Deadline not available — check the official "
                "website for the exact date."
            )

        st.divider()

        # ── Compatibility breakdown (text) ─────────────────────────────────────
        st.markdown("### 🔍 Eligibility Breakdown")
        elig_col1, elig_col2 = st.columns(2)

        with elig_col1:
            # GPA
            if user_gpa and req_gpa and user_gpa >= req_gpa:
                st.success(
                    f"✅ **GPA** — {user_gpa} meets "
                    f"the {req_gpa} minimum."
                )
            elif user_gpa and req_gpa and user_gpa < req_gpa:
                st.error(
                    f"❌ **GPA** — {user_gpa} is below "
                    f"the {req_gpa} minimum."
                )
            else:
                st.info("ℹ️ **GPA** — Verify on official website.")

            # Major
            if "all" in majors_lower:
                st.success(
                    f"✅ **Major** — Open to all majors "
                    f"including {p.get('major')}."
                )
            elif any(
                user_major in m or m in user_major
                for m in majors_lower
            ):
                st.success(
                    f"✅ **Major** — {p.get('major')} "
                    f"is a priority field."
                )
            else:
                st.warning(
                    f"⚠️ **Major** — {p.get('major')} may not "
                    f"be a primary target. Verify eligibility."
                )

            # Citizenship
            if s.get("requires_filipino_citizen"):
                if p.get("is_filipino_citizen"):
                    st.success(
                        "✅ **Citizenship** — Filipino citizen "
                        "requirement met."
                    )
                else:
                    st.error(
                        "❌ **Citizenship** — Filipino citizen "
                        "required."
                    )
            else:
                st.success(
                    "✅ **Citizenship** — No citizenship "
                    "restriction."
                )

        with elig_col2:
            # Level
            user_level = p.get("level_seeking") or "undergraduate"
            if user_level in s.get("level", []):
                st.success(
                    f"✅ **Level** — Available for "
                    f"{user_level} students."
                )
            else:
                st.error(
                    f"❌ **Level** — May not be available for "
                    f"{user_level} students."
                )

            # Need-based
            if s.get("need_based"):
                threshold = s.get("income_threshold")
                user_income = p.get("income_ceiling")
                if user_income and threshold and user_income <= threshold:
                    st.success(
                        f"✅ **Need-based** — Your income "
                        f"bracket qualifies."
                    )
                elif user_income and threshold and user_income > threshold:
                    st.error(
                        f"❌ **Need-based** — Income may exceed "
                        f"the ₱{threshold:,}/month threshold."
                    )
                else:
                    st.info(
                        "ℹ️ **Need-based** — Verify income "
                        "requirements on official page."
                    )
            else:
                st.success(
                    "✅ **Need-based** — Not income-restricted."
                )

            # Leadership
            if user_leadership and s.get("id") in [
                "sm-foundation-it", "apc-leadership", "chevening"
            ]:
                st.success(
                    "✅ **Leadership** — Your leadership "
                    "experience is a strong asset."
                )
            elif user_leadership:
                st.info(
                    "ℹ️ **Leadership** — Experience may "
                    "strengthen your application."
                )
            else:
                st.warning(
                    "⚠️ **Leadership** — None entered. "
                    "Consider adding informal roles."
                )

        st.divider()

        # Scholarship details
        st.markdown("### 📋 Scholarship Details")
        det_col1, det_col2 = st.columns(2)
        with det_col1:
            st.markdown(f"**Benefits:** {s['benefits']}")
            st.markdown(f"**Deadline:** {s['deadline']}")
            st.markdown(
                f"**Type:** {s['type'].capitalize()} scholarship"
            )
        with det_col2:
            st.markdown(f"**Core values:** {s['core_values']}")
            if s.get("link") and s["link"].startswith("http"):
                st.markdown(f"[🔗 Official website]({s['link']})")

        st.divider()

        st.markdown("### ✍️ Essay Prompt to Prepare For")
        st.info(f'"{s["essay_prompt"]}"')
        st.divider()

        if st.button(
            "📋 Generate my step-by-step action plan",
            type="primary"
        ):
            st.session_state.step = 4
            st.rerun()

# ── STEP 4: Action Plan + Calendar ────────────────────────────────────────────
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

        st.markdown("### 📅 Add milestones to your calendar")
        st.caption(
            "Download the .ics file and open it to import all "
            "4 milestones into Apple Calendar, Google Calendar, "
            "or Outlook."
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