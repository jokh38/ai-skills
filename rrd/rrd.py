#!/usr/bin/env python3
"""RRD - Recursive Repair Development Entry Point"""

import sys
from pathlib import Path

# Add to Python path
sys.path.insert(0, str(Path(__file__).parent))

from cli.cli import cli

if __name__ == "__main__":
    sys.exit(cli())
