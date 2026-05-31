def extract_profile(form_data: dict) -> dict:
    """
    Accepts structured form data directly from the Streamlit form.
    Normalizes all fields including new expanded profile fields.
    Nothing is saved — pure in-memory.
    """
    # Normalize income bracket to a monthly integer ceiling for comparison
    income_map = {
        "Below ₱15,000": 15000,
        "₱15,000 – ₱30,000": 30000,
        "₱30,000 – ₱60,000": 60000,
        "Above ₱60,000": 999999,
    }
    income_label = form_data.get("income_bracket", "")
    income_ceiling = income_map.get(income_label, None)

    # Normalize enrollment status to lowercase key
    enrollment_map = {
        "Incoming Freshman": "incoming",
        "Currently Enrolled": "enrolled",
        "Graduating": "graduating",
        "Graduate Applicant": "graduate applicant",
    }
    enrollment_raw = form_data.get("enrollment_status", "")
    enrollment_normalized = enrollment_map.get(enrollment_raw, "enrolled")

    # Combine selected skills + any manually typed extras
    selected_skills = form_data.get("skills", [])
    other_skills_raw = form_data.get("other_skills", "")
    extra_skills = (
        [s.strip() for s in other_skills_raw.split(",") if s.strip()]
        if other_skills_raw
        else []
    )

    return {
        # Personal
        "name": form_data.get("name", "").strip() or None,
        "school": form_data.get("school", "").strip() or None,
        "is_filipino_citizen": form_data.get("is_filipino_citizen", True),
        "region": form_data.get("region") or None,
        "city": form_data.get("city", "").strip() or None,
        # Academic
        "year_level": form_data.get("year_level") or None,
        "level_seeking": form_data.get("level_seeking") or "undergraduate",
        "program_track": form_data.get("program_track") or None,
        "major": form_data.get("major", "").strip() or None,
        "gpa": (
            float(form_data.get("gpa"))
            if form_data.get("gpa")
            else None
        ),
        "school_type": form_data.get("school_type") or None,
        "enrollment_status": enrollment_normalized,
        # Financial
        "income_bracket": income_label or None,
        "income_ceiling": income_ceiling,
        "has_existing_scholarship": form_data.get(
            "has_existing_scholarship", False
        ),
        # Extracurricular
        "skills": selected_skills + extra_skills,
        "leadership_roles": form_data.get("leadership_roles") or [],
        "extracurricular_focus": (
            form_data.get("extracurricular_focus") or []
        ),
        "leadership": form_data.get("leadership", "").strip() or None,
        "goals": form_data.get("goals") or None,
    }