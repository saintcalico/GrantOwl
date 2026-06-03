import os
import json
from tavily import TavilyClient
from openai import OpenAI


# ── Layer 3 — URL quality filter ───────────────────────────────────────────────
JUNK_PATTERNS = [
    "top-10", "top10", "best-scholarships", "scholarships.com",
    "findgrants", "find-grants", "scholarship-list", "listicle",
    "pinterest", "quora", "reddit", "facebook", "twitter",
    "youtube", "tiktok", "blogspot", "wordpress.com",
    "buzzfeed", "ranker", "listverse", "wikihow",
]


def _is_quality_url(url: str, title: str) -> bool:
    combined = (url + " " + title).lower()
    return not any(pattern in combined for pattern in JUNK_PATTERNS)


# ── Layer 1 — Hard filter rules ────────────────────────────────────────────────
def _passes_hard_filters(
    scholarship: dict, profile: dict
) -> tuple[bool, str]:
    """
    Applies deterministic eligibility gates before any scoring.
    Returns (passes: bool, reason_if_failed: str).
    """
    user_level = (
        profile.get("level_seeking") or "undergraduate"
    ).lower()
    user_enrollment = profile.get("enrollment_status") or "enrolled"
    user_track = (profile.get("program_track") or "").upper()
    user_income = profile.get("income_ceiling")
    user_citizen = profile.get("is_filipino_citizen", True)
    user_has_grant = profile.get("has_existing_scholarship", False)
    user_school_type = (profile.get("school_type") or "").lower()
    user_region = (profile.get("region") or "").strip()
    user_gpa = profile.get("gpa") or 0

    # Level match — hard gate
    if user_level not in scholarship.get("level", []):
        return False, "Level mismatch"

    # Enrollment status
    allowed_enrollment = scholarship.get(
        "enrollment_status_required", []
    )
    if (
        allowed_enrollment
        and user_enrollment not in allowed_enrollment
    ):
        return False, (
            f"Enrollment status '{user_enrollment}' not eligible"
        )

    # STEM requirement
    if scholarship.get("requires_stem") and user_track != "STEM":
        return False, "STEM program required"

    # Citizenship requirement
    if (
        scholarship.get("requires_filipino_citizen")
        and not user_citizen
    ):
        return False, "Filipino citizenship required"

    # Need-based income check
    if (
        scholarship.get("need_based")
        and scholarship.get("income_threshold")
    ):
        if (
            user_income
            and user_income > scholarship["income_threshold"]
        ):
            return False, (
                f"Income exceeds threshold "
                f"(₱{scholarship['income_threshold']:,}/month)"
            )

    # Double grant prohibition
    if scholarship.get("prohibits_double_grant") and user_has_grant:
        return False, "Prohibits double grants"

    # School type requirement
    req_school_type = scholarship.get("school_type_required")
    if (
        req_school_type
        and user_school_type != req_school_type.lower()
    ):
        return False, f"Requires {req_school_type} school"

    # Region restriction
    allowed_regions = scholarship.get("regions_allowed", ["all"])
    if "all" not in allowed_regions:
        if not user_region or user_region not in allowed_regions:
            return False, (
                f"Only available in: {', '.join(allowed_regions)}"
            )

    # GPA hard check
    if user_gpa and scholarship.get("gpa_required", 0) > 0:
        if user_gpa < scholarship["gpa_required"]:
            return False, (
                f"GPA {user_gpa} below minimum "
                f"{scholarship['gpa_required']}"
            )

    return True, ""


# ── Tavily queries ─────────────────────────────────────────────────────────────
def _build_tavily_queries(profile: dict) -> list[str]:
    major = profile.get("major") or "Information Technology"
    level = profile.get("level_seeking") or "undergraduate"
    track = profile.get("program_track") or ""
    region = profile.get("region") or "Philippines"
    city = profile.get("city") or ""
    school = profile.get("school") or ""
    income = profile.get("income_bracket") or ""
    location = city if city else region

    query_a = (
        f"official scholarship application 2026 requirements "
        f"{major} {track} {level} student Philippines "
        f"deadline eligibility"
    )

    query_b = (
        f"scholarship grant {level} {major} student "
        f"{location} 2026 Philippines"
    )
    if income and "Below" in income:
        query_b += " financial assistance need-based"
    if track == "STEM":
        query_b += " STEM science technology"
    if school:
        query_b += f" {school}"

    return [query_a, query_b]


def _parse_tavily_results(results: list, profile: dict) -> list:
    """
    Parses and scores Tavily results.
    Applies URL quality filter and level hard filter autonomously.
    """
    scholarships = []
    user_level = (
        profile.get("level_seeking") or "undergraduate"
    ).lower()
    user_major = (profile.get("major") or "").lower()
    user_skills = profile.get("skills") or ""
    if isinstance(user_skills, list):
        user_skills = " ".join(user_skills).lower()
    else:
        user_skills = user_skills.lower()
    user_leadership = profile.get("leadership_roles") or []
    seen_urls = set()

    # Level-specific keywords for hard filtering live results
    # If user is undergraduate, reject results that are
    # clearly graduate-only and vice versa
    level_reject_keywords = {
        "undergraduate": [
            "master's degree", "masters degree", "phd scholarship",
            "doctoral", "postgraduate", "post-graduate",
            "graduate school scholarship", "ms scholarship",
            "mba scholarship",
        ],
        "graduate": [
            "high school scholarship", "senior high scholarship",
            "grade 12 scholarship", "incoming college freshman",
        ],
    }
    reject_keywords = level_reject_keywords.get(user_level, [])

    for r in results:
        title = r.get("title", "Unknown")
        url = r.get("url", "")
        content = r.get("content", "")
        combined = (title + " " + content).lower()

        # Deduplicate
        if url in seen_urls:
            continue
        seen_urls.add(url)

        # Layer 3 — URL quality filter
        if not _is_quality_url(url, title):
            continue

        # Must be scholarship-related
        if not any(
            kw in combined
            for kw in [
                "scholarship", "grant", "fellowship",
                "stipend", "award", "subsidy",
            ]
        ):
            continue

        # Fix 2 — Hard level filter for live results
        # Reject results that clearly target the wrong level
        if any(kw in combined for kw in reject_keywords):
            continue

        score = 1
        reasons = []

        if user_level in combined:
            score += 2
            reasons.append(f"{user_level.capitalize()} level match")

        if user_major and any(
            word in combined
            for word in user_major.lower().split()
        ):
            score += 2
            reasons.append(f"Major relevance: {profile.get('major')}")

        tech_keywords = [
            "it", "technology", "computer",
            "engineering", "stem", "programming",
        ]
        if any(kw in combined for kw in tech_keywords):
            score += 1
            reasons.append("Tech field relevance")

        ph_keywords = [
            "philippines", "filipino", "dost", "ched", "deped",
        ]
        if any(kw in combined for kw in ph_keywords):
            score += 1
            reasons.append("Philippines-specific")

        if "international" in combined or "abroad" in combined:
            score += 1
            reasons.append("International opportunity")

        if user_skills and any(
            sk in combined for sk in user_skills.split()
            if len(sk) > 3
        ):
            score += 1
            reasons.append("Skills align with scholarship focus")

        if user_leadership and any(
            kw in combined
            for kw in [
                "leadership", "community", "service", "volunteer",
            ]
        ):
            score += 1
            reasons.append("Leadership experience valued")

        if not reasons:
            reasons.append("General scholarship match")

        scholarships.append({
            "id": url,
            "name": title,
            "provider": _extract_domain(url),
            "type": "live",
            "level": [user_level],
            "majors": [profile.get("major") or "All"],
            "gpa_required": 0,
            "deadline": "Check official website",
            "benefits": (
                content[:150] + "..."
                if len(content) > 150
                else content
            ),
            "core_values": "See official website for full details",
            "essay_prompt": (
                "Visit the scholarship website for the specific "
                "essay prompt and requirements."
            ),
            "link": url,
            "match_score": score,
            "match_reasons": reasons,
            "source": "live",
            "requires_stem": False,
            "requires_filipino_citizen": False,
            "need_based": False,
            "income_threshold": None,
            "school_type_required": None,
            "enrollment_status_required": [],
            "regions_allowed": ["all"],
            "prohibits_double_grant": False,
        })

    return sorted(
        scholarships, key=lambda x: x["match_score"], reverse=True
    )


def _extract_domain(url: str) -> str:
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        return domain.replace("www.", "").capitalize()
    except Exception:
        return "Online source"


# ── OpenAI reasoning layer ─────────────────────────────────────────────────────
def _openai_rank_scholarships(
    profile: dict,
    candidates: list,
    client: OpenAI,
) -> list:
    """
    Sends filtered scholarship candidates + user profile to OpenAI.
    OpenAI ranks them with contextual reasoning.
    Returns ordered list with match score, reasons, adviser note.
    """
    if not candidates:
        return []

    # Build household context for LLM
    household_size = profile.get("household_size")
    occupations = profile.get("household_occupations") or []
    has_pwd = profile.get("has_pwd_in_household", False)
    sibling_scholarship = profile.get("sibling_has_scholarship", False)

    household_context = ""
    if household_size:
        household_context += f"Household size: {household_size} people\n"
    if occupations:
        for i, occ in enumerate(occupations, 1):
            household_context += f"Person {i} occupation: {occ}\n"
    if has_pwd:
        household_context += "Has PWD member in household: Yes\n"
    if sibling_scholarship:
        household_context += "Sibling with existing scholarship: Yes\n"

    profile_summary = f"""
Name: {profile.get('name') or 'Not provided'}
School: {profile.get('school') or 'Not provided'}
Major: {profile.get('major') or 'Not provided'}
Program Track: {profile.get('program_track') or 'Not provided'}
Year Level: {profile.get('year_level') or 'Not provided'}
GPA: {profile.get('gpa') or 'Not provided'}
Level Seeking: {profile.get('level_seeking') or 'undergraduate'}
Enrollment Status: {profile.get('enrollment_status') or 'Not provided'}
Filipino Citizen: {profile.get('is_filipino_citizen', True)}
Region: {profile.get('region') or 'Not provided'}
Income Bracket: {profile.get('income_bracket') or 'Not provided'}
Skills: {profile.get('skills') or 'Not provided'}
Leadership Roles: {', '.join(profile.get('leadership_roles') or []) or 'None'}
Extracurricular: {', '.join(profile.get('extracurricular_focus') or []) or 'None'}
Leadership Description: {profile.get('leadership') or 'Not provided'}
Goals: {profile.get('goals') or 'Not provided'}
Research Experience: {profile.get('research_experience') or 'N/A'}
Thesis Topic: {profile.get('thesis_topic') or 'N/A'}
Work Experience: {profile.get('work_experience') or 'N/A'}
{household_context}"""

    scholarships_summary = json.dumps([
        {
            "id": s["id"],
            "name": s["name"],
            "provider": s["provider"],
            "type": s["type"],
            "benefits": s["benefits"],
            "core_values": s["core_values"],
            "essay_prompt": s["essay_prompt"],
            "gpa_required": s["gpa_required"],
            "deadline": s["deadline"],
            "majors": s.get("majors", []),
        }
        for s in candidates
    ], indent=2)

    system_prompt = """You are an expert Philippine scholarship adviser
with deep knowledge of local and international grants.

You will receive a student profile and a list of scholarship candidates
that have already passed hard eligibility filters.

Your job is to rank these scholarships from best to worst fit for this
specific student and explain your reasoning. Consider household context
(PWD members, sibling scholarships, occupations) as indicators of
financial need and family support structure.

Return ONLY a valid JSON array in this exact format,
no markdown, no preamble:
[
  {
    "id": "scholarship id or url",
    "match_score": integer from 1 to 10,
    "match_reasons": ["reason 1", "reason 2", "reason 3"],
    "adviser_note": "1-2 sentence contextual insight about why this fits or what to watch out for"
  }
]

Consider: GPA buffer above minimum, leadership alignment with scholarship
values, skills relevance, financial need alignment, household context,
career goals alignment with scholarship mission, and overall profile
strength. Be honest — if a scholarship is borderline, say so."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": (
                        f"Student profile:\n{profile_summary}\n\n"
                        f"Scholarship candidates:\n"
                        f"{scholarships_summary}"
                    ),
                },
            ],
            temperature=0.2,
            max_tokens=1000,
        )

        raw = response.choices[0].message.content.strip()
        raw = raw.replace("```json", "").replace("```", "").strip()
        rankings = json.loads(raw)

        ranked_map = {r["id"]: r for r in rankings}
        enriched = []
        for s in candidates:
            ranking = ranked_map.get(s["id"])
            if ranking:
                enriched.append({
                    **s,
                    "match_score": ranking.get("match_score", 5),
                    "match_reasons": ranking.get(
                        "match_reasons",
                        s.get("match_reasons", []),
                    ),
                    "adviser_note": ranking.get("adviser_note", ""),
                    "ranked_by": "openai",
                })
            else:
                enriched.append({
                    **s,
                    "adviser_note": "",
                    "ranked_by": "fallback",
                })

        return sorted(
            enriched,
            key=lambda x: x["match_score"],
            reverse=True,
        )

    except Exception:
        return [
            {**s, "adviser_note": "", "ranked_by": "fallback"}
            for s in candidates
        ]


# ── Main matcher entry point ───────────────────────────────────────────────────
def match_scholarships(
    profile: dict,
    static_scholarships: list,
    client: OpenAI,
) -> tuple[list, str]:
    """
    Layer 1: Hard filter static scholarships.
    Layer 2: Tavily live search + URL quality filter + level filter.
    Layer 3: Merge static + live candidates.
    Layer 4: OpenAI ranks and reasons about final top 3.

    Returns:
        (top 3 ranked scholarships, source: 'live' | 'fallback')
    """
    # Static hard filtering
    static_candidates = []
    for s in static_scholarships:
        passes, _ = _passes_hard_filters(s, profile)
        if passes:
            static_candidates.append({
                **s,
                "match_score": 5,
                "match_reasons": ["Passed eligibility filters"],
                "source": "fallback",
            })

    # Tavily live search
    tavily_key = os.environ.get("TAVILY_API_KEY", "")
    live_candidates = []
    source = "fallback"

    if tavily_key:
        try:
            tavily_client = TavilyClient(api_key=tavily_key)
            queries = _build_tavily_queries(profile)
            raw_results = []

            for query in queries:
                response = tavily_client.search(
                    query=query,
                    search_depth="advanced",
                    max_results=6,
                    include_answer=False,
                )
                raw_results.extend(response.get("results", []))

            live_candidates = _parse_tavily_results(
                raw_results, profile
            )
            if live_candidates:
                source = "live"

        except Exception:
            pass

    # Merge candidates
    static_names = {s["name"].lower() for s in static_candidates}
    unique_live = [
        r for r in live_candidates
        if r["name"].lower() not in static_names
    ]
    all_candidates = static_candidates + unique_live

    if not all_candidates:
        return [], source

    # Pass top 8 to OpenAI for reasoning
    top_candidates = sorted(
        all_candidates,
        key=lambda x: x["match_score"],
        reverse=True,
    )[:8]

    ranked = _openai_rank_scholarships(
        profile, top_candidates, client
    )

    return ranked[:3], source