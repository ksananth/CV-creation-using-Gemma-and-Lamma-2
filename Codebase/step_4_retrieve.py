"""
================================================================================
STAGE 4: RETRIEVE EVIDENCE
================================================================================

Classes:
- RetrieveEvidence: For every matched skill, find the resume text that proves
  it (pure Python, no LLM, no vector index - the resume is a few paragraphs,
  not a corpus, so a regex scan over sentences is enough).

This is the "RAG" half of stage 4: retrieval only. Stage 5 is the generation
half - it consumes this evidence instead of reading the raw resume, so it can
never write a bullet point for a skill that has no supporting sentence.

Imported by main.py

IMPORT:
from step_4_retrieve import RetrieveEvidence

================================================================================
"""

import re


def _split_sentences(text):
    """Break resume prose into short, evidence-sized chunks."""
    if not text:
        return []
    # Split on newlines, bullet markers, and sentence-ending punctuation.
    parts = re.split(r"[\n\r]+|(?<=[.!?])\s+", str(text))
    chunks = []
    for part in parts:
        chunk = part.strip(" -•*\t")
        if chunk:
            chunks.append(chunk)
    return chunks


class RetrieveEvidence:
    """Find the resume sentence(s) that back up each matched skill"""

    def __init__(self):
        """Initialize"""
        print("[*] Initializing evidence retriever (no LLM)...")
        print("[✓] Retriever ready")

    def run(self, resume_data, match_data):
        """Retrieve evidence and return JSON"""
        print("\n" + "=" * 70)
        print("STAGE 4: RETRIEVE EVIDENCE (Python)")
        print("=" * 70)

        chunks = []
        chunks.extend(_split_sentences(resume_data.get("summary", "")))
        for job in resume_data.get("experience", []) or []:
            chunks.extend(_split_sentences(job.get("description", "")))
        skills_line = ", ".join(resume_data.get("skills", []) or [])

        evidence = {}
        matched_skills = (
            match_data["required"]["matched"] + match_data["preferred"]["matched"]
        )
        sources = {
            **match_data["required"]["sources"],
            **match_data["preferred"]["sources"],
        }

        for skill in matched_skills:
            pattern = rf"\b{re.escape(skill)}\b"
            snippets = [c for c in chunks if re.search(pattern, c.lower())]

            source = sources.get(skill, "skills_list")
            if not snippets:
                # Only evidence is the skills list itself - say so plainly
                # rather than pretending there's a detailed example.
                snippets = [f"Listed in skills: {skills_line}"]

            evidence[skill] = {
                "snippets": snippets,
                "source": source,
            }

        print(f"[✓] Retrieved evidence for {len(evidence)} matched skills")
        thin = [s for s, e in evidence.items() if e["source"] == "skills_list"]
        if thin:
            print(f"[*] Skills-list-only (no experience detail): {', '.join(thin)}")

        return {
            "evidence": evidence,
            "fabrication_blocklist": match_data["fabrication_blocklist"],
        }
