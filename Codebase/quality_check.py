"""Rule-based quality gate for extracted profiles and generated CVs.

Pure Python, no LLM - a sanity check before a CV is written to disk.
"""

_PLACEHOLDER_MARKERS = ("todo", "n/a", "achievement 1", "achievement 2", "[", "lorem ipsum")


def check_extraction(profile_data):
    """Return a list of problems with the extracted profile (empty = OK)"""
    issues = []
    if not profile_data.get("name"):
        issues.append("missing name")
    if not profile_data.get("email") and not profile_data.get("phone"):
        issues.append("missing both email and phone")
    if not profile_data.get("experience"):
        issues.append("no work experience extracted")
    if not profile_data.get("skills"):
        issues.append("no skills extracted")
    return issues


def check_generated_cv(generated_cv, profile_data):
    """Return a list of problems with the generated CV (empty = OK)"""
    issues = []

    summary = (generated_cv.get("summary") or "").strip()
    if not summary:
        issues.append("empty summary")
    elif any(marker in summary.lower() for marker in _PLACEHOLDER_MARKERS):
        issues.append("summary contains placeholder text")

    experience = generated_cv.get("experience") or []
    if not experience:
        issues.append("no experience entries generated")
    else:
        known_companies = {
            (job.get("company") or "").strip().lower()
            for job in profile_data.get("experience", []) or []
        }
        for job in experience:
            if not job.get("bullets"):
                issues.append(f"no bullets for {job.get('position', 'a role')}")
            company = (job.get("company") or "").strip().lower()
            if company and known_companies and company not in known_companies:
                issues.append(f"unrecognised company introduced: {job.get('company')}")

    if not generated_cv.get("ordered_skills"):
        issues.append("no skills in generated CV")

    return issues
