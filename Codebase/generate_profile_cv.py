"""Rewrite one extracted profile into a polished, professional CV using
Gemma. There is no target job here (unlike generate_tailored_cv.py) - the
goal is only to professionalise the candidate's own facts (clear summary,
strong action-verb bullets, consistent formatting), not to match a posting.
"""

from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate

from json_utils import invoke_json

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
    """Rewrite an extracted profile into a professional CV using Gemma"""

    def __init__(self):
        self.chain = PROMPT | OllamaLLM(model="gemma:7b", temperature=0.4)

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
        return invoke_json(self.chain, inputs)
