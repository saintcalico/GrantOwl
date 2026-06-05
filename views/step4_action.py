import streamlit as st
import datetime

def generate_ics_content(scholarship_name, deadlines_dict):
    """
    Generates an RFC 5545 compliant iCalendar payload string.
    Ensures strict date syntax tracking and unique UIDs for error-free ingestion.
    """
    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//GrantOwl//Scholarship Tracker Framework//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH"
    ]
    
    current_timestamp = datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    
    for index, (task_title, date_obj) in enumerate(deadlines_dict.items()):
        if isinstance(date_obj, (datetime.date, datetime.datetime)):
            date_str = date_obj.strftime("%Y%m%d")
            end_date_obj = date_obj + datetime.timedelta(days=1)
            end_date_str = end_date_obj.strftime("%Y%m%d")
        else:
            continue

        ics_lines.extend([
            "BEGIN:VEVENT",
            f"UID:grantowl-{index}-{current_timestamp}@iskolar.ai",
            f"DTSTAMP:{current_timestamp}",
            f"DTSTART;VALUE=DATE:{date_str}",
            f"DTEND;VALUE=DATE:{end_date_str}",
            f"SUMMARY:[GrantOwl] {task_title}",
            f"DESCRIPTION:Action item tracker milestone for your upcoming {scholarship_name} application requirements.",
            "STATUS:CONFIRMED",
            "SEQUENCE:0",
            "END:VEVENT"
        ])
        
    ics_lines.append("END:VCALENDAR")
    return "\r\n".join(ics_lines)

def render_step4():
    if st.session_state.step < 4 or not st.session_state.selected_scholarship:
        return

    s = st.session_state.selected_scholarship
    p = st.session_state.profile or {}
    
    st.markdown(f"## 📋 Tactical Action Plan: {s['name']}")
    st.caption(f"Target Track: {p.get('major', 'Your Major')} | Provider: {s['provider']}")
    st.divider()

    # ── SECTION 1: MASTER PHASE MILESTONES & CALENDAR EXPORT ──────────────────
    st.markdown("### 📅 Phase 1 — Milestone Tracking & Calendar Synchronization")
    st.write("Sync your personalized application timeline milestones directly into your personal digital calendar platform.")

    today = datetime.date.today()
    milestones = {
        f"Gather Eligibility Documents for {s['name']}": today + datetime.timedelta(days=3),
        f"Draft Personal Statements & Essay Rationales": today + datetime.timedelta(days=7),
        f"Refine Technical Portfolio Layouts": today + datetime.timedelta(days=14),
        f"Final Submission Review Gate": today + datetime.timedelta(days=21)
    }

    # Left column for the download engine, right column for the quick instruction card
    col_dl, col_inst = st.columns([2, 3])
    
    with col_dl:
        ics_string = generate_ics_content(s['name'], milestones)
        st.write("") # Spacing padding
        st.download_button(
            label="📥 Download Calendar (.ics) File",
            data=ics_string,
            file_name=f"GrantOwl_{s['name'].replace(' ', '_')}_Timeline.ics",
            mime="text/calendar",
            type="primary",
            use_container_width=True
        )
        
        # Chronological layout table view of deadlines
        st.markdown("**Timeline Summary Breakdown:**")
        for task, task_date in milestones.items():
            st.write(f"• `{task_date.strftime('%B %d, %Y')}` — {task}")

    with col_inst:
        with st.container(border=True):
            st.markdown("##### 💡 Google Calendar Import Guide")
            st.markdown(
                "1. Download the generated `.ics` file.\n"
                "2. Open **Google Calendar** and click the gear icon ➔ **Settings**.\n"
                "3. Navigate to **Import & export** in the left sidebar menu.\n"
                "4. Upload the file and choose your destination calendar tracker."
            )

    st.divider()

    # ── SECTION 2: DOCUMENT CHECKLIST (SOFT VS HARD COPIES) ─────────────────
    st.markdown("### 📑 Phase 2 — Required Documentation Checklist")
    st.write("Keep track of your document compilation states to prevent accidental processing disqualifications.")

    col_soft, col_hard = st.columns(2)

    with col_soft:
        with st.container(border=True):
            st.markdown("#### 🌐 Digital/Soft Copy Assets")
            st.checkbox("Anonymized, Updated Technical Resume (PDF format)", value=True)
            st.checkbox("Certified True Copy of Grades / Academic Transcripts", value=False)
            st.checkbox("Digital Portfolio / GitHub Repository Links (For Tech Grants)", value=False)
            st.checkbox("Scanned Copy of Valid School ID or Certificate of Enrollment", value=False)

    with col_hard:
        with st.container(border=True):
            st.markdown("#### 🏢 Physical/Hard Copy Originals")
            st.checkbox("Signed Scholarship Application Forms", value=False)
            st.checkbox("Certificate of Good Moral Character from Academic Registrar", value=False)
            st.checkbox("BIR Income Tax Return (ITR) or Certificate of Indigency", value=False)
            st.checkbox("Formal Letters of Recommendation (2 Faculty Members)", value=False)

    st.divider()

    # ── SECTION 3: STRATEGIC ESSAY COGNITIVE BREAKDOWN ──────────────────────
    st.markdown("### 🧠 Phase 3 — Personal Narrative & Essay Strategy")
    st.write("Tailor your personal statements to emphasize specific high-value vectors that match the reviewer committee's baseline requirements.")

    # Tailoring tips based on user's profile attributes
    with st.container(border=True):
        st.markdown(f"#### 🎯 Strategic Essay Themes for {s['name']}")
        
        st.markdown(
            "##### 1. Bridge the Practical Experience Matrix\n"
            "Since your background includes specialized technical exposure—such as your data analytics framework models and internship "
            "contributions—ensure your introduction immediately frames your academic intentions through a problem-solving lens. "
            "Discuss how your practical technical tool experience positions you for immediate contribution to the grantor's objectives."
        )
        
        st.markdown(
            "##### 2. Emphasize Community Alignment Indices\n"
            "Incorporate your administrative and external collaboration milestones into your narrative. "
            "Do not just list leadership titles; explicitly describe how organizing complex projects and community events "
            "honed your capacity to champion educational advocacy objectives outside the classroom."
        )
        
        st.markdown(
            "##### 3. Contextualize Analytical Readiness\n"
            "If your profile lacks traditional research variables (such as a finalized thesis topic track), pivot this space "
            "to focus on empirical project deployments. Explicitly showcase how your automated systems engineering work or predictive accuracy "
            "models serve as reliable proxies for rigorous, data-driven analytical inquiries."
        )

    st.divider()

    # Back Navigation Controller
    if st.button("← Back to Match Dashboard", type="secondary"):
        st.session_state.step = 3
        st.rerun()