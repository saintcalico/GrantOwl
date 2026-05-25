import json
from openai import OpenAI

def extract_profile(user_text: str, client: OpenAI) -> dict:
    """
    Takes raw user input (resume paste or bio) and returns
    a structured profile JSON. Nothing is saved — pure in-memory.
    """
    system_prompt = """You are a profile extraction assistant.
Extract the following fields from the user's text and return ONLY valid JSON.
No explanation, no markdown, no preamble.

Fields to extract:
{
  "name": "string or null",
  "year_level": "1st/2nd/3rd/4th/Graduate or null",
  "major": "string or null",
  "gpa": "float or null (on a 100-point scale)",
  "skills": ["list of technical skills"],
  "leadership": ["list of leadership roles or activities"],
  "goals": "string summarizing their academic or career goal",
  "level_seeking": "undergraduate or graduate"
}

If a field cannot be determined, use null. Never invent information."""

    # Suggestion 3 — API failure handling
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_text}
            ],
            temperature=0.1,
            max_tokens=500
        )
        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"error": "Could not parse profile. Please try rephrasing your input."}

    except Exception as e:
        return {"error": f"OpenAI API error: {str(e)}"}