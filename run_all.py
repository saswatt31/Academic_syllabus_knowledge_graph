"""Run the full syllabus knowledge-graph pipeline in one go."""
import subprocess
import sys

STEPS = [
    "ner_extractor.py",
    "relation_extractor.py",
    "build_graph.py",
    "visualize_graph.py",
    "query_graph.py",
    "evaluate_extraction.py",
]

for script in STEPS:
    print(f"\n=== {script} " + "=" * 50)
    ret = subprocess.run([sys.executable, script]).returncode
    if ret != 0:
        sys.exit(f"{script} failed with exit code {ret}")
print("\nAll done. See results/ for outputs.")
