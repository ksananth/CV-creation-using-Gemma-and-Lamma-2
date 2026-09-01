"""Rewrite a candidate's experience into job-tailored CV content using Gemma 3.

The model only ever sees the job details, the evidence retrieved for skills
the candidate can prove, and the fabrication blocklist - never the raw
resume - so it can rephrase real experience but cannot invent an
achievement with no evidence, or claim a blocked skill.

Output shares generate_profile_cv.py's schema (summary/experience/
ordered_skills) so both feed the same document renderer.
"""

import json

from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate

from json_utils import invoke_json, merge_unique

REFINE_PROMPT = PromptTemplate(
    input_variables=["current_cv", "evidence_lines", "blocklist", "feedback"],
    template="""You are revising a CV based on user feedback.

CURRENT CV:
{current_cv}

EVIDENCE FROM THE CANDIDATE'S ACTUAL RESUME (the only facts you may use):
{evidence_lines}

STRICT RULES:
- Use ONLY the evidence above. Do not invent achievements, numbers, or tools.
- NEVER mention or imply these skills, the candidate cannot prove them: {blocklist}
- Apply the user's feedback below; leave anything the feedback doesn't mention unchanged.

USER FEEDBACK: {feedback}

Return ONLY valid JSON in the same shape as CURRENT CV (no markdown, no explanations):
{{
    "summary": "...",
    "experience": [
        {{"position": "...", "company": "...", "duration": "...", "bullets": ["...", "..."]}}
    ],
    "ordered_skills": ["skill1", "skill2"]
}}""",
)

PROMPT = PromptTemplate(
    input_variables=[
        "job_title", "company", "responsibilities",
        "evidence_lines", "blocklist", "work_history",
    ],
    template="""You are tailoring a real candidate's CV for a specific job.

JOB: {job_title} at {company}
RESPONSIBILITIES: {responsibilities}

EVIDENCE FROM THE CANDIDATE'S ACTUAL RESUME (the only facts you may use):
{evidence_lines}

CANDIDATE'S FULL WORK HISTORY (produce one tailored experience entry for
EVERY role listed here, in the same order - do not drop any role):
{work_history}

STRICT RULES:
- Use ONLY the evidence above. Do not invent achievements, numbers, or tools.
- NEVER mention or imply these skills, the candidate cannot prove them: {blocklist}
- Rephrase evidence into achievement-style bullet points matching the job's language.
- If evidence for a skill is only "Listed in skills", write a short, general bullet - do not invent a specific project for it.
- Return exactly one experience entry per role in CANDIDATE'S FULL WORK HISTORY, same order, same company/duration.

Return ONLY valid JSON (no markdown, no explanations):
{{
    "summary": "2-3 sentence professional summary tailored to this job, using only the evidence given",
    "experience": [
        {{"position": "...", "company": "...", "duration": "...", "bullets": ["Achievement bullet 1", "Achievement bullet 2"]}}
    ],
    "ordered_skills": ["skill1", "skill2"]
}}""",
)


def _strip_blocklisted(data, blocklist):
    """Hard safety net: strip any blocklisted skill the model slipped in
    anyway, rather than trusting it to have followed the prompt."""
    blocked = {b.lower() for b in blocklist}
    for job in data.get("experience", []):
        job["bullets"] = [b for b in job.get("bullets", []) if not any(bl in b.lower() for bl in blocked)]
    data["ordered_skills"] = [s for s in data.get("ordered_skills", []) if s.lower() not in blocked]
    return data


class GenerateCV:
    """Generate job-tailored CV content using Gemma 3"""

    def __init__(self):
        self.chain = PROMPT | OllamaLLM(model="gemma3:1b", temperature=0.4)
        self.refine_chain = REFINE_PROMPT | OllamaLLM(model="gemma3:1b", temperature=0.4)

    def run(self, resume_data, job_data, match_data, evidence_data):
        evidence = evidence_data["evidence"]
        blocklist = evidence_data["fabrication_blocklist"]
        original_jobs = resume_data.get("experience", []) or []

        inputs = {
            "job_title": job_data.get("title", ""),
            "company": job_data.get("company", ""),
            "responsibilities": "; ".join(job_data.get("responsibilities", [])),
            "evidence_lines": "\n".join(
                f"- {skill}: {'; '.join(info['snippets'])}"
                for skill, info in evidence.items()
            ) or "(none)",
            "blocklist": ", ".join(blocklist) or "(none)",
            "work_history": "\n".join(
                f"- {job.get('position', '')} at {job.get('company', '')} "
                f"({job.get('duration', '')}): {job.get('description', '')}"
                for job in original_jobs
            ) or "(none provided)",
        }

        data = invoke_json(self.chain, inputs)
        if data is None:
            return None

        # The model already knows each role's real company/duration from
        # WORK HISTORY context, but pin them from resume_data by position
        # anyway rather than trust free-form output.
        for i, job in enumerate(data.get("experience", [])):
            if i < len(original_jobs):
                job["company"] = original_jobs[i].get("company", "")
                job["duration"] = original_jobs[i].get("duration", "")

        data = _strip_blocklisted(data, blocklist)
        data["ordered_skills"] = merge_unique(data["ordered_skills"], resume_data.get("skills", []), exclude=blocklist)
        return data

    def refine(self, current_cv, feedback, evidence_data):
        """Revise an already-generated CV per free-text user feedback,
        constrained to the same evidence/blocklist as the original generation."""
        evidence = evidence_data["evidence"]
        blocklist = evidence_data["fabrication_blocklist"]

        inputs = {
            "current_cv": json.dumps(current_cv, indent=2),
            "evidence_lines": "\n".join(
                f"- {skill}: {'; '.join(info['snippets'])}"
                for skill, info in evidence.items()
            ) or "(none)",
            "blocklist": ", ".join(blocklist) or "(none)",
            "feedback": feedback,
        }

        data = invoke_json(self.refine_chain, inputs)
        if data is None:
            return None
        return _strip_blocklisted(data, blocklist)
