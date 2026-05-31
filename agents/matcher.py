import os
from tavily import TavilyClient

# ── Layer 3 — URL quality filter patterns ─────────────────────────────────────
JUNK_PATTERNS = [
    "top-10", "top10", "best-scholarships", "scholarships.com",
    "findgrants", "find-grants", "scholarship-list", "listicle",
    "pinterest", "quora", "reddit", "facebook", "twitter",
    "youtube", "tiktok", "blogspot", "wordpress.com",
    "buzzfeed", "ranker", "listverse", "wikihow",
]


def _is_quality_url(url: str, title: str) -> bool:
    """
    Autonomously rejects aggregator/listicle URLs.
    Returns True if the URL passes quality check.
    """
    combined = (url + " " + title).lower()
    return not any(pattern in combined for pattern in JUNK_PATTERNS)


# ── Layer 1 — Hard filter rules ───────────────────────────────────────────────
def _passes_hard_filters(scholarship: dict, profile: dict) -> tuple[bool, str]:
    """
    Applies deterministic eligibility gates before any scoring.
    Returns (passes: bool, reason_if_failed: str).
    """
    user_level = (profile.get("level_seeking") or "undergraduate").lower()
    user_enrollment = profile.get("enrollment_status") or "enrolled"
    user_track = (profile.get("program_track") or "").upper()
    user_income = profile.get("income_ceiling")
    user_citizen = profile.get("is_filipino_citizen", True)
    user_has_grant = profile.get("has_existing_scholarship", False)
    user_school_type = (profile.get("school_type") or "").lower()
    user_region = (profile.get("region") or "").strip()
    user_gpa = profile.get("gpa") or 0

    # Level match
    if user_level not in scholarship.get("level", []):
        return False, "Level mismatch"

    # Enrollment status
    allowed_enrollment = scholarship.get("enrollment_status_required", [])
    if allowed_enrollment and user_enrollment not in allowed_enrollment:
        return False, f"Enrollment status '{user_enrollment}' not eligible"

    # STEM requirement
    if scholarship.get("requires_stem") and user_track != "STEM":
        return False, "STEM program required"

    # Citizenship requirement
    if scholarship.get("requires_filipino_citizen") and not user_citizen:
        return False, "Filipino citizenship required"

    # Need-based income check
    if scholarship.get("need_based") and scholarship.get("income_threshold"):
        if user_income and user_income > scholarship["income_threshold"]:
            return False, (
                f"Income exceeds threshold "
                f"(₱{scholarship['income_threshold']:,}/month)"
            )

    # Double grant prohibition
    if scholarship.get("prohibits_double_grant") and user_has_grant:
        return False, "Prohibits double grants"

    # School type requirement
    req_school_type = scholarship.get("school_type_required")
    if req_school_type and user_school_type != req_school_type.lower():
        return False, f"Requires {req_school_type} school"

    # Region restriction
    allowed_regions = scholarship.get("regions_allowed", ["all"])
    if "all" not in allowed_regions:
        if not user_region or user_region not in allowed_regions:
            return False, f"Only available in: {', '.join(allowed_regions)}"

    # Minimum GPA hard check (only filter if user entered GPA)
    if user_gpa and scholarship.get("gpa_required", 0) > 0:
        if user_gpa < scholarship["gpa_required"]:
            return False, (
                f"GPA {user_gpa} below minimum "
                f"{scholarship['gpa_required']}"
            )

    return True, ""


# ── Layer 2 — Scoring after hard filters ──────────────────────────────────────
def _score_static(scholarship: dict, profile: dict) -> tuple[int, list[str]]:
    """
    Soft scoring for scholarships that passed hard filters.
    Returns (score, reasons).
    """
    score = 0
    reasons = []

    user_major = (profile.get("major") or "").lower()
    user_gpa = profile.get("gpa") or 0
    user_skills = [s.lower() for s in (profile.get("skills") or [])]
    user_leadership = profile.get("leadership_roles") or []
    user_extracurricular = profile.get("extracurricular_focus") or []
    user_level = (profile.get("level_seeking") or "undergraduate").lower()

    # Major match
    majors_lower = [m.lower() for m in scholarship.get("majors", [])]
    if "all" in majors_lower:
        score += 2
        reasons.append("Open to all majors")
    elif any(user_major in m or m in user_major for m in majors_lower):
        score += 3
        reasons.append(f"Major match: {profile.get('major')}")

    # GPA buffer bonus (above minimum by margin)
    req_gpa = scholarship.get("gpa_required", 0)
    if user_gpa and req_gpa:
        if user_gpa >= req_gpa + 3:
            score += 2
            reasons.append(f"GPA well above minimum ({user_gpa} vs {req_gpa})")
        elif user_gpa >= req_gpa:
            score += 1
            reasons.append(f"GPA meets minimum ({user_gpa} vs {req_gpa})")
    elif req_gpa == 0:
        score += 1
        reasons.append("No GPA requirement")

    # Skills alignment
    tech_keywords = [
        "react", "node", "python", "javascript", "sql",
        "java", "it", "programming", "machine learning",
        "data", "cloud", "cybersecurity",
    ]
    if any(kw in " ".join(user_skills) for kw in tech_keywords):
        if any(
            "technology" in m.lower()
            or "computer" in m.lower()
            or "it" in m.lower()
            for m in scholarship.get("majors", [])
        ):
            score += 1
            reasons.append("Tech skills align with scholarship focus")

    # Leadership bonus
    leadership_scholarships = [
        "sm-foundation-it", "apc-leadership", "chevening"
    ]
    if user_leadership and scholarship["id"] in leadership_scholarships:
        score += 2
        reasons.append("Leadership experience is a key criterion")
    elif user_leadership:
        score += 1
        reasons.append("Leadership experience strengthens application")

    # Community service / extracurricular bonus
    if (
        "Community Service" in user_extracurricular
        and scholarship["id"] in ["sm-foundation-it", "apc-leadership"]
    ):
        score += 1
        reasons.append("Community service aligns with scholarship values")

    # International boost for grad
    if scholarship.get("type") == "international" and user_level == "graduate":
        score += 1
        reasons.append("International opportunity for graduate applicants")

    return score, reasons


# ── Build hyper-specific Tavily queries ───────────────────────────────────────
def _build_tavily_queries(profile: dict) -> list[str]:
    """
    Builds two targeted Tavily queries from the profile.
    Query A — known scholarship verification.
    Query B — profile-specific discovery.
    """
    major = profile.get("major") or "Information Technology"
    level = profile.get("level_seeking") or "undergraduate"
    track = profile.get("program_track") or ""
    region = profile.get("region") or "Philippines"
    city = profile.get("city") or ""
    school = profile.get("school") or ""
    income = profile.get("income_bracket") or ""

    location = city if city else region

    # Query A — verification of known scholarships
    query_a = (
        f"official scholarship application 2026 requirements "
        f"{major} {track} {level} student Philippines deadline eligibility"
    )

    # Query B — profile-specific discovery
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
    Applies URL quality filter autonomously.
    """
    scholarships = []
    user_level = (profile.get("level_seeking") or "undergraduate").lower()
    user_major = (profile.get("major") or "").lower()
    user_skills = [s.lower() for s in (profile.get("skills") or [])]
    user_leadership = profile.get("leadership_roles") or []

    seen_urls = set()

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
                "stipend", "award", "subsidy"
            ]
        ):
            continue

        score = 1
        reasons = []

        if user_level in combined:
            score += 2
            reasons.append(f"{user_level.capitalize()} level match")

        if user_major and any(
            word in combined for word in user_major.lower().split()
        ):
            score += 2
            reasons.append(f"Major relevance: {profile.get('major')}")

        tech_keywords = [
            "it", "technology", "computer",
            "engineering", "stem", "programming"
        ]
        if any(kw in combined for kw in tech_keywords):
            score += 1
            reasons.append("Tech field relevance")

        ph_keywords = [
            "philippines", "filipino", "dost", "ched", "deped"
        ]
        if any(kw in combined for kw in ph_keywords):
            score += 1
            reasons.append("Philippines-specific")

        if "international" in combined or "abroad" in combined:
            score += 1
            reasons.append("International opportunity")

        if user_skills and any(sk in combined for sk in user_skills):
            score += 1
            reasons.append("Skills align with scholarship focus")

        if user_leadership and any(
            kw in combined
            for kw in ["leadership", "community", "service", "volunteer"]
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
            # Provide neutral values for dashboard compatibility
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


# ── Main matcher entry point ───────────────────────────────────────────────────
def match_scholarships(
    profile: dict, static_scholarships: list
) -> tuple[list, str]:
    """
    Layer 1: Hard filter static scholarships.
    Layer 2: Score remaining static scholarships.
    Layer 3: Run Tavily queries and filter/score live results.
    Merge, deduplicate, return top 3.
    Falls back to static-only if Tavily unavailable.
    """
    # ── Static matching (always runs) ─────────────────────────────────────────
    static_results = []
    for s in static_scholarships:
        passes, reason = _passes_hard_filters(s, profile)
        if passes:
            score, reasons = _score_static(s, profile)
            if score > 0:
                static_results.append({
                    **s,
                    "match_score": score,
                    "match_reasons": reasons,
                    "source": "fallback",
                })

    static_results.sort(key=lambda x: x["match_score"], reverse=True)

    # ── Tavily live search (primary enrichment layer) ──────────────────────────
    tavily_key = os.environ.get("TAVILY_API_KEY", "")
    live_results = []

    if tavily_key:
        try:
            client = TavilyClient(api_key=tavily_key)
            queries = _build_tavily_queries(profile)
            raw_results = []

            for query in queries:
                response = client.search(
                    query=query,
                    search_depth="advanced",
                    max_results=6,
                    include_answer=False,
                )
                raw_results.extend(response.get("results", []))

            live_results = _parse_tavily_results(raw_results, profile)

        except Exception:
            pass  # Fall through silently to static only

    # ── Merge: static first (verified), then live discoveries ─────────────────
    if live_results:
        # Avoid showing duplicate scholarship names
        static_names = {s["name"].lower() for s in static_results}
        unique_live = [
            r for r in live_results
            if r["name"].lower() not in static_names
        ]
        merged = static_results + unique_live
        merged.sort(key=lambda x: x["match_score"], reverse=True)
        return merged[:3], "live"

    return static_results[:3], "fallback"