import json
from openai import OpenAI


def generate_match_rationale(
    profile: dict,
    scholarship: dict,
    client: OpenAI,
) -> str:
    """
    Option B — Generates a personalized 2-3 sentence rationale
    explaining why this specific scholarship is the best fit
    for this specific student.
    Returns a plain string. Nothing is saved.
    """
    profile_summary = _build_profile_summary(profile)

    system_prompt = """You are a warm, encouraging Philippine scholarship
adviser writing directly to a student applicant.

Write 2-3 sentences explaining specifically why this scholarship is a
strong fit for them personally. Be specific — reference their actual
major, GPA, skills, or leadership roles. Do not use generic language.
Do not start with 'I' or 'This scholarship'. Sound like a real adviser
talking to a student, not an AI generating text.

Return only the 2-3 sentences. No title, no label, no extra text."""

    scholarship_context = f"""
Scholarship: {scholarship['name']}
Provider: {scholarship['provider']}
Core values: {scholarship['core_values']}
Benefits: {scholarship['benefits']}
Essay prompt: {scholarship['essay_prompt']}
Adviser note from matching: {scholarship.get('adviser_note', '')}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Student profile:\n{profile_summary}\n\n"
                        f"Scholarship:\n{scholarship_context}"
                    ),
                },
            ],
            temperature=0.7,
            max_tokens=200,
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return (
            f"This scholarship aligns well with your profile. "
            f"Review the compatibility breakdown below for details."
        )


def generate_application_tips(
    profile: dict,
    scholarship: dict,
    client: OpenAI,
) -> list[dict]:
    """
    Option C — Generates 3 personalized strategic tips for this
    specific student applying to this specific scholarship.
    Returns a list of tip dicts with title and description.
    Nothing is saved.
    """
    profile_summary = _build_profile_summary(profile)

    system_prompt = """You are an expert Philippine scholarship application
coach giving personalized advice to a student.

Generate exactly 3 strategic tips for this specific student applying to
this specific scholarship. Each tip must:
1. Be specific to their profile — reference their actual major, skills,
   GPA, or experiences
2. Be actionable — something they can actually do
3. Be honest — if there is a weakness, address it directly

Return ONLY a valid JSON array, no markdown, no preamble:
[
  {
    "title": "short tip title (5-7 words)",
    "description": "2-3 sentences of specific actionable advice"
  },
  {
    "title": "...",
    "description": "..."
  },
  {
    "title": "...",
    "description": "..."
  }
]"""

    scholarship_context = f"""
Scholarship: {scholarship['name']}
Provider: {scholarship['provider']}
Core values: {scholarship['core_values']}
Essay prompt: {scholarship['essay_prompt']}
GPA required: {scholarship.get('gpa_required', 0)}
Benefits: {scholarship['benefits']}
Adviser note: {scholarship.get('adviser_note', '')}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Student profile:\n{profile_summary}\n\n"
                        f"Scholarship:\n{scholarship_context}"
                    ),
                },
            ],
            temperature=0.6,
            max_tokens=500,
        )

        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        tips = json.loads(raw)

        if isinstance(tips, list) and len(tips) == 3:
            return tips

        return _fallback_tips()

    except Exception:
        return _fallback_tips()


def _fallback_tips() -> list[dict]:
    return [
        {
            "title": "Review the official requirements carefully",
            "description": (
                "Visit the scholarship's official website and download "
                "the full requirements checklist. Many applications are "
                "disqualified due to missing documents, not weak profiles."
            ),
        },
        {
            "title": "Start your essay early",
            "description": (
                "Give yourself at least 2 weeks to write and revise your "
                "essay. A rushed essay is easy to spot. Use the essay "
                "prompt provided and connect your experiences to the "
                "scholarship's core values."
            ),
        },
        {
            "title": "Request recommendation letters immediately",
            "description": (
                "Contact your professor or adviser today — not next week. "
                "Give them at least 3 weeks and provide a brief summary "
                "of the scholarship so they can write a targeted letter."
            ),
        },
    ]


def _build_profile_summary(profile: dict) -> str:
    return f"""
Name: {profile.get('name') or 'Not provided'}
Major: {profile.get('major') or 'Not provided'}
Program Track: {profile.get('program_track') or 'Not provided'}
Year Level: {profile.get('year_level') or 'Not provided'}
GPA: {profile.get('gpa') or 'Not provided'}
Level: {profile.get('level_seeking') or 'undergraduate'}
School: {profile.get('school') or 'Not provided'}
Region: {profile.get('region') or 'Not provided'}
Skills: {', '.join(profile.get('skills') or []) or 'Not provided'}
Leadership Roles: {', '.join(profile.get('leadership_roles') or []) or 'None'}
Extracurricular: {', '.join(profile.get('extracurricular_focus') or []) or 'None'}
Leadership Description: {profile.get('leadership') or 'Not provided'}
Goals: {profile.get('goals') or 'Not provided'}
Research Experience: {profile.get('research_experience') or 'N/A'}
Thesis Topic: {profile.get('thesis_topic') or 'N/A'}
Work Experience: {profile.get('work_experience') or 'N/A'}
Income Bracket: {profile.get('income_bracket') or 'Not provided'}
"""