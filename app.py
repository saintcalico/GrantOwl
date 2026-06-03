import streamlit as st
import json
import os
import plotly.graph_objects as go
from datetime import datetime
from openai import OpenAI
from agents.extractor import (
    extract_from_form,
    extract_from_resume_pdf,
    extract_from_resume_image,
)
from agents.matcher import match_scholarships
from agents.explainer import (
    generate_match_rationale,
    generate_application_tips,
)
from agents.timeline import generate_timeline, generate_application_steps

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Iskolar.AI",
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

# ── Progress indicator ─────────────────────────────────────────────────────────
STEPS = {
    1: "📝 Your Profile",
    2: "🎯 Matches",
    3: "📊 Best Match",
    4: "📋 Action Plan",
}

st.title("🎓 Iskolar.AI")
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

# ── STEP 1: Input layer ────────────────────────────────────────────────────────
with st.expander(
    "Step 1 — Tell us about yourself",
    expanded=(st.session_state.step == 1),
):
    # Level selector
    level_seeking_label = st.selectbox(
        "I am applying for a scholarship for:",
        ["Undergraduate studies", "Graduate studies"],
    )
    is_graduate = level_seeking_label == "Graduate studies"
    level_seeking = "graduate" if is_graduate else "undergraduate"

    if is_graduate:
        input_method = st.radio(
            "How would you like to provide your information?",
            [
                "📄 Upload my resume (PDF or image)",
                "📝 Fill a structured form",
            ],
            horizontal=True,
        )
    else:
        input_method = "📝 Fill a structured form"

    st.divider()

    # ── Resume upload path (graduate only) ────────────────────────────────────
    if (
        is_graduate
        and input_method == "📄 Upload my resume (PDF or image)"
    ):
        st.markdown("#### 📄 Resume Upload")
        st.caption(
            "Upload your undergraduate resume or CV. "
            "Accepted: PDF, JPG, PNG. "
            "Your file is sent to OpenAI for extraction only — "
            "nothing is stored."
        )

        uploaded_file = st.file_uploader(
            "Upload your resume",
            type=["pdf", "jpg", "jpeg", "png"],
            help="PDF recommended for best extraction accuracy.",
        )

        if uploaded_file:
            st.success(
                f"✅ {uploaded_file.name} "
                f"({uploaded_file.size // 1024} KB)"
            )

            if st.button(
                "🔍 Extract my profile from resume",
                type="primary",
            ):
                file_bytes = uploaded_file.read()
                file_type = uploaded_file.type

                with st.spinner(
                    "Reading your resume and extracting "
                    "your profile..."
                ):
                    if file_type == "application/pdf":
                        profile = extract_from_resume_pdf(
                            file_bytes,
                            client,
                            level_override=level_seeking,
                        )
                    else:
                        profile = extract_from_resume_image(
                            file_bytes,
                            file_type,
                            client,
                            level_override=level_seeking,
                        )

                if "error" in profile:
                    st.error(f"❌ {profile['error']}")
                else:
                    st.session_state.profile = profile
                    with st.spinner(
                        "Searching for your best "
                        "scholarship matches..."
                    ):
                        results, source = match_scholarships(
                            st.session_state.profile,
                            scholarships,
                            client,
                        )
                        st.session_state.matches = results
                        st.session_state.match_source = source
                    st.session_state.step = 2
                    st.rerun()

    # ── Structured form path ───────────────────────────────────────────────────
    else:
        st.markdown(
            "Fill in the sections below. The more detail you "
            "provide, the more specific your matches will be."
        )

        # ── Section A: Personal Information ───────────────────────────────────
        st.markdown("#### 🧑 Personal Information")
        col1, col2 = st.columns(2)
        with col1:
            name = st.text_input(
                "Full name", placeholder="Juan dela Cruz"
            )
            school = st.text_input(
                "School / University",
                placeholder="Asia Pacific College",
            )
            school_type = st.selectbox(
                "School type",
                [
                    "",
                    "Private",
                    "Public",
                    "State University (SUC)",
                ],
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
                placeholder="e.g. Pasay City",
            )

        st.divider()

        # ── Section B: Academic Information ───────────────────────────────────
        st.markdown("#### 📚 Academic Information")
        col3, col4 = st.columns(2)
        with col3:
            program_track = st.selectbox(
                "Program track",
                [
                    "",
                    "STEM",
                    "Business",
                    "Arts & Humanities",
                    "Education",
                    "Health Sciences",
                ],
            )
            major = st.text_input(
                "Degree / Major",
                placeholder=(
                    "BS Information Technology"
                    if not is_graduate
                    else "MS Computer Science"
                ),
            )
        with col4:
            if not is_graduate:
                year_level = st.selectbox(
                    "Year level",
                    [
                        "",
                        "1st Year",
                        "2nd Year",
                        "3rd Year",
                        "4th Year",
                    ],
                )
                enrollment_status = st.selectbox(
                    "Enrollment status",
                    [
                        "Currently Enrolled",
                        "Incoming Freshman",
                        "Graduating",
                    ],
                )
            else:
                year_level = "Graduate"
                enrollment_status = "Graduate Applicant"
                st.info(
                    "📌 Graduate applicant — year level "
                    "set automatically."
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

        # Graduate-specific fields
        if is_graduate:
            st.divider()
            st.markdown("#### 🎓 Graduate-Specific Information")
            col_g1, col_g2 = st.columns(2)
            with col_g1:
                undergraduate_degree = st.text_input(
                    "Undergraduate degree completed",
                    placeholder="BS Information Technology",
                )
                thesis_topic = st.text_area(
                    "Thesis or research topic (if any)",
                    placeholder=(
                        "e.g. Machine learning for crop "
                        "disease detection in the Philippines"
                    ),
                    height=80,
                )
            with col_g2:
                work_experience = st.text_area(
                    "Relevant work experience",
                    placeholder=(
                        "e.g. 2 years as software developer "
                        "at a fintech startup"
                    ),
                    height=80,
                )
                publications = st.text_input(
                    "Publications or research papers (if any)",
                    placeholder=(
                        "e.g. Published paper in IEEE 2024"
                    ),
                )

        st.divider()

        # ── Section C: Financial Information ──────────────────────────────────
        st.markdown("#### 💰 Financial Information")
        st.caption(
            "Used only to match need-based scholarships. "
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
                "I currently have an active scholarship",
                value=False,
            )

        st.divider()

        # ── Section D: Household Information ──────────────────────────────────
        st.markdown("#### 🏠 Household Information")
        st.caption(
            "This helps match scholarships that consider "
            "family context and financial need."
        )

        col_h1, col_h2 = st.columns(2)
        with col_h1:
            household_size = st.number_input(
                "How many people live in your household? "
                "(including yourself)",
                min_value=1,
                max_value=20,
                value=1,
                step=1,
            )
        with col_h2:
            has_pwd_in_household = st.toggle(
                "There is a PWD (person with disability) "
                "in my household",
                value=False,
            )
            sibling_has_scholarship = st.toggle(
                "A sibling currently has an active scholarship",
                value=False,
            )

        # Dynamic occupation fields based on household size
        st.markdown(
            f"**Occupation of each household member** "
            f"({int(household_size)} {'person' if household_size == 1 else 'people'})"
        )
        st.caption(
            "Enter the occupation of each person. "
            "You may write 'Student', 'Unemployed', "
            "'Retired', etc."
        )

        household_occupations = []
        occ_cols = st.columns(min(int(household_size), 3))
        for idx in range(int(household_size)):
            col_idx = idx % 3
            label = (
                "Your occupation (Person 1 — you)"
                if idx == 0
                else f"Person {idx + 1} occupation"
            )
            with occ_cols[col_idx]:
                occ = st.text_input(
                    label,
                    placeholder=(
                        "e.g. Student"
                        if idx == 0
                        else "e.g. Farmer, Teacher, Driver..."
                    ),
                    key=f"occupation_{idx}",
                )
                household_occupations.append(occ)

        st.divider()

        # ── Section E: Skills ──────────────────────────────────────────────────
        st.markdown("#### 💡 Skills")
        skills_text = st.text_area(
            "Do you have any skills you'd like to mention? "
            "(optional)",
            placeholder=(
                "e.g. I know React, Node.js, and Python. "
                "I also have experience in UI/UX design "
                "and data analysis..."
            ),
            height=80,
        )

        st.divider()

        # ── Section F: Leadership & Extracurricular ────────────────────────────
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
                placeholder="Select your roles...",
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
                placeholder="Select your focus areas...",
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
            if not is_graduate and not year_level:
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
                    "has_existing_scholarship": (
                        has_existing_scholarship
                    ),
                    "household_size": int(household_size),
                    "household_occupations": household_occupations,
                    "has_pwd_in_household": has_pwd_in_household,
                    "sibling_has_scholarship": sibling_has_scholarship,
                    "skills": skills_text,
                    "leadership_roles": leadership_roles,
                    "leadership": leadership_text,
                    "extracurricular_focus": extracurricular_focus,
                    "goals": goals,
                    "thesis_topic": (
                        thesis_topic if is_graduate else None
                    ),
                    "work_experience": (
                        work_experience if is_graduate else None
                    ),
                    "publications": (
                        publications if is_graduate else None
                    ),
                    "research_experience": (
                        thesis_topic if is_graduate else None
                    ),
                }

                with st.spinner(
                    "Applying eligibility filters and searching "
                    "for your best matches..."
                ):
                    st.session_state.profile = extract_from_form(
                        form_data
                    )

                    if not st.session_state.profile.get("gpa"):
                        st.warning(
                            "⚠️ No GPA entered — scholarships with "
                            "GPA requirements may still appear. "
                            "Verify eligibility carefully."
                        )

                    results, source = match_scholarships(
                        st.session_state.profile,
                        scholarships,
                        client,
                    )
                    st.session_state.matches = results
                    st.session_state.match_source = source
                    st.session_state.step = 2
                    st.rerun()

# ── STEP 2: Top 3 Matches ──────────────────────────────────────────────────────
if st.session_state.matches:
    with st.expander(
        "Step 2 — Your top scholarship matches",
        expanded=(st.session_state.step == 2),
    ):
        if st.session_state.match_source == "live":
            st.success(
                "🌐 Live results — sourced from real-time "
                "web search via Tavily, ranked by AI adviser."
            )
        else:
            st.warning(
                "📁 Showing curated local results — "
                "live search unavailable. Ranked by AI adviser."
            )

        # Comparison bar chart
        if len(st.session_state.matches) > 1:
            st.markdown("### 📊 How your top matches compare")
            names = [
                s["name"][:30] + "..."
                if len(s["name"]) > 30
                else s["name"]
                for s in st.session_state.matches
            ]
            scores = [
                s["match_score"]
                for s in st.session_state.matches
            ]
            colors = ["#6C63FF", "#A89CF7", "#D4D0FA"]

            fig_compare = go.Figure(go.Bar(
                x=names,
                y=scores,
                marker_color=colors[:len(names)],
                text=scores,
                textposition="outside",
            ))
            fig_compare.update_layout(
                yaxis_title="AI Match Score",
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#FAFAFA",
                yaxis=dict(range=[0, 11]),
                margin=dict(t=20, b=20),
                height=300,
            )
            st.plotly_chart(fig_compare, use_container_width=True)

        st.markdown(
            f"Found **{len(st.session_state.matches)}** matches "
            f"ranked by your AI adviser:"
        )

        for i, s in enumerate(st.session_state.matches):
            score = s["match_score"]
            score_color = (
                "🟢" if score >= 7
                else "🟡" if score >= 4
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
                    if s.get("adviser_note"):
                        st.info(
                            f"💡 **Adviser:** {s['adviser_note']}"
                        )
                    if (
                        s.get("link")
                        and s["link"].startswith("http")
                    ):
                        st.markdown(
                            f"[🔗 View scholarship]({s['link']})"
                        )
                with col2:
                    st.metric(
                        "AI Score",
                        f"{score_color} {score}/10",
                    )
                    if i == 0:
                        if st.button(
                            "📊 View full dashboard",
                            key=f"dashboard_{i}",
                            type="primary",
                        ):
                            st.session_state.selected_scholarship = s
                            st.session_state.step = 3
                            with st.spinner(
                                "Generating your personalized "
                                "match analysis..."
                            ):
                                st.session_state.rationale = (
                                    generate_match_rationale(
                                        st.session_state.profile,
                                        s,
                                        client,
                                    )
                                )
                                st.session_state.tips = (
                                    generate_application_tips(
                                        st.session_state.profile,
                                        s,
                                        client,
                                    )
                                )
                            st.rerun()
                    else:
                        if st.button(
                            "📋 View action plan",
                            key=f"action_{i}",
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
        expanded=(st.session_state.step == 3),
    ):
        st.markdown(f"## 🏅 {s['name']}")
        st.caption(f"{s['provider']} · {s['type'].capitalize()}")

        if st.session_state.rationale:
            st.info(
                f"💬 **Your AI Adviser says:** "
                f"{st.session_state.rationale}"
            )

        st.divider()

        # Radar chart
        st.markdown(
            "### 🕸️ Your Profile vs. Scholarship Requirements"
        )
        user_gpa = p.get("gpa") or 0
        req_gpa = s.get("gpa_required") or 0
        user_major = (p.get("major") or "").lower()
        majors_lower = [m.lower() for m in s.get("majors", [])]
        user_skills = p.get("skills") or ""
        user_leadership = p.get("leadership_roles") or []
        user_extracurricular = p.get("extracurricular_focus") or []

        gpa_fit = (
            min((user_gpa / req_gpa) * 100, 100)
            if req_gpa > 0 and user_gpa
            else 80
        )
        major_fit = (
            100 if "all" in majors_lower
            else 90 if any(
                user_major in m or m in user_major
                for m in majors_lower
            )
            else 40
        )
        skills_fit = min(len(user_skills.split()) * 10, 100) if user_skills else 20
        leadership_fit = (
            100 if len(user_leadership) >= 2
            else 60 if len(user_leadership) == 1
            else 20
        )
        extracurricular_fit = min(
            len(user_extracurricular) * 25, 100
        )

        radar_cats = [
            "GPA Fit", "Major Fit", "Skills",
            "Leadership", "Extracurricular",
        ]
        user_vals = [
            gpa_fit, major_fit, skills_fit,
            leadership_fit, extracurricular_fit,
        ]
        radar_cats_c = radar_cats + [radar_cats[0]]
        user_vals_c = user_vals + [user_vals[0]]

        fig_radar = go.Figure()
        fig_radar.add_trace(go.Scatterpolar(
            r=[100, 100, 100, 100, 100, 100],
            theta=radar_cats_c,
            fill="toself",
            name="Scholarship Ideal",
            fillcolor="rgba(108,99,255,0.15)",
            line=dict(color="#6C63FF", width=1, dash="dash"),
        ))
        fig_radar.add_trace(go.Scatterpolar(
            r=user_vals_c,
            theta=radar_cats_c,
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

        # Horizontal bar chart
        st.markdown("### 📊 Match Score Breakdown")
        criteria_labels = [
            "GPA Fit", "Major Fit", "Skills",
            "Leadership", "Extracurricular",
        ]
        criteria_values = [
            gpa_fit, major_fit, skills_fit,
            leadership_fit, extracurricular_fit,
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

        # Deadline urgency timeline
        st.markdown("### ⏳ Time Until Deadline")
        deadline_str = s.get("deadline", "")
        try:
            deadline_dt = datetime.strptime(
                deadline_str, "%Y-%m-%d"
            )
            days_left = max(
                (deadline_dt - datetime.now()).days, 0
            )
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
                else (
                    f"🟢 {days_left} days left "
                    f"— Good time to start"
                )
            )
            fig_tl = go.Figure(go.Bar(
                x=[progress_pct * 100],
                y=["Deadline"],
                orientation="h",
                marker_color=urgency_color,
                text=[urgency_label],
                textposition="inside",
                insidetextanchor="middle",
            ))
            fig_tl.add_trace(go.Bar(
                x=[(1 - progress_pct) * 100],
                y=["Deadline"],
                orientation="h",
                marker_color="rgba(255,255,255,0.08)",
                showlegend=False,
                hoverinfo="skip",
            ))
            fig_tl.update_layout(
                barmode="stack",
                xaxis=dict(
                    range=[0, 100],
                    showgrid=False,
                    showticklabels=False,
                ),
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#FAFAFA",
                margin=dict(t=10, b=10, l=10, r=10),
                height=100,
                showlegend=False,
            )
            st.plotly_chart(fig_tl, use_container_width=True)
            st.caption(
                f"Deadline: "
                f"**{deadline_dt.strftime('%B %d, %Y')}**"
            )
        except ValueError:
            st.info(
                "ℹ️ Deadline not available — check the official "
                "website for the exact date."
            )

        st.divider()

        # Eligibility breakdown
        st.markdown("### 🔍 Eligibility Breakdown")
        elig_col1, elig_col2 = st.columns(2)
        with elig_col1:
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
            user_level = (
                p.get("level_seeking") or "undergraduate"
            )
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

            if s.get("need_based"):
                threshold = s.get("income_threshold")
                user_income = p.get("income_ceiling")
                if (
                    user_income
                    and threshold
                    and user_income <= threshold
                ):
                    st.success(
                        "✅ **Need-based** — Income bracket "
                        "qualifies."
                    )
                elif (
                    user_income
                    and threshold
                    and user_income > threshold
                ):
                    st.error(
                        f"❌ **Need-based** — Income may exceed "
                        f"₱{threshold:,}/month threshold."
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

            if user_leadership and s.get("id") in [
                "sm-foundation-it",
                "apc-leadership",
                "chevening",
            ]:
                st.success(
                    "✅ **Leadership** — Strong asset for "
                    "this scholarship."
                )
            elif user_leadership:
                st.info(
                    "ℹ️ **Leadership** — May strengthen "
                    "your application."
                )
            else:
                st.warning(
                    "⚠️ **Leadership** — None entered. "
                    "Consider adding informal roles."
                )

        st.divider()

        # Option C — AI strategic tips
        if st.session_state.tips:
            st.markdown(
                "### 🎯 Your Personalized Application Tips"
            )
            for i, tip in enumerate(st.session_state.tips):
                with st.container(border=True):
                    st.markdown(
                        f"**Tip {i+1}: {tip['title']}**"
                    )
                    st.markdown(tip["description"])

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
                st.markdown(
                    f"[🔗 Official website]({s['link']})"
                )

        st.divider()
        st.markdown("### ✍️ Essay Prompt to Prepare For")
        st.info(f'"{s["essay_prompt"]}"')
        st.divider()

        if st.button(
            "📋 Generate my step-by-step action plan",
            type="primary",
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
        expanded=True,
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