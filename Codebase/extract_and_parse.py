"""Extract structured fields from a resume or job description using Llama 2."""

from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate

from json_utils import invoke_json

RESUME_PROMPT = PromptTemplate(
    input_variables=["resume_text"],
    template="""Extract resume data and return ONLY valid JSON. If a field is
not mentioned in the resume, use an empty string "" (or an empty list [] for
list fields) - never write placeholder or filler text into a field.

RESUME:
{resume_text}

Return JSON (no markdown, no explanations):
{{
    "name": "Full Name",
    "email": "email@domain.com",
    "phone": "+1-xxx-xxx-xxxx",
    "location": "City, State",
    "years_experience": "7+",
    "summary": "Professional summary",
    "experience": [
        {{"company": "Name", "position": "Title", "duration": "Start-End", "location": "City", "description": "Achievements"}}
    ],
    "skills": ["Skill1", "Skill2"],
    "education": [
        {{"degree": "Degree", "field": "Field", "school": "School", "graduation_year": "YYYY"}}
    ],
    "certifications": ["Cert1"],
    "languages": ["Language1"]
}}""",
)

JOB_PROMPT = PromptTemplate(
    input_variables=["job_text"],
    template="""Parse job and return ONLY valid JSON. If a field is not
mentioned in the job description, use an empty string "" (or an empty list
[] for list fields) - never write placeholder or filler text into a field.

JOB:
{job_text}

Return JSON (no markdown, no explanations):
{{
    "title": "Job Title",
    "company": "",
    "location": "",
    "experience_level": "junior/mid/senior",
    "years_required": "5+",
    "required_skills": ["Skill1", "Skill2"],
    "preferred_skills": ["Skill3"],
    "responsibilities": ["Responsibility1"],
    "team_size": ""
}}""",
)


_PLACEHOLDER_SUFFIX = "or empty"


def _clean_placeholders(data):
    """Hard safety net: some local models echo the prompt's own field-hint
    text (e.g. 'Company or empty') into a field instead of leaving it blank
    when the source text doesn't mention it. Blank those out rather than
    trust every model to have followed the "" instruction."""
    for key, value in data.items():
        if isinstance(value, str) and value.strip().lower().endswith(_PLACEHOLDER_SUFFIX):
            data[key] = ""
    return data


class ExtractResume:
    """Extract structured resume fields from free text using Llama 2"""

    def __init__(self):
        # format="json" stops the model rambling past the closing brace
        # (fewer malformed-JSON retries, each of which costs a full
        # regeneration); num_predict bounds worst-case runaway output;
        # keep_alive keeps the model loaded across the whole batch instead
        # of unloading between calls.
        self.chain = RESUME_PROMPT | OllamaLLM(
            model="llama2:7b", temperature=0.3, format="json",
            num_predict=1024, keep_alive="15m",
        )

    def run(self, resume_text):
        data = invoke_json(self.chain, {"resume_text": resume_text})
        return _clean_placeholders(data) if data else data


class ParseJob:
    """Extract structured job fields from free text using Llama 2"""

    def __init__(self):
        self.chain = JOB_PROMPT | OllamaLLM(
            model="llama2:7b", temperature=0.3, format="json",
            num_predict=700, keep_alive="15m",
        )

    def run(self, job_text):
        data = invoke_json(self.chain, {"job_text": job_text})
        return _clean_placeholders(data) if data else data
