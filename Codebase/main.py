"""Tailored CV pipeline: resume + job description -> job-tailored CV.

Reads input/resume.txt and input/job_description.txt, writes stage outputs
and the final .docx/.pdf to output/.
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from extract_and_parse import ExtractResume, ParseJob
from match_skills import MatchSkills
from retrieve_evidence import RetrieveEvidence
from generate_tailored_cv import GenerateCV
from render_document import DocumentGenerator
from json_utils import save_json

INPUT_DIR = Path("input")
OUTPUT_DIR = Path("output")


def main():
    INPUT_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    resume_path = INPUT_DIR / "resume.txt"
    job_path = INPUT_DIR / "job_description.txt"
    if not resume_path.exists() or not job_path.exists():
        print(f"Missing {resume_path} or {job_path}")
        return

    resume_text = resume_path.read_text(encoding="utf-8")
    job_text = job_path.read_text(encoding="utf-8")

    print("Extracting resume and job description...")
    resume_data = ExtractResume().run(resume_text)
    job_data = ParseJob().run(job_text)
    if not resume_data or not job_data:
        print("Extraction failed: Gemma did not return valid JSON")
        return
    save_json(OUTPUT_DIR / "stage_1_extracted_resume.json", resume_data)
    save_json(OUTPUT_DIR / "stage_2_parsed_job.json", job_data)

    print("Matching skills...")
    match_data = MatchSkills().run(resume_data, job_data)
    save_json(OUTPUT_DIR / "stage_3_match.json", match_data)

    print("Retrieving evidence...")
    evidence_data = RetrieveEvidence().run(resume_data, match_data)
    save_json(OUTPUT_DIR / "stage_4_evidence.json", evidence_data)

    print("Generating tailored CV...")
    generated_cv = GenerateCV().run(resume_data, job_data, match_data, evidence_data)
    if not generated_cv:
        print("CV generation failed: Gemma did not return valid JSON")
        return
    save_json(OUTPUT_DIR / "stage_5_generated_cv.json", generated_cv)

    print("Rendering documents...")
    heading = f"Experience - tailored for {job_data.get('title', '')} at {job_data.get('company', '')}"
    paths = DocumentGenerator().run(
        resume_data, generated_cv, str(OUTPUT_DIR),
        experience_heading=heading, filename_suffix=job_data.get("company", ""),
    )

    print(f"\nRequired skills matched: {match_data['required']['coverage_pct']}%  "
          f"Preferred: {match_data['preferred']['coverage_pct']}%")
    if match_data["fabrication_blocklist"]:
        print(f"Could not prove (excluded from CV): {', '.join(match_data['fabrication_blocklist'])}")
    print(f"Saved: {paths['docx_path']}")
    print(f"Saved: {paths['pdf_path']}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Cancelled")
