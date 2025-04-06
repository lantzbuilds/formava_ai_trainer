"""
Run script for the AI Personal Trainer application with improved hot-reloading support.
"""

import os
import subprocess
import sys
from typing import List


def run_streamlit(args: List[str] = None):
    """Run Streamlit with hot-reloading enabled."""
    if args is None:
        args = []

    # Base command with hot-reloading enabled
    cmd = [
        "streamlit",
        "run",
        "app.py",
        "--server.runOnSave=true",
        "--server.fileWatcherType=watchdog",
        "--logger.level=debug",
    ]

    # Add any additional arguments
    cmd.extend(args)

    # Run the command
    subprocess.run(cmd)


if __name__ == "__main__":
    # Get any additional arguments passed to the script
    args = sys.argv[1:]
    run_streamlit(args)
