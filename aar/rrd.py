#!/usr/bin/env python3
"""RRD - Recursive Repair Development Entry Point"""

import sys
from pathlib import Path

# Add src and tools directories to Python path
src_dir = Path(__file__).parent / "src"
tools_dir = Path(__file__).parent / "tools"
sys.path.insert(0, str(src_dir))
sys.path.insert(0, str(tools_dir))

# Import and execute
from src.cli import main

if __name__ == "__main__":
    sys.exit(main())
