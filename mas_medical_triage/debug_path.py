import sys
import os

# Add the project root to sys.path
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, root_dir)

print(f"CWD: {os.getcwd()}")
print(f"Project Root: {root_dir}")
print(f"PYTHONPATH: {os.environ.get('PYTHONPATH')}")

try:
    from agents.clinical_agent import ClinicalAgent
    print("SUCCESS: Imported ClinicalAgent")
except Exception as e:
    print(f"FAIL: ClinicalAgent import failed: {e}")

try:
    from utils.severity_calculator import compute_score
    print("SUCCESS: Imported compute_score")
except Exception as e:
    print(f"FAIL: compute_score import failed: {e}")