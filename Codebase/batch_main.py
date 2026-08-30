"""Mandatory core task: 10 unstructured profiles -> LLM processing -> 10
professional CVs.

Reads input/profiles/*.txt, writes each profile's extracted JSON, generated
CV JSON, .docx, and .pdf to output/core/. Resumable: a profile whose
extracted/generated JSON already exists in output/core/ is loaded instead
of re-run, so an interrupted batch can continue without redoing work.
"""

import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

from extract_and_parse import ExtractResume
from generate_profile_cv import ProfessionalCVGenerator
from quality_check import check_extraction, check_generated_cv
from render_document import DocumentGenerator
from json_utils import save_json, load_json

PROFILES_DIR = Path("input/profiles")
OUTPUT_DIR = Path("output/core")


def process(profile_path, extractor, generator, renderer):
    stem = profile_path.stem
    extracted_path = OUTPUT_DIR / f"{stem}_extracted.json"
    cv_path = OUTPUT_DIR / f"{stem}_cv.json"

    if extracted_path.exists():
        profile_data = load_json(extracted_path)
    else:
        profile_data = extractor.run(profile_path.read_text(encoding="utf-8"))
        if not profile_data:
            return "extraction returned no data"
        save_json(extracted_path, profile_data)

    issues = check_extraction(profile_data)

    if cv_path.exists():
        generated_cv = load_json(cv_path)
    else:
        generated_cv = generator.run(profile_data)
        if not generated_cv:
            return "generation returned no data"
        save_json(cv_path, generated_cv)

    issues += check_generated_cv(generated_cv, profile_data)

    paths = renderer.run(profile_data, generated_cv, str(OUTPUT_DIR))
    print(f"{profile_path.name}: {paths['docx_path']}" + (f"  (warnings: {', '.join(issues)})" if issues else ""))
    return None


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    profile_files = sorted(PROFILES_DIR.glob("*.txt"))
    if not profile_files:
        print(f"No profile files found in {PROFILES_DIR}/")
        return

    extractor = ExtractResume()
    generator = ProfessionalCVGenerator()
    renderer = DocumentGenerator()

    failures = []
    for profile_path in profile_files:
        try:
            error = process(profile_path, extractor, generator, renderer)
        except Exception as e:
            error = f"crashed: {e}"
        if error:
            failures.append((profile_path.name, error))

    ok = len(profile_files) - len(failures)
    print(f"\n{ok}/{len(profile_files)} CVs generated")
    for name, error in failures:
        print(f"  FAILED {name}: {error}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Cancelled")
