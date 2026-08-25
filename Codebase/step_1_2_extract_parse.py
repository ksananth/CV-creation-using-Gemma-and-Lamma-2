"""
================================================================================
STAGE 1 & 2: EXTRACT RESUME + PARSE JOB
================================================================================

Classes:
- ExtractResume: Extract resume using Gemma 3.1B
- ParseJob: Parse job using Gemma 3.1B

Can be run standalone or imported by main.py

STANDALONE:
python stage_1_2_extract_parse.py

IMPORT:
from stage_1_2_extract_parse import ExtractResume, ParseJob

================================================================================
"""

import json
import re
from langchain_community.llms import Ollama
from langchain_core.prompts import PromptTemplate


# ============================================================================
# STAGE 1: EXTRACT RESUME
# ============================================================================

class ExtractResume:
    """Extract resume using Gemma 3.1B"""
    
    def __init__(self):
        """Initialize with Gemma"""
        print("[*] Initializing Gemma 3.1B for Stage 1...")
        self.llm = Ollama(model="gemma:7b", temperature=0.3)
        print("[✓] Gemma ready")
    
    def run(self, resume_text):
        """Extract resume and return JSON"""
        print("\n" + "="*70)
        print("STAGE 1: EXTRACT RESUME (Gemma 3.1B)")
        print("="*70)
        
        prompt = PromptTemplate(
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
}}"""
        )
        
        chain = prompt | self.llm

        print("[*] Sending resume to Gemma 3.1B...")
        response = chain.invoke({"resume_text": resume_text})
        
        print(f"[✓] Got response ({len(response)} chars)")
        print("[*] Parsing JSON...")
        
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                print(f"[✓] SUCCESS! Extracted resume")
                print(f"    Name: {data.get('name', 'N/A')}")
                print(f"    Experience: {len(data.get('experience', []))} jobs")
                print(f"    Skills: {len(data.get('skills', []))} skills")
                return data
            else:
                print("[✗] No JSON found")
                return None
        except json.JSONDecodeError as e:
            print(f"[✗] JSON error: {e}")
            return None


# ============================================================================
# STAGE 2: PARSE JOB
# ============================================================================

class ParseJob:
    """Parse job using Gemma 3.1B"""
    
    def __init__(self):
        """Initialize with Gemma"""
        print("[*] Initializing Gemma 3.1B for Stage 2...")
        self.llm = Ollama(model="gemma:7b", temperature=0.3)
        print("[✓] Gemma ready")
    
    def run(self, job_text):
        """Parse job and return JSON"""
        print("\n" + "="*70)
        print("STAGE 2: PARSE JOB (Gemma 3.1B)")
        print("="*70)
        
        prompt = PromptTemplate(
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
}}"""
        )
        
        chain = prompt | self.llm

        print("[*] Sending job to Gemma 3.1B...")
        response = chain.invoke({"job_text": job_text})
        
        print(f"[✓] Got response ({len(response)} chars)")
        print("[*] Parsing JSON...")
        
        try:
            json_match = re.search(r'\{.*\}', response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                print(f"[✓] SUCCESS! Parsed job")
                print(f"    Title: {data.get('title', 'N/A')}")
                print(f"    Required skills: {len(data.get('required_skills', []))}")
                return data
            else:
                print("[✗] No JSON found")
                return None
        except json.JSONDecodeError as e:
            print(f"[✗] JSON error: {e}")
            return None

