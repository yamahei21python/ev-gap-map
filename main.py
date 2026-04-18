#!/usr/bin/env python3
"""EVCharge CLI - Main entry point (delegates to src/)"""

import argparse
import sys

# Add src to path for imports
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "src"))

from src.main import main


if __name__ == "__main__":
    main()
