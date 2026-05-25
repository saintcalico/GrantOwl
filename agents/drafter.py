from openai import OpenAI

def draft_essay(profile: dict, scholarship: dict, client: OpenAI) -> str:
    """
    Generates a tailored essay/cover letter draft.
    Uses gpt-4o-mini. Result is returned as a string — never saved.
    """
    profile_summary = f"""
Applicant: {profile.get('name', 'the applicant')}
Major: {profile.get('major', 'not specified')}
Year Level: {profile.get('year_level', 'not specified')}
GPA: {profile.get('gpa', 'not specified')}
Skills: {', '.join(profile.get('skills', []))}
Leadership: {', '.join(profile.get('leadership', []))}
Goals: {profile.get('goals', 'not specified')}
"""

    system_prompt = f"""You are an expert scholarship application writer who specializes
in helping Filipino students craft compelling, authentic essays.

Scholarship: {scholarship['name']}
Provider: {scholarship['provider']}
Core values: {scholarship['core_values']}
Essay prompt: {scholarship['essay_prompt']}

Write a 280–320 word first draft that:
1. Opens with a specific, vivid personal detail (not a generic statement)
2. Weaves the applicant's actual skills and experiences throughout
3. Connects their background directly to the scholarship's core values
4. Closes with a concrete vision of impact
5. Sounds human and authentic — not like AI generated it

Return only the essay text. No title, no notes, no explanation."""

    # Suggestion 3 — API failure handling
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Write the essay for this applicant:\n{profile_summary}"}
            ],
            temperature=0.75,
            max_tokens=600
        )
        return response.choices[0].message.content.strip()

    except Exception as e:
        return f"Essay generation failed: {str(e)}. Please try again."