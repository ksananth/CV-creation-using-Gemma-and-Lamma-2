"""Rewrite a candidate's experience into job-tailored CV content using Gemma.

The model only ever sees the job details, the evidence retrieved for skills
the candidate can prove, and the fabrication blocklist - never the raw
resume - so it can rephrase real experience but cannot invent an
achievement with no evidence, or claim a blocked skill.
"""

from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate

from json_utils import extract_json

PROMPT = PromptTemplate(
    input_variables=[
        "job_title", "company", "responsibilities",
        "evidence_lines", "blocklist", "position", "duration",
    ],
    template="""You are tailoring a real candidate's CV for a specific job.

JOB: {job_title} at {company}
RESPONSIBILITIES: {responsibilities}

EVIDENCE FROM THE CANDIDATE'S ACTUAL RESUME (the only facts you may use):
{evidence_lines}

CURRENT ROLE: {position} ({duration})

STRICT RULES:
- Use ONLY the evidence above. Do not invent achievements, numbers, or tools.
- NEVER mention or imply these skills, the candidate cannot prove them: {blocklist}
- Rephrase evidence into achievement-style bullet points matching the job's language.
- If evidence for a skill is only "Listed in skills", write a short, general bullet - do not invent a specific project for it.

Return ONLY valid JSON (no markdown, no explanations):
{{
    "summary": "2-3 sentence professional summary tailored to this job, using only the evidence given",
    "bullets": ["Achievement bullet 1", "Achievement bullet 2"],
    "ordered_skills": ["skill1", "skill2"]
}}""",
)

MAX_ATTEMPTS = 3


class GenerateCV:
    """Generate job-tailored CV content using Gemma"""

    def __init__(self):
        self.llm = OllamaLLM(model="gemma:7b", temperature=0.4)

    def run(self, resume_data, job_data, match_data, evidence_data):
        evidence = evidence_data["evidence"]
        blocklist = evidence_data["fabrication_blocklist"]
        current_job = (resume_data.get("experience") or [{}])[0]

        inputs = {
            "job_title": job_data.get("title", ""),
            "company": job_data.get("company", ""),
            "responsibilities": "; ".join(job_data.get("responsibilities", [])),
            "evidence_lines": "\n".join(
                f"- {skill}: {'; '.join(info['snippets'])}"
                for skill, info in evidence.items()
            ) or "(none)",
            "blocklist": ", ".join(blocklist) or "(none)",
            "position": current_job.get("position", ""),
            "duration": current_job.get("duration", ""),
        }

        chain = PROMPT | self.llm
        data = None
        for _ in range(MAX_ATTEMPTS):
            data = extract_json(chain.invoke(inputs))
            if data is not None:
                break
        if data is None:
            return None

        # Hard safety net: strip any blocklisted skill the model slipped in
        # anyway, rather than trusting it to have followed the prompt.
        blocked = {b.lower() for b in blocklist}
        data["bullets"] = [
            b for b in data.get("bullets", []) if not any(bl in b.lower() for bl in blocked)
        ]
        data["ordered_skills"] = [
            s for s in data.get("ordered_skills", []) if s.lower() not in blocked
        ]
        return data
