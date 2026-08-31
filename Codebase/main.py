"""Tailored CV pipeline: resumes + job description -> job-tailored, ATS-friendly CVs.

Usage:
    py main.py -input <input_folder> -output <output_folder> -jd <job_description_file>

Reads every resume .txt file from the input folder and one job description
file, and writes a tailored CV (.docx/.pdf) plus stage JSON for each resume
into the output folder.
"""

import argparse
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from extract_and_parse import ExtractResume, ParseJob
from match_skills import MatchSkills
from retrieve_evidence import RetrieveEvidence
from generate_tailored_cv import GenerateCV
from render_document import DocumentGenerator
from json_utils import save_json


def parse_args():
    parser = argparse.ArgumentParser(description="Generate ATS-friendly, job-tailored CVs.")
    parser.add_argument("-input", dest="input_dir", required=True, help="Folder containing resume .txt files")
    parser.add_argument("-output", dest="output_dir", required=True, help="Folder to write generated CVs and stage JSON")
    parser.add_argument("-jd", dest="jd_path", required=True, help="Path to the job description .txt file")
    return parser.parse_args()


def process_resume(resume_path, job_data, output_dir, extractor, matcher, retriever, generator, renderer):
    stem = resume_path.stem
    resume_text = resume_path.read_text(encoding="utf-8")

    resume_data = extractor.run(resume_text)
    if not resume_data:
        return "extraction failed: Gemma did not return valid JSON"
    save_json(output_dir / f"{stem}_extracted_resume.json", resume_data)

    match_data = matcher.run(resume_data, job_data)
    save_json(output_dir / f"{stem}_match.json", match_data)

    evidence_data = retriever.run(resume_data, match_data)
    save_json(output_dir / f"{stem}_evidence.json", evidence_data)

    generated_cv = generator.run(resume_data, job_data, match_data, evidence_data)
    if not generated_cv:
        return "generation failed: Gemma did not return valid JSON"
    save_json(output_dir / f"{stem}_generated_cv.json", generated_cv)

    heading = f"Experience - tailored for {job_data.get('title', '')} at {job_data.get('company', '')}"
    paths = renderer.run(
        resume_data, generated_cv, str(output_dir),
        experience_heading=heading, filename_suffix=job_data.get("company", ""),
    )

    print(f"  {resume_path.name} -> {paths['docx_path']}  "
          f"(required {match_data['required']['coverage_pct']}%, preferred {match_data['preferred']['coverage_pct']}%)")
    if match_data["fabrication_blocklist"]:
        print(f"    Could not prove (excluded from CV): {', '.join(match_data['fabrication_blocklist'])}")
    return None


def main():
    args = parse_args()
    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    jd_path = Path(args.jd_path)

    if not input_dir.is_dir():
        print(f"Input folder not found: {input_dir}")
        return
    if not jd_path.is_file():
        print(f"Job description file not found: {jd_path}")
        return

    resume_files = sorted(input_dir.glob("*.txt"))
    if not resume_files:
        print(f"No resume .txt files found in {input_dir}")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Parsing Sample Resumes from {input_dir}")
    print(f"Parsing JD from {jd_path}")

    job_text = jd_path.read_text(encoding="utf-8")
    job_data = ParseJob().run(job_text)
    if not job_data:
        print("JD parsing failed: Gemma did not return valid JSON")
        return
    save_json(output_dir / "parsed_job_description.json", job_data)

    extractor = ExtractResume()
    matcher = MatchSkills()
    retriever = RetrieveEvidence()
    generator = GenerateCV()
    renderer = DocumentGenerator()

    print(f"Creating ATS friendly Resumes in {output_dir}")
    failures = []
    for resume_path in resume_files:
        try:
            error = process_resume(resume_path, job_data, output_dir, extractor, matcher, retriever, generator, renderer)
        except Exception as e:
            error = f"crashed: {e}"
        if error:
            failures.append((resume_path.name, error))
            print(f"  FAILED {resume_path.name}: {error}")

    ok = len(resume_files) - len(failures)
    print(f"\nCompleted: {ok}/{len(resume_files)} ATS-friendly CVs generated in {output_dir}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Cancelled")
