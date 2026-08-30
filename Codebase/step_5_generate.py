"""
================================================================================
STAGE 5: GENERATE TAILORED CV (RAG + "ResumeLM")
================================================================================

Classes:
- GenerateCV: Rewrite the candidate's real experience into job-tailored CV
  content using Gemma 3.1B, grounded strictly in the evidence retrieved in
  Stage 4.

The model is only ever shown:
  - the job title/company/responsibilities
  - the evidence snippets for skills the candidate can actually prove
  - the fabrication blocklist (skills to never claim)

It never sees the raw, unfiltered resume - so it can rephrase real experience
into job-matching language, but it cannot invent an achievement that has no
evidence, or claim a skill on the blocklist.

Imported by main.py

IMPORT:
from step_5_generate import GenerateCV

================================================================================
"""

import json
import re
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate


class GenerateCV:
    """Generate job-tailored CV content using Gemma 3.1B"""

    def __init__(self):
        """Initialize with Gemma"""
        print("[*] Initializing Gemma 3.1B for Stage 5...")
        self.llm = Ollama(model="gemma:7b", temperature=0.4)
        print("[✓] Gemma ready")

    def run(self, resume_data, job_data, match_data, evidence_data):
        """Generate tailored CV content and return JSON"""
        print("\n" + "=" * 70)
        print("STAGE 5: GENERATE TAILORED CV (Gemma 3.1B)")
        print("=" * 70)

        evidence = evidence_data["evidence"]
        blocklist = evidence_data["fabrication_blocklist"]

        evidence_lines = "\n".join(
            f"- {skill}: {'; '.join(info['snippets'])}"
            for skill, info in evidence.items()
        ) or "(none)"

        prompt = PromptTemplate(
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

        chain = prompt | self.llm

        current_job = (resume_data.get("experience") or [{}])[0]

        print("[*] Sending evidence + job to Gemma 3.1B...")
        response = chain.invoke({
            "job_title": job_data.get("title", ""),
            "company": job_data.get("company", ""),
            "responsibilities": "; ".join(job_data.get("responsibilities", [])),
            "evidence_lines": evidence_lines,
            "blocklist": ", ".join(blocklist) or "(none)",
            "position": current_job.get("position", ""),
            "duration": current_job.get("duration", ""),
        })

        print(f"[✓] Got response ({len(response)} chars)")
        print("[*] Parsing JSON...")

        try:
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if not json_match:
                print("[✗] No JSON found")
                return None
            data = json.loads(json_match.group(0))
        except json.JSONDecodeError as e:
            print(f"[✗] JSON error: {e}")
            return None

        # Hard safety net: strip any blocklisted skill the model slipped in
        # anyway, rather than trusting it to have followed the prompt.
        blocked = {b.lower() for b in blocklist}
        data["bullets"] = [
            b for b in data.get("bullets", [])
            if not any(bl in b.lower() for bl in blocked)
        ]
        data["ordered_skills"] = [
            s for s in data.get("ordered_skills", [])
            if s.lower() not in blocked
        ]

        print(f"[✓] SUCCESS! Generated {len(data['bullets'])} bullets, "
              f"{len(data['ordered_skills'])} ordered skills")
        return data
