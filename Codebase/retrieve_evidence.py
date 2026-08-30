"""Find the resume sentence(s) that back up each matched skill (pure Python).

No vector index - the resume is a few paragraphs, not a corpus, so a regex
scan over sentences is enough. This is what feeds the CV generator instead
of the raw resume, so it can never write a bullet point for a skill that
has no supporting sentence.
"""

import re


def _split_sentences(text):
    if not text:
        return []
    parts = re.split(r"[\n\r]+|(?<=[.!?])\s+", str(text))
    return [c for c in (p.strip(" -•*\t") for p in parts) if c]


class RetrieveEvidence:
    """Find the resume sentence(s) that back up each matched skill"""

    def run(self, resume_data, match_data):
        chunks = _split_sentences(resume_data.get("summary", ""))
        for job in resume_data.get("experience", []) or []:
            chunks.extend(_split_sentences(job.get("description", "")))
        skills_line = ", ".join(resume_data.get("skills", []) or [])

        matched_skills = (
            match_data["required"]["matched"] + match_data["preferred"]["matched"]
        )
        sources = {
            **match_data["required"]["sources"],
            **match_data["preferred"]["sources"],
        }

        evidence = {}
        for skill in matched_skills:
            pattern = rf"\b{re.escape(skill)}\b"
            snippets = [c for c in chunks if re.search(pattern, c.lower())]
            if not snippets:
                # Only evidence is the skills list itself - say so plainly
                # rather than pretending there's a detailed example.
                snippets = [f"Listed in skills: {skills_line}"]
            evidence[skill] = {
                "snippets": snippets,
                "source": sources.get(skill, "skills_list"),
            }

        return {
            "evidence": evidence,
            "fabrication_blocklist": match_data["fabrication_blocklist"],
        }
