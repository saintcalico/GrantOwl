import streamlit as st
from agents.extractor import (
    extract_from_form,
    extract_profile_from_text,
)
from agents.matcher import match_scholarships
import fitz  # PyMuPDF
import base64

def render_step1(client, scholarships):
    with st.expander("Step 1 — Tell us about yourself", expanded=(st.session_state.step == 1)):
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
                ["Upload my resume (PDF or image)", "Fill a structured form"],
                horizontal=True,
            )
        else:
            input_method = "Fill a structured form"

        st.divider()

        # ── Resume upload path ──
        if is_graduate and input_method == "Upload my resume (PDF or image)":
            st.markdown("#### Resume Upload")
            st.caption(
                "Upload your undergraduate resume or CV. Accepted: PDF, JPG, PNG. "
                "Your file is sent to OpenAI for extraction only — nothing is stored."
            )

            uploaded_file = st.file_uploader(
                "Upload your resume",
                type=["pdf", "jpg", "jpeg", "png"],
                help="PDF recommended for best extraction accuracy.",
            )

            if uploaded_file:
                st.success(f"File uploaded: {uploaded_file.name} ({uploaded_file.size // 1024} KB)")

                if st.button("Extract my profile from resume", type="primary"):
                    file_bytes = uploaded_file.read()
                    file_type = uploaded_file.type
                    extracted_text = ""

                    with st.spinner("Reading your resume and extracting your profile safely..."):
                        try:
                            if file_type == "application/pdf":
                                doc = fitz.open(stream=file_bytes, filetype="pdf")
                                for page in doc:
                                    extracted_text += page.get_text()
                                doc.close()
                            else:
                                # For images, we use a basic vision pass to get the text first
                                image_b64 = base64.b64encode(file_bytes).decode("utf-8")
                                response = client.chat.completions.create(
                                    model="gpt-4o-mini",
                                    messages=[
                                        {
                                            "role": "user",
                                            "content": [
                                                {"type": "text", "text": "Extract all readable text from this image perfectly."},
                                                {
                                                    "type": "image_url",
                                                    "image_url": {"url": f"data:{file_type};base64,{image_b64}"}
                                                },
                                            ],
                                        }
                                    ],
                                    max_tokens=800,
                                )
                                extracted_text = response.choices[0].message.content

                            # Pass the raw text through our hardened defensive extractor
                            profile = extract_profile_from_text(extracted_text, client)

                        except Exception as e:
                            profile = {"is_valid_resume": False, "rejection_reason": f"File processing failed: {str(e)}"}

                    # Evaluate Guardrail Output
                    if not profile.get("is_valid_resume"):
                        st.error(
                            f"Parsing Error: {profile.get('rejection_reason', 'The uploaded file could not be verified as a valid academic profile or resume.')}"
                        )
                        st.warning("Please upload a standard document layout or manually populate the entry form below.")
                    else:
                        st.success("Document analyzed and parameters structuralized successfully!")
                        # Ensure the correct level is enforced regardless of what the LLM inferred
                        profile["level_seeking"] = level_seeking
                        if is_graduate:
                            profile["enrollment_status"] = "graduate applicant"
                            profile["year_level"] = "Graduate"
                        
                        st.session_state.profile = profile
                        with st.spinner("Searching for your best scholarship matches..."):
                            results, source = match_scholarships(st.session_state.profile, scholarships, client)
                        st.session_state.matches = results
                        st.session_state.match_source = source
                        st.session_state.step = 2
                        st.rerun()

        # ── Structured form path ──
        else:
            st.markdown("Fill in the sections below. The more detail you provide, the more specific your matches will be.")

            # Section A: Personal
            st.markdown("#### Personal Information")
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Full name", placeholder="Juan dela Cruz")
                school = st.text_input("School / University", placeholder="Asia Pacific College")
                if not is_graduate:
                    school_type = st.selectbox("School type", ["", "Private", "Public"])
                else:
                    school_type = st.selectbox("School type", ["", "Private", "Public", "State University (SUC)"])
            with col2:
                is_filipino_citizen = st.toggle("I am a Filipino citizen", value=True)
                region = st.selectbox(
                    "Region",
                    [
                        "", "NCR (Metro Manila)", "Region I (Ilocos)", "Region II (Cagayan Valley)",
                        "Region III (Central Luzon)", "Region IV-A (CALABARZON)", "Region IV-B (MIMAROPA)",
                        "Region V (Bicol)", "Region VI (Western Visayas)", "Region VII (Central Visayas)",
                        "Region VIII (Eastern Visayas)", "Region IX (Zamboanga Peninsula)",
                        "Region X (Northern Mindanao)", "Region XI (Davao)", "Region XII (SOCCSKSARGEN)",
                        "Region XIII (Caraga)", "BARMM", "CAR (Cordillera)",
                    ],
                )
                city = st.text_input("City / Municipality", placeholder="e.g. Pasay City")

            st.divider()

            # Section B: Academic
            st.markdown("#### Academic Information")
            col3, col4 = st.columns(2)
            with col3:
                if not is_graduate:
                    enrollment_status = st.selectbox("Enrollment status", ["Currently Enrolled", "Incoming Freshman", "Graduating"])
                else:
                    enrollment_status = "Graduate Applicant"

                major_label = "Desired / Intended Major" if enrollment_status == "Incoming Freshman" else "Degree / Major"
                major_placeholder = "BS Information Technology" if not is_graduate else "MS Computer Science"
                major = st.text_input(major_label, placeholder=major_placeholder)

                if not is_graduate and enrollment_status == "Incoming Freshman":
                    program_track = st.selectbox(
                        "Senior High School Program Track",
                        [
                            "", "STEM (Science, Technology, Engineering, and Mathematics)", "ABM (Accountancy, Business, and Management)",
                            "HUMSS (Humanities and Social Sciences)", "GAS (General Academic Strand)", "TVL (Technical-Vocational-Livelihood)",
                            "Sports Track", "Arts and Design Track",
                        ],
                    )
                else:
                    program_track = ""
                
            with col4:
                if not is_graduate:
                    if enrollment_status != "Incoming Freshman":
                        year_level = st.selectbox("Year level", ["", "1st Year", "2nd Year", "3rd Year", "4th Year"])
                    else:
                        year_level = ""
                else:
                    year_level = "Graduate"
                    st.info("Note: Graduate applicant — year level set automatically.")

                if not is_graduate:
                    gpa_input = st.number_input("GPA (100-point scale)", min_value=0, max_value=100, value=0, step=1)
                    st.caption("Enter your grade as a whole number percentage (e.g., 92).")
                    gpa = float(gpa_input) if gpa_input > 0 else None
                else:
                    gpa_input = st.number_input("GPA", min_value=0.0, max_value=100.0, value=0.0, step=0.1, format="%.2f")
                    gpa = gpa_input if gpa_input > 0 else None

            # Graduate Specific
            if is_graduate:
                st.divider()
                st.markdown("#### Graduate-Specific Information")
                col_g1, col_g2 = st.columns(2)
                with col_g1:
                    undergraduate_degree = st.text_input("Undergraduate degree completed", placeholder="BS Information Technology")
                    thesis_topic = st.text_area("Thesis or research topic (if any)", height=80)
                with col_g2:
                    work_experience = st.text_area("Relevant work experience", height=80)
                    publications = st.text_input("Publications or research papers (if any)")

            st.divider()

            # Section C: Financial
            st.markdown("#### Financial Information")
            st.caption("Used only to match need-based scholarships. Nothing is stored.")
            col5, col6 = st.columns(2)
            with col5:
                income_bracket = st.selectbox("Monthly household income", ["", "Below ₱15,000", "₱15,000 – ₱30,000", "₱30,000 – ₱60,000", "Above ₱60,000"])
            with col6:
                has_existing_scholarship = st.toggle("I currently have an active scholarship", value=False)

            st.divider()

            # Section D: Household
            st.markdown("#### Household Information")
            col_h1, col_h2 = st.columns(2)
            with col_h1:
                household_size = st.number_input("How many people live in your household? (including yourself)", min_value=1, max_value=20, value=1, step=1)
            with col_h2:
                has_pwd_in_household = st.toggle("There is a PWD (person with disability) in my household", value=False)
                sibling_has_scholarship = st.toggle("A sibling currently has an active scholarship", value=False)

            st.markdown(f"**Occupation of each household member** ({int(household_size)} {'person' if household_size == 1 else 'people'})")
            household_occupations = []
            occ_cols = st.columns(min(int(household_size), 3))
            for idx in range(int(household_size)):
                col_idx = idx % 3
                label = "Your occupation (Person 1 — you)" if idx == 0 else f"Person {idx + 1} occupation"
                with occ_cols[col_idx]:
                    occ = st.text_input(label, key=f"occupation_{idx}")
                    household_occupations.append(occ)

            st.divider()

            # Section E: Skills
            st.markdown("#### Skills")
            skills_text = st.text_area("Do you have any skills you'd like to mention? (optional)", height=80)

            st.divider()

            # Section F: Leadership & Extracurricular
            st.markdown("#### Leadership & Extracurricular")
            col7, col8 = st.columns(2)
            with col7:
                leadership_roles_selected = st.multiselect(
                    "Leadership roles",
                    ["Student Organization Officer", "Class Officer", "Athlete (varsity)", "Volunteer / Community Worker", "Event Organizer", "None", "Others"],
                )
                if "Others" in leadership_roles_selected:
                    leadership_other_text = st.text_input("Specify other leadership roles")
                else:
                    leadership_other_text = ""
                leadership_text = st.text_area("Describe your leadership or community involvement", height=80)
                
            with col8:
                extracurricular_focus_selected = st.multiselect(
                    "Extracurricular focus",
                    ["Community Service", "Research", "Sports", "Arts & Culture", "Tech Competitions", "Entrepreneurship", "Environmental Advocacy", "Others"],
                )
                if "Others" in extracurricular_focus_selected:
                    extracurricular_other_text = st.text_input("Specify other extracurricular focus")
                else:
                    extracurricular_other_text = ""
                goals = st.selectbox(
                    "Primary scholarship goal",
                    ["", "Fund my undergraduate tuition", "Cover living expenses while studying", "Study abroad for a semester", "Fund a full graduate degree", "Access an international research opportunity"],
                )

            st.divider()
            st.caption(
                "Reminder: It is highly advisable to do your own research and not solely rely on this AI agent. "
                "Always verify details on the official scholarship websites."
            )

            if st.button("Find my scholarships", type="primary"):
                missing = []
                if not major.strip(): missing.append("Degree / Major")
                if not is_graduate and enrollment_status == "Incoming Freshman" and not program_track: missing.append("Program track")
                if not is_graduate and enrollment_status != "Incoming Freshman" and not year_level: missing.append("Year level")
                if not region: missing.append("Region")
                if not goals: missing.append("Primary scholarship goal")

                if missing:
                    st.warning(f"Please fill in: {', '.join(missing)}")
                else:
                    leadership_roles = [r for r in leadership_roles_selected if r != "Others"]
                    if leadership_other_text: leadership_roles.append(leadership_other_text)
                        
                    extracurricular_focus = [r for r in extracurricular_focus_selected if r != "Others"]
                    if extracurricular_other_text: extracurricular_focus.append(extracurricular_other_text)
                        
                    form_data = {
                        "name": name, "school": school, "school_type": school_type,
                        "is_filipino_citizen": is_filipino_citizen, "region": region, "city": city,
                        "year_level": year_level, "level_seeking": level_seeking, "program_track": program_track,
                        "major": major, "gpa": gpa, "enrollment_status": enrollment_status,
                        "income_bracket": income_bracket, "has_existing_scholarship": has_existing_scholarship,
                        "household_size": int(household_size), "household_occupations": household_occupations,
                        "has_pwd_in_household": has_pwd_in_household, "sibling_has_scholarship": sibling_has_scholarship,
                        "skills": skills_text, "leadership_roles": leadership_roles, "leadership": leadership_text,
                        "extracurricular_focus": extracurricular_focus, "goals": goals,
                        "thesis_topic": thesis_topic if is_graduate else None,
                        "work_experience": work_experience if is_graduate else None,
                        "publications": publications if is_graduate else None,
                        "research_experience": thesis_topic if is_graduate else None,
                    }

                    with st.spinner("Applying eligibility filters and searching for your best matches..."):
                        st.session_state.profile = extract_from_form(form_data)
                        if not st.session_state.profile.get("gpa"):
                            st.warning("Warning: No GPA entered — scholarships with GPA requirements may still appear.")

                        results, source = match_scholarships(st.session_state.profile, scholarships, client)
                        st.session_state.matches = results
                        st.session_state.match_source = source
                        st.session_state.step = 2
                        st.rerun()