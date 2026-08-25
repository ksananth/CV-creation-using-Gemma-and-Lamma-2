"""
================================================================================
MAIN.PY - ORCHESTRATOR
================================================================================

Orchestrates all stages by importing from separate stage files:
- stage_1_2_extract_parse.py (Extract Resume + Parse Job)
- stage_3_skill_matcher.py (Skill Matching)
- stage_4_rag_resumelm.py (RAG + ResumeLM)
- stage_5_cv_generator.py (CV Generation)
- stage_6_docx_generator.py (DOCX and PDF Output)

Reads from:
- input/resume.txt
- input/job_description.txt

Writes to:
- output/ (all results)

USAGE:
python main.py

================================================================================
"""

import json
import os
import sys
from pathlib import Path

# Windows consoles default to cp1252, which can't encode the ✓/✗ status glyphs
sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

# Import stage modules
try:
    from step_1_2_extract_parse import ExtractResume, ParseJob
    print("[✓] Imported: step_1_2_extract_parse.py")
except ImportError as e:
    print(f"[✗] ERROR: Cannot import stage_1_2_extract_parse.py")
    print(f"    Make sure stage_1_2_extract_parse.py is in same folder as main.py")
    print(f"    Error: {e}")
    exit(1)


# ============================================================================
# SETUP
# ============================================================================

Path("input").mkdir(exist_ok=True)
Path("output").mkdir(exist_ok=True)


# ============================================================================
# ORCHESTRATOR
# ============================================================================

class CVOrchestrator:
    """Orchestrate all stages"""
    
    def __init__(self):
        """Initialize"""
        print("\n" + "="*70)
        print("CV GENERATION ORCHESTRATOR")
        print("="*70)
    
    def run(self):
        """Run pipeline"""
        print("\n[*] Checking input files...")
        
        resume_path = "input/resume.txt"
        job_path = "input/job_description.txt"
        
        # Check files exist
        if not os.path.exists(resume_path):
            print(f"[✗] ERROR: {resume_path} not found!")
            print(f"    Create: input/resume.txt with your resume")
            return
        
        if not os.path.exists(job_path):
            print(f"[✗] ERROR: {job_path} not found!")
            print(f"    Create: input/job_description.txt with job description")
            return
        
        print(f"[✓] Found: {resume_path}")
        print(f"[✓] Found: {job_path}")
        
        # Load input files
        print("\n[*] Loading input files...")
        with open(resume_path, 'r', encoding='utf-8') as f:
            resume_text = f.read()
        print(f"[✓] Resume loaded ({len(resume_text)} chars)")
        
        with open(job_path, 'r', encoding='utf-8') as f:
            job_text = f.read()
        print(f"[✓] Job loaded ({len(job_text)} chars)")
        
        # ====================================================================
        # STAGE 1 & 2: Extract Resume + Parse Job
        # ====================================================================
        
        print("\n[*] Running Stage 1 & 2...")
        
        try:
            # Stage 1
            extractor = ExtractResume()
            resume_data = extractor.run(resume_text)
            
            if not resume_data:
                print("[✗] Stage 1 failed!")
                return
            
            # Save Stage 1 output
            with open("output/stage_1_extracted_resume.json", 'w', encoding='utf-8') as f:
                json.dump(resume_data, f, indent=2)
            print("[✓] Saved: output/stage_1_extracted_resume.json")
            
            # Stage 2
            parser = ParseJob()
            job_data = parser.run(job_text)
            
            if not job_data:
                print("[✗] Stage 2 failed!")
                return
            
            # Save Stage 2 output
            with open("output/stage_2_parsed_job.json", 'w', encoding='utf-8') as f:
                json.dump(job_data, f, indent=2)
            print("[✓] Saved: output/stage_2_parsed_job.json")
        
        except Exception as e:
            print(f"[✗] ERROR in Stage 1 & 2: {e}")
            import traceback
            traceback.print_exc()
            return
        
        
        print("\n" + "="*70)
        print("SUMMARY")
        print("="*70)
        
        print(f"\nRESUME DATA:")
        print(f"  Name: {resume_data.get('name', 'N/A')}")
        print(f"  Email: {resume_data.get('email', 'N/A')}")
        print(f"  Experience: {len(resume_data.get('experience', []))} jobs")
        print(f"  Skills: {len(resume_data.get('skills', []))} skills")
        
        print(f"\nJOB DATA:")
        print(f"  Title: {job_data.get('title', 'N/A')}")
        print(f"  Company: {job_data.get('company', 'N/A')}")
        print(f"  Required skills: {len(job_data.get('required_skills', []))}")
        
        print(f"\nOUTPUT FILES:")
        print(f"  ✓ output/stage_1_extracted_resume.json")
        print(f"  ✓ output/stage_2_parsed_job.json")
        
        print("\n" + "="*70)
        print("✅ STAGE 1 & 2 COMPLETE!")
        print("="*70)
        print("\nNext: Uncomment stages 3-6 when ready")
        print("="*70 + "\n")


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    try:
        orchestrator = CVOrchestrator()
        orchestrator.run()
    except KeyboardInterrupt:
        print("\n[*] Cancelled")
    except Exception as e:
        print(f"\n[✗] ERROR: {e}")
        import traceback
        traceback.print_exc()