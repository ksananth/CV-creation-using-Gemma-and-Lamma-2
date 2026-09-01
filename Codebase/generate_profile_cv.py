"""Rewrite one extracted profile into a polished, professional CV using
Gemma 3. There is no target job here (unlike generate_tailored_cv.py) - the
goal is only to professionalise the candidate's own facts (clear summary,
strong action-verb bullets, consistent formatting), not to match a posting.
"""

import json

from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate

from json_utils import invoke_json, merge_unique

REFINE_PROMPT = PromptTemplate(
    input_variables=["current_cv", "raw_summary", "experience_lines", "skills", "feedback"],
    template="""You are revising a CV based on user feedback. Use ONLY the
candidate's own facts below - do not invent employers, numbers, titles, or
achievements that are not stated or clearly implied.

CURRENT CV:
{current_cv}

CANDIDATE'S OWN FACTS:
BACKGROUND (their own words): {raw_summary}
WORK HISTORY:
{experience_lines}
SKILLS: {skills}

Apply the user's feedback below; leave anything the feedback doesn't mention unchanged.

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
    input_variables=["name", "raw_summary", "experience_lines", "skills"],
    template="""You are a professional CV writer. Rewrite the candidate's own
facts below into polished, professional CV content. Use ONLY the facts given -
do not invent employers, numbers, titles, or achievements that are not stated
or clearly implied below. Do not name any specific tool, software, or
technology unless it appears in SKILLS or WORK HISTORY below.

CANDIDATE: {name}
BACKGROUND (their own words): {raw_summary}
WORK HISTORY:
{experience_lines}
SKILLS: {skills}

Return ONLY valid JSON (no markdown, no explanations):
{{
    "summary": "2-3 sentence professional summary in third person, based only on the background given",
    "experience": [
        {{"position": "Title", "company": "Name", "duration": "Start-End", "bullets": ["Polished achievement bullet", "Another bullet"]}}
    ],
    "ordered_skills": ["skill1", "skill2"]
}}""",
)


class ProfessionalCVGenerator:
    """Rewrite an extracted profile into a professional CV using Gemma 3"""

    def __init__(self):
        self.chain = PROMPT | OllamaLLM(model="gemma3:1b", temperature=0.4)
        self.refine_chain = REFINE_PROMPT | OllamaLLM(model="gemma3:1b", temperature=0.4)

    def run(self, profile_data):
        experience = profile_data.get("experience", []) or []
        inputs = {
            "name": profile_data.get("name", ""),
            "raw_summary": profile_data.get("summary", ""),
            "experience_lines": "\n".join(
                f"- {job.get('position', '')} at {job.get('company', '')} "
                f"({job.get('duration', '')}): {job.get('description', '')}"
                for job in experience
            ) or "(none provided)",
            "skills": ", ".join(profile_data.get("skills", [])),
        }
        data = invoke_json(self.chain, inputs)
        if data is None:
            return None
        data["ordered_skills"] = merge_unique(data.get("ordered_skills", []), profile_data.get("skills", []))
        return data

    def refine(self, current_cv, feedback, profile_data):
        """Revise an already-generated CV per free-text user feedback,
        constrained to the same candidate facts as the original generation."""
        experience = profile_data.get("experience", []) or []
        inputs = {
            "current_cv": json.dumps(current_cv, indent=2),
            "raw_summary": profile_data.get("summary", ""),
            "experience_lines": "\n".join(
                f"- {job.get('position', '')} at {job.get('company', '')} "
                f"({job.get('duration', '')}): {job.get('description', '')}"
                for job in experience
            ) or "(none provided)",
            "skills": ", ".join(profile_data.get("skills", [])),
            "feedback": feedback,
        }
        return invoke_json(self.refine_chain, inputs)
