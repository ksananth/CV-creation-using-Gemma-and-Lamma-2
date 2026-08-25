"""
================================================================================
STAGE 3: MATCH SKILLS
================================================================================

Classes:
- MatchSkills: Compare resume skills against job requirements (pure Python)

No LLM is used here. Set intersection is deterministic and reproducible; the
only fuzzy part is the alias table below, which is easier to explain and audit
than a model's opinion.

The real work is NORMALISATION, not comparison. Stage 2 returns requirement
phrases, not atomic skills - e.g. "Android, kotlin, Python, Java, or similar"
is four skills in one string, and "AWS knowledge" is one skill plus a filler
word. Comparing those raw against the resume would report a 33% match for a
candidate who actually has every required skill.

Imported by main.py

IMPORT:
from step_3_match import MatchSkills

================================================================================
"""

import re


# ============================================================================
# NORMALISATION TABLES
# ============================================================================

# Canonical forms for common spelling variants.
ALIASES = {
    "react.js": "react", "reactjs": "react", "react js": "react",
    "node.js": "node", "nodejs": "node", "node js": "node",
    "vue.js": "vue", "vuejs": "vue",
    "js": "javascript", "ts": "typescript",
    "k8s": "kubernetes",
    "ml": "machine learning", "dl": "deep learning",
    "ai": "artificial intelligence",
    "gcp": "google cloud", "aws": "aws", "amazon web services": "aws",
    "postgres": "postgresql", "psql": "postgresql",
    "restful": "rest", "rest api": "rest", "rest apis": "rest",
    "golang": "go",
    "c sharp": "c#", "csharp": "c#",
    "net": ".net", "dotnet": ".net",
    "html5": "html", "css3": "css",
    "tf": "tensorflow",
    "gh actions": "github actions",
}

# Multi-word skills that must NOT be split on "and" / "or" / "/".
PROTECTED = {
    "ci/cd",
    "a/b testing",
    "research and development",
    "extract transform and load",
}

# Words that carry no skill meaning; dropped from each atom.
FILLER = {
    "knowledge", "experience", "experienced", "proficiency", "proficient",
    "familiarity", "familiar", "expertise", "understanding", "ability",
    "skills", "skill", "with", "in", "of", "the", "a", "an", "and", "or",
    "years", "year", "yrs", "strong", "solid", "good", "excellent", "great",
    "similar", "plus", "advanced", "basic", "working", "hands", "on",
    "deep", "demonstrated", "proven", "using", "use", "must", "have",
    "required", "preferred", "nice", "to", "etc", "is", "are", "such", "as",
}

# Split on commas, semicolons, pipes, slashes, and the words "or" / "and".
_SPLIT_RE = re.compile(r"\s*(?:,|;|\||/|\bor\b|\band\b)\s*")


def normalise(phrase):
    """Turn one raw requirement phrase into a list of canonical skills."""
    if not phrase:
        return []

    s = re.sub(r"[()\[\]]", " ", str(phrase).lower())
    s = re.sub(r"\s+", " ", s).strip(" .,:;-")

    # Whole-phrase hits win, so protected skills survive the splitter.
    if s in PROTECTED:
        return [s]
    if s in ALIASES:
        return [ALIASES[s]]

    skills = []
    for atom in _SPLIT_RE.split(s):
        atom = atom.strip(" .,:;-•*")
        if not atom:
            continue
        if atom in ALIASES:
            skills.append(ALIASES[atom])
            continue

        tokens = [t.strip(" .,:;-•*+") for t in atom.split()]
        tokens = [
            t for t in tokens
            if t and t not in FILLER and not re.fullmatch(r"[\d.+]+", t)
        ]
        if not tokens:
            continue

        candidate = " ".join(tokens)
        skills.append(ALIASES.get(candidate, candidate))

    return skills


def normalise_all(phrases):
    """Normalise a list of phrases into a de-duplicated, ordered skill list."""
    seen = []
    for phrase in phrases or []:
        for skill in normalise(phrase):
            if skill not in seen:
                seen.append(skill)
    return seen


# ============================================================================
# STAGE 3: MATCH SKILLS
# ============================================================================

class MatchSkills:
    """Compare resume skills against job requirements"""

    def __init__(self):
        """Initialize"""
        print("[*] Initializing skill matcher (no LLM)...")
        print(f"[✓] Matcher ready ({len(ALIASES)} aliases, {len(FILLER)} filler words)")

    def run(self, resume_data, job_data):
        """Match skills and return JSON"""
        print("\n" + "="*70)
        print("STAGE 3: MATCH SKILLS (Python)")
        print("="*70)

        resume_skills = normalise_all(resume_data.get("skills", []))
        required = normalise_all(job_data.get("required_skills", []))
        preferred = normalise_all(job_data.get("preferred_skills", []))

        print(f"[*] Normalised resume:    {len(resume_data.get('skills', []))} phrases -> {len(resume_skills)} skills")
        print(f"[*] Normalised required:  {len(job_data.get('required_skills', []))} phrases -> {len(required)} skills")
        print(f"[*] Normalised preferred: {len(job_data.get('preferred_skills', []))} phrases -> {len(preferred)} skills")

        # A skill can be evidenced in the experience text without appearing in
        # the skills list, so fall back to a scan of the resume prose.
        resume_text = self._resume_text(resume_data)
        resume_set = set(resume_skills)

        def find(skill):
            if skill in resume_set:
                return "skills_list"
            if re.search(rf"\b{re.escape(skill)}\b", resume_text):
                return "experience_text"
            return None

        report = {}
        for label, wanted in (("required", required), ("preferred", preferred)):
            matched, missing, sources = [], [], {}
            for skill in wanted:
                source = find(skill)
                if source:
                    matched.append(skill)
                    sources[skill] = source
                else:
                    missing.append(skill)
            report[label] = {
                "matched": matched,
                "missing": missing,
                "sources": sources,
            }
            pct = round(100.0 * len(matched) / len(wanted), 1) if wanted else 0.0
            report[label]["coverage_pct"] = pct
            print(f"[✓] {label.capitalize():9} {len(matched)}/{len(wanted)} matched ({pct}%)")

        # Skills the candidate has that this job never asked for - first
        # candidates to cut when the CV has to fit two pages.
        asked = set(required) | set(preferred)
        report["extra"] = [s for s in resume_skills if s not in asked]

        # Exactly the skills the generator would be tempted to invent, because
        # the job asks for them and the resume cannot back them up. Stage 5
        # uses this as a blocklist.
        report["fabrication_blocklist"] = (
            report["required"]["missing"] + report["preferred"]["missing"]
        )

        report["normalized"] = {
            "resume_skills": resume_skills,
            "required_skills": required,
            "preferred_skills": preferred,
        }

        if report["extra"]:
            print(f"[*] Extra (not asked for): {', '.join(report['extra'])}")
        if report["fabrication_blocklist"]:
            print(f"[!] Do NOT invent: {', '.join(report['fabrication_blocklist'])}")

        return report

    @staticmethod
    def _resume_text(resume_data):
        """Flatten resume prose to lowercase text for fallback skill lookup"""
        parts = [str(resume_data.get("summary", ""))]
        for job in resume_data.get("experience", []) or []:
            parts.append(str(job.get("position", "")))
            parts.append(str(job.get("description", "")))
        return re.sub(r"\s+", " ", " ".join(parts).lower())
