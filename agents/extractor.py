import json
import base64
import fitz  # PyMuPDF
from openai import OpenAI


# ── Shared system prompt for profile extraction ────────────────────────────────
EXTRACTION_SYSTEM_PROMPT = """You are an academic profile extraction assistant
specialized in Philippine and international scholarship applications.

Extract the following fields and return ONLY valid JSON.
No explanation, no markdown, no preamble, no code fences.

{
  "name": "string or null",
  "school": "string or null",
  "school_type": "Private or Public or State University (SUC) or null",
  "is_filipino_citizen": true or false,
  "region": "string or null (e.g. NCR (Metro Manila))",
  "city": "string or null",
  "year_level": "1st Year / 2nd Year / 3rd Year / 4th Year / Graduate or null",
  "level_seeking": "undergraduate or graduate",
  "program_track": "STEM or Business or Arts & Humanities or Education or Health Sciences or null",
  "major": "string or null (e.g. BS Information Technology)",
  "gpa": float or null (on 100-point scale),
  "enrollment_status": "Currently Enrolled or Incoming Freshman or Graduating or Graduate Applicant",
  "income_bracket": "Below ₱15,000 or ₱15,000 – ₱30,000 or ₱30,000 – ₱60,000 or Above ₱60,000 or null",
  "has_existing_scholarship": true or false,
  "skills": "string or null (free text describing skills)",
  "leadership_roles": ["list from: Student Organization Officer, Class Officer, Athlete (varsity), Volunteer / Community Worker, Event Organizer, None"],
  "extracurricular_focus": ["list from: Community Service, Research, Sports, Arts & Culture, Tech Competitions, Entrepreneurship, Environmental Advocacy"],
  "leadership": "string describing leadership experience or null",
  "goals": "string describing scholarship goal or null",
  "research_experience": "string or null (graduate only)",
  "thesis_topic": "string or null (graduate only)",
  "work_experience": "string or null (graduate only)",
  "publications": "string or null (graduate only)",
  "household_size": integer or null,
  "household_occupations": ["list of occupation strings"] or [],
  "has_pwd_in_household": true or false,
  "sibling_has_scholarship": true or false
}

If a field cannot be determined, use null.
Never invent information not present in the input.
For is_filipino_citizen, default to true if not mentioned.
For has_existing_scholarship, default to false if not mentioned.
For has_pwd_in_household, default to false if not mentioned.
For sibling_has_scholarship, default to false if not mentioned."""


def _normalize_income(label: str) -> int | None:
    income_map = {
        "Below ₱15,000": 15000,
        "₱15,000 – ₱30,000": 30000,
        "₱30,000 – ₱60,000": 60000,
        "Above ₱60,000": 999999,
    }
    return income_map.get(label, None)


def _normalize_enrollment(raw: str) -> str:
    enrollment_map = {
        "Incoming Freshman": "incoming",
        "Currently Enrolled": "enrolled",
        "Graduating": "graduating",
        "Graduate Applicant": "graduate applicant",
    }
    return enrollment_map.get(raw, "enrolled")


def _build_profile_from_dict(raw: dict) -> dict:
    """
    Normalizes a raw extracted or form dict into a
    consistent profile dict for the matcher.
    """
    income_label = raw.get("income_bracket") or ""
    enrollment_raw = raw.get("enrollment_status") or "Currently Enrolled"

    # Handle skills as free text string
    skills_raw = raw.get("skills")
    if isinstance(skills_raw, list):
        skills = ", ".join(skills_raw) if skills_raw else None
    else:
        skills = skills_raw or None

    # Normalize household occupations
    occupations = raw.get("household_occupations") or []
    if isinstance(occupations, str):
        occupations = [o.strip() for o in occupations.split(",") if o.strip()]

    return {
        # Personal
        "name": raw.get("name") or None,
        "school": raw.get("school") or None,
        "school_type": raw.get("school_type") or None,
        "is_filipino_citizen": raw.get("is_filipino_citizen", True),
        "region": raw.get("region") or None,
        "city": raw.get("city") or None,
        # Academic
        "year_level": raw.get("year_level") or None,
        "level_seeking": raw.get("level_seeking") or "undergraduate",
        "program_track": raw.get("program_track") or None,
        "major": raw.get("major") or None,
        "gpa": (
            float(raw.get("gpa"))
            if raw.get("gpa")
            else None
        ),
        "enrollment_status": _normalize_enrollment(enrollment_raw),
        # Financial
        "income_bracket": income_label or None,
        "income_ceiling": _normalize_income(income_label),
        "has_existing_scholarship": raw.get(
            "has_existing_scholarship", False
        ),
        # Household
        "household_size": (
            int(raw.get("household_size"))
            if raw.get("household_size")
            else None
        ),
        "household_occupations": occupations,
        "has_pwd_in_household": raw.get(
            "has_pwd_in_household", False
        ),
        "sibling_has_scholarship": raw.get(
            "sibling_has_scholarship", False
        ),
        # Skills (free text)
        "skills": skills,
        # Extracurricular
        "leadership_roles": raw.get("leadership_roles") or [],
        "extracurricular_focus": (
            raw.get("extracurricular_focus") or []
        ),
        "leadership": raw.get("leadership") or None,
        "goals": raw.get("goals") or None,
        # Graduate-specific
        "research_experience": raw.get("research_experience") or None,
        "thesis_topic": raw.get("thesis_topic") or None,
        "work_experience": raw.get("work_experience") or None,
        "publications": raw.get("publications") or None,
    }


def extract_from_form(form_data: dict) -> dict:
    """
    Undergraduate or graduate structured form path.
    Directly normalizes form input — no LLM call needed.
    Returns a normalized profile dict.
    """
    return _build_profile_from_dict(form_data)


def extract_from_resume_pdf(
    pdf_bytes: bytes,
    client: OpenAI,
    level_override: str | None = None,
) -> dict:
    """
    Graduate resume upload path — PDF.
    Extracts text from PDF using PyMuPDF then sends to OpenAI.
    level_override: injects the UI-selected level into the
    extracted profile, overriding whatever OpenAI inferred.
    Returns a normalized profile dict.
    """
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        doc.close()

        if not text.strip():
            return {
                "error": (
                    "Could not extract text from PDF. "
                    "Please try a different file or use "
                    "the form instead."
                )
            }

        profile = _call_openai_extraction(text, client)

        # Fix 1 — inject UI-selected level as ground truth
        if level_override and "error" not in profile:
            profile["level_seeking"] = level_override
            if level_override == "graduate":
                profile["enrollment_status"] = "graduate applicant"
                profile["year_level"] = "Graduate"

        return profile

    except Exception as e:
        return {"error": f"PDF processing error: {str(e)}"}


def extract_from_resume_image(
    image_bytes: bytes,
    mime_type: str,
    client: OpenAI,
    level_override: str | None = None,
) -> dict:
    """
    Graduate resume upload path — image (JPG/PNG).
    Sends image directly to OpenAI vision for extraction.
    level_override: injects the UI-selected level into the
    extracted profile, overriding whatever OpenAI inferred.
    Returns a normalized profile dict.
    """
    try:
        image_b64 = base64.b64encode(image_bytes).decode("utf-8")

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": EXTRACTION_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": (
                                    f"data:{mime_type};"
                                    f"base64,{image_b64}"
                                )
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                "Extract the applicant profile from "
                                "this resume image and return the JSON."
                            ),
                        },
                    ],
                },
            ],
            temperature=0.1,
            max_tokens=800,
        )

        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()

        try:
            extracted = json.loads(raw)
            profile = _build_profile_from_dict(extracted)

            # Fix 1 — inject UI-selected level as ground truth
            if level_override and "error" not in profile:
                profile["level_seeking"] = level_override
                if level_override == "graduate":
                    profile["enrollment_status"] = "graduate applicant"
                    profile["year_level"] = "Graduate"

            return profile

        except json.JSONDecodeError:
            return {
                "error": (
                    "Could not parse resume. "
                    "Please try the structured form instead."
                )
            }

    except Exception as e:
        return {"error": f"Image processing error: {str(e)}"}


def _call_openai_extraction(
    text: str,
    client: OpenAI,
) -> dict:
    """
    Sends extracted resume text to OpenAI for profile parsing.
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": EXTRACTION_SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": (
                        f"Extract the applicant profile from "
                        f"this resume text:\n\n{text}"
                    ),
                },
            ],
            temperature=0.1,
            max_tokens=800,
        )

        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()

        try:
            extracted = json.loads(raw)
            return _build_profile_from_dict(extracted)
        except json.JSONDecodeError:
            return {
                "error": (
                    "Could not parse resume content. "
                    "Please try the structured form instead."
                )
            }

    except Exception as e:
        return {"error": f"OpenAI extraction error: {str(e)}"}