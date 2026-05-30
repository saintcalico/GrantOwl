import os
import json
from tavily import TavilyClient


def _build_search_query(profile: dict) -> str:
    """
    Builds a targeted Tavily search query from the structured profile.
    """
    major = profile.get("major") or "Information Technology"
    level = profile.get("level_seeking") or "undergraduate"
    skills = ", ".join(profile.get("skills") or [])
    query = (
        f"active scholarships grants for {level} {major} "
        f"students Philippines 2026"
    )
    if skills:
        query += f" {skills}"
    if level == "graduate":
        query += " international graduate scholarship"
    return query


def _parse_tavily_results(results: list, profile: dict) -> list:
    """
    Parses raw Tavily search results into a normalized scholarship list
    with match scoring. Filters out clearly irrelevant results.
    """
    scholarships = []
    user_level = (profile.get("level_seeking") or "undergraduate").lower()
    user_major = (profile.get("major") or "").lower()
    user_gpa = profile.get("gpa") or 0
    user_skills = [s.lower() for s in (profile.get("skills") or [])]
    user_leadership = profile.get("leadership") or ""

    for r in results:
        title = r.get("title", "Unknown Scholarship")
        url = r.get("url", "")
        content = r.get("content", "")
        combined = (title + " " + content).lower()

        # Skip results that are not scholarship-related
        if not any(
            kw in combined
            for kw in ["scholarship", "grant", "fellowship", "stipend", "award"]
        ):
            continue

        score = 1
        reasons = []

        # Level match
        if user_level in combined:
            score += 2
            reasons.append(f"{user_level.capitalize()} level match")

        # Major match
        if user_major and any(
            word in combined for word in user_major.lower().split()
        ):
            score += 2
            reasons.append(f"Major relevance: {profile.get('major')}")

        # Tech field relevance
        tech_keywords = [
            "it", "technology", "computer", "engineering",
            "stem", "programming"
        ]
        if any(kw in combined for kw in tech_keywords):
            score += 1
            reasons.append("Tech field relevance")

        # Philippines-specific
        ph_keywords = [
            "philippines", "filipino", "dost", "ched", "deped", "tesda"
        ]
        if any(kw in combined for kw in ph_keywords):
            score += 1
            reasons.append("Philippines-specific")

        # International opportunity
        if "international" in combined or "abroad" in combined:
            score += 1
            reasons.append("International opportunity")

        # Skills match
        if user_skills and any(sk in combined for sk in user_skills):
            score += 1
            reasons.append("Skills align with scholarship focus")

        # Leadership signals
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
                content[:120] + "..."
                if len(content) > 120
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
        })

    return sorted(
        scholarships, key=lambda x: x["match_score"], reverse=True
    )


def _extract_domain(url: str) -> str:
    """Extracts a readable domain name from a URL."""
    try:
        from urllib.parse import urlparse
        domain = urlparse(url).netloc
        return domain.replace("www.", "").capitalize()
    except Exception:
        return "Online source"


def _match_static(profile: dict, scholarships: list) -> list:
    """
    Rule-based matcher against the static JSON fallback database.
    Runs entirely in memory — no external API calls.
    """
    results = []
    user_major = (profile.get("major") or "").lower()
    user_gpa = profile.get("gpa") or 0
    user_level = (profile.get("level_seeking") or "undergraduate").lower()
    user_skills = [s.lower() for s in (profile.get("skills") or [])]
    user_leadership = profile.get("leadership") or ""

    for s in scholarships:
        score = 0
        reasons = []

        # Level match (hard filter)
        if user_level not in s["level"] and "All" not in s["level"]:
            continue

        # Major match
        majors_lower = [m.lower() for m in s["majors"]]
        if "all" in majors_lower:
            score += 2
            reasons.append("Open to all majors")
        elif any(
            user_major in m or m in user_major for m in majors_lower
        ):
            score += 3
            reasons.append(f"Major match: {s['majors']}")

        # GPA match
        if user_gpa >= s["gpa_required"]:
            score += 2
            reasons.append(f"GPA qualifies (≥{s['gpa_required']})")
        elif s["gpa_required"] == 0:
            score += 1
            reasons.append("No GPA requirement")

        # Tech skills boost
        tech_keywords = [
            "react", "node", "python", "javascript",
            "sql", "java", "it", "programming"
        ]
        if any(kw in " ".join(user_skills) for kw in tech_keywords):
            if any(
                "technology" in m.lower()
                or "computer" in m.lower()
                or "it" in m.lower()
                for m in s["majors"]
            ):
                score += 1
                reasons.append("Tech skills align")

        # Leadership boost
        if user_leadership and s["id"] in [
            "sm-foundation-it", "apc-leadership", "chevening"
        ]:
            score += 1
            reasons.append("Leadership experience valued")

        # International boost for grad students
        if s["type"] == "international" and user_level == "graduate":
            score += 1
            reasons.append("International opportunity for grad students")

        if score > 0:
            results.append({
                **s,
                "match_score": score,
                "match_reasons": reasons,
                "source": "fallback",
            })

    return sorted(
        results, key=lambda x: x["match_score"], reverse=True
    )


def match_scholarships(
    profile: dict, static_scholarships: list
) -> tuple[list, str]:
    """
    Primary: Tavily live search based on profile.
    Fallback: static JSON database if Tavily fails or returns nothing.

    Returns:
        (top 3 matched scholarships, source: 'live' | 'fallback')
    """
    tavily_key = os.environ.get("TAVILY_API_KEY", "")

    if tavily_key:
        try:
            client = TavilyClient(api_key=tavily_key)
            query = _build_search_query(profile)
            response = client.search(
                query=query,
                search_depth="advanced",
                max_results=8,
                include_answer=False,
            )
            results = response.get("results", [])
            if results:
                parsed = _parse_tavily_results(results, profile)
                if parsed:
                    return parsed[:3], "live"
        except Exception:
            pass  # Fall through to static fallback silently

    # Fallback to static JSON
    static_results = _match_static(profile, static_scholarships)
    return static_results[:3], "fallback"