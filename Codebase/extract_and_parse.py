"""Extract structured fields from a resume or job description using Llama 2."""

from langchain_ollama import OllamaLLM
from langchain_core.prompts import PromptTemplate

from json_utils import invoke_json

RESUME_PROMPT = PromptTemplate(
    input_variables=["resume_text"],
    template="""Extract resume data and return ONLY valid JSON:

RESUME:
{resume_text}

Return JSON (no markdown, no explanations):
{{
    "name": "Full Name",
    "email": "email@domain.com",
    "phone": "+1-xxx-xxx-xxxx or empty",
    "location": "City, State or empty",
    "years_experience": "7+ or empty",
    "summary": "Summary or empty",
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
    template="""Parse job and return ONLY valid JSON:

JOB:
{job_text}

Return JSON (no markdown, no explanations):
{{
    "title": "Job Title",
    "company": "Company or empty",
    "location": "Location or empty",
    "experience_level": "junior/mid/senior or empty",
    "years_required": "5+ or empty",
    "required_skills": ["Skill1", "Skill2"],
    "preferred_skills": ["Skill3"],
    "responsibilities": ["Responsibility1"],
    "team_size": "number or empty"
}}""",
)


class ExtractResume:
    """Extract structured resume fields from free text using Llama 2"""

    def __init__(self):
        self.chain = RESUME_PROMPT | OllamaLLM(model="llama2:7b", temperature=0.3)

    def run(self, resume_text):
        return invoke_json(self.chain, {"resume_text": resume_text})


class ParseJob:
    """Extract structured job fields from free text using Llama 2"""

    def __init__(self):
        self.chain = JOB_PROMPT | OllamaLLM(model="llama2:7b", temperature=0.3)

    def run(self, job_text):
        return invoke_json(self.chain, {"job_text": job_text})
