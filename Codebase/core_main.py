"""
================================================================================
CORE_MAIN.PY - MANDATORY CORE TASK ORCHESTRATOR
================================================================================

Mandatory core task (per instructor clarification):
    10 unstructured user profiles -> LLM-based processing -> 10 professionally
    generated CVs

Pipeline per profile:
- core_1 (reuses ExtractResume from step_1_2_extract_parse.py): LLM extracts
  structured fields (name, contact, experience, skills, education) from the
  unstructured profile text.
- core_2 (core_2_generate_cv.py): LLM rewrites those facts into a polished,
  professional CV - summary + achievement bullets - without inventing facts.
- core_3 (core_3_quality_check.py): rule-based checks catch empty output,
  leftover placeholder text, or a company/skill the LLM introduced that
  wasn't in the source profile.
- core_4 (core_4_docx.py): renders the generated CV to .docx and .pdf.

Reads from:
- input/profiles/*.txt  (10 unstructured profiles)

Writes to:
- output/core/  (per-profile extracted JSON, generated CV JSON, .docx, .pdf)

USAGE:
python core_main.py

================================================================================
"""

import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

try:
    from step_1_2_extract_parse import ExtractResume
    from core_2_generate_cv import ProfessionalCVGenerator
    from core_3_quality_check import check_extraction, check_generated_cv
    from core_4_docx import ProfessionalDocumentGenerator
except ImportError as e:
    print(f"[✗] ERROR: {e}")
    print(f"    Fix: \"{sys.executable}\" -m pip install -r requirements.txt")
    exit(1)


PROFILES_DIR = Path("input/profiles")
OUTPUT_DIR = Path("output/core")


def run():
    print("\n" + "=" * 70)
    print("CORE TASK: 10 PROFILES -> LLM PROCESSING -> 10 PROFESSIONAL CVS")
    print("=" * 70)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    profile_files = sorted(PROFILES_DIR.glob("*.txt"))
    if not profile_files:
        print(f"[✗] ERROR: no profile files found in {PROFILES_DIR}/")
        return

    print(f"\n[*] Found {len(profile_files)} profile(s) in {PROFILES_DIR}/")

    extractor = ExtractResume()
    generator = ProfessionalCVGenerator()
    doc_generator = ProfessionalDocumentGenerator()

    results = []

    for i, profile_path in enumerate(profile_files, start=1):
        print("\n" + "-" * 70)
        print(f"PROFILE {i}/{len(profile_files)}: {profile_path.name}")
        print("-" * 70)

        stem = profile_path.stem
        extracted_path = OUTPUT_DIR / f"{stem}_extracted.json"
        cv_path = OUTPUT_DIR / f"{stem}_cv.json"

        if cv_path.exists() and extracted_path.exists():
            print("[=] Already completed in a previous run, reusing output")
            with open(extracted_path, encoding="utf-8") as f:
                profile_data = json.load(f)
            with open(cv_path, encoding="utf-8") as f:
                generated_cv = json.load(f)
            extraction_issues, cv_issues = [], []
        else:
            profile_text = profile_path.read_text(encoding="utf-8")

            # ---- extract ----
            if extracted_path.exists():
                print("[=] Reusing extraction from a previous run")
                with open(extracted_path, encoding="utf-8") as f:
                    profile_data = json.load(f)
            else:
                try:
                    profile_data = extractor.run(profile_text)
                except Exception as e:
                    print(f"[✗] Extraction crashed: {e}")
                    results.append((profile_path.name, "FAILED", "extraction crashed"))
                    continue

                if not profile_data:
                    print("[✗] Extraction returned no data, skipping")
                    results.append((profile_path.name, "FAILED", "extraction returned no data"))
                    continue

                with open(extracted_path, "w", encoding="utf-8") as f:
                    json.dump(profile_data, f, indent=2)

            extraction_issues = check_extraction(profile_data)
            if extraction_issues:
                print(f"[!] Extraction quality issues: {', '.join(extraction_issues)}")

            # ---- generate ----
            try:
                generated_cv = generator.run(profile_data)
            except Exception as e:
                print(f"[✗] Generation crashed: {e}")
                results.append((profile_path.name, "FAILED", "generation crashed"))
                continue

            if not generated_cv:
                print("[✗] Generation returned no data, skipping")
                results.append((profile_path.name, "FAILED", "generation returned no data"))
                continue

            cv_issues = check_generated_cv(generated_cv, profile_data)
            if cv_issues:
                print(f"[!] Generated CV quality issues: {', '.join(cv_issues)}")

            with open(cv_path, "w", encoding="utf-8") as f:
                json.dump(generated_cv, f, indent=2)

        # ---- render ----
        try:
            paths = doc_generator.run(profile_data, generated_cv, str(OUTPUT_DIR))
        except Exception as e:
            print(f"[✗] Document rendering crashed: {e}")
            results.append((profile_path.name, "FAILED", "rendering crashed"))
            continue

        print(f"[✓] Saved: {paths['docx_path']}")
        print(f"[✓] Saved: {paths['pdf_path']}")

        status = "OK" if not (extraction_issues or cv_issues) else "OK (with warnings)"
        results.append((profile_path.name, status, ""))

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    ok_count = sum(1 for _, status, _ in results if status.startswith("OK"))
    for name, status, note in results:
        marker = "✓" if status.startswith("OK") else "✗"
        suffix = f" - {note}" if note else ""
        print(f"  [{marker}] {name}: {status}{suffix}")
    print(f"\n{ok_count}/{len(profile_files)} CVs generated successfully")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        run()
    except KeyboardInterrupt:
        print("\n[*] Cancelled")
