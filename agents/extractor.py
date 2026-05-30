def extract_profile(form_data: dict) -> dict:
    """
    Accepts structured form data directly from the Streamlit form.
    No LLM call needed — profile is already structured.
    Returns a normalized profile dict for the matcher.
    Nothing is saved — pure in-memory.
    """
    return {
        "name": form_data.get("name", "").strip() or None,
        "year_level": form_data.get("year_level") or None,
        "major": form_data.get("major", "").strip() or None,
        "gpa": float(form_data.get("gpa")) if form_data.get("gpa") else None,
        "skills": form_data.get("skills") or [],
        "leadership": form_data.get("leadership", "").strip() or None,
        "goals": form_data.get("goals") or None,
        "level_seeking": form_data.get("level_seeking") or "undergraduate",
        "school": form_data.get("school", "").strip() or None,
    }