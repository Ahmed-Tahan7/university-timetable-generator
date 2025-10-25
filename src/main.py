"""
CSIT Timetable Generator - Entry Point
"""

import sys
import os

# Add parent directory to path (this fixes the import error)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.gui import run_gui


if __name__ == "__main__":
    print("=" * 60)
    print("CSIT Timetable Generator")
    print("=" * 60)
    print("\nLaunching GUI application...")
    print("Please wait while the interface loads...\n")
    
    # Launch the GUI
    run_gui()
