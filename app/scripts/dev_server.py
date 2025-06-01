"""
Development server for the AI Personal Trainer application.
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

# Import the app creation function
from app.main import create_app

if __name__ == "__main__":
    # Create and launch the app
    app = create_app()
    app.launch(server_name="0.0.0.0", server_port=7860, share=True, debug=True)
