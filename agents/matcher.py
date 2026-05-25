def match_scholarships(profile: dict, scholarships: list) -> list:
    """
    Rule-based matcher against the static JSON database.
    Runs entirely in memory — no external API calls.
    Returns scholarships sorted by match score descending.
    """
    results = []
    user_major = (profile.get("major") or "").lower()
    user_gpa = profile.get("gpa") or 0
    user_level = (profile.get("level_seeking") or "undergraduate").lower()
    user_skills = [s.lower() for s in (profile.get("skills") or [])]
    user_leadership = profile.get("leadership") or []

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
        elif any(user_major in m or m in user_major for m in majors_lower):
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
        tech_keywords = ["react", "node", "python", "javascript", "sql", "java", "it", "programming"]
        if any(kw in " ".join(user_skills) for kw in tech_keywords):
            if any("technology" in m.lower() or "computer" in m.lower() or "it" in m.lower()
                   for m in s["majors"]):
                score += 1
                reasons.append("Tech skills align")

        # Leadership boost
        if user_leadership and s["id"] in ["sm-foundation-it", "apc-leadership", "chevening"]:
            score += 1
            reasons.append("Leadership experience valued")

        # International boost for grad students
        if s["type"] == "international" and user_level == "graduate":
            score += 1
            reasons.append("International opportunity for grad students")

        if score > 0:
            results.append({**s, "match_score": score, "match_reasons": reasons})

    return sorted(results, key=lambda x: x["match_score"], reverse=True)