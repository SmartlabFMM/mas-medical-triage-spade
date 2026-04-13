import sys
import os

# Ensure the root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import the main function from ml_triage/train.py
from ml_triage.train import main

if __name__ == "__main__":
    main()
