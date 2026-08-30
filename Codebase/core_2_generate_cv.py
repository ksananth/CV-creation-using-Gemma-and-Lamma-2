"""
================================================================================
CORE TASK - STEP 2: GENERATE PROFESSIONAL CV
================================================================================

Classes:
- ProfessionalCVGenerator: Turn one extracted, unstructured profile into a
  polished, professional CV using Gemma 3.1B. Unlike the enhancement
  pipeline (step_5_generate.py), this has no target job to tailor against -
  the goal is just to professionalise the candidate's own facts (clear
  summary, strong action-verb bullets, consistent tense/formatting), not to
  match a posting.

Imported by core_main.py

IMPORT:
from core_2_generate_cv import ProfessionalCVGenerator

================================================================================
"""

import json
import re
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate


class ProfessionalCVGenerator:
    """Rewrite an extracted profile into a professional CV using Gemma 3.1B"""

    def __init__(self):
        print("[*] Initializing Gemma 3.1B for CV generation...")
        self.llm = Ollama(model="gemma:7b", temperature=0.4)
        print("[✓] Gemma ready")

    def run(self, profile_data):
        """Generate professional CV content and return JSON"""
        experience = profile_data.get("experience", []) or []
        experience_lines = "\n".join(
            f"- {job.get('position', '')} at {job.get('company', '')} "
            f"({job.get('duration', '')}): {job.get('description', '')}"
            for job in experience
        ) or "(none provided)"

        prompt = PromptTemplate(
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
}}"""
        )

        chain = prompt | self.llm
        inputs = {
            "name": profile_data.get("name", ""),
            "raw_summary": profile_data.get("summary", ""),
            "experience_lines": experience_lines,
            "skills": ", ".join(profile_data.get("skills", [])),
        }

        max_attempts = 3
        for attempt in range(1, max_attempts + 1):
            response = chain.invoke(inputs)
            data = self._parse(response)
            if data is not None:
                return data
            print(f"[!] Attempt {attempt}/{max_attempts} produced unparseable JSON"
                  + (", retrying..." if attempt < max_attempts else ""))

        print(f"    Raw response: {response[:800]}")
        return None

    @staticmethod
    def _parse(response):
        """Try to pull valid JSON out of a Gemma response; return None on failure"""
        json_match = re.search(r"\{.*\}", response, re.DOTALL)
        if not json_match:
            return None

        raw_json = json_match.group(0)
        no_trailing_commas = re.sub(r",\s*([}\]])", r"\1", raw_json)
        candidates = [
            raw_json,
            no_trailing_commas,
            _fix_unterminated_before_bracket(raw_json),
            _fix_unterminated_before_bracket(no_trailing_commas),
        ]
        for candidate in candidates:
            try:
                return json.loads(candidate, strict=False)
            except json.JSONDecodeError:
                continue
        return None


def _fix_unterminated_before_bracket(text):
    """Gemma occasionally drops the closing quote on the last string in a
    bullet list (e.g. '...days.]}' instead of '...days."]}'). Insert the
    missing quote wherever ']' is not preceded by a quote, brace, or bracket."""
    out = []
    for c in text:
        if c == "]":
            j = len(out) - 1
            while j >= 0 and out[j] in " \t\n\r":
                j -= 1
            prev = out[j] if j >= 0 else ""
            if prev not in ('"', "}", "]", "["):
                out.append('"')
        out.append(c)
    return "".join(out)
