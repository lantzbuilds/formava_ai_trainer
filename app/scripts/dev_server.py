"""
Development server with hot-reloading for the AI Personal Trainer application.
"""

import os
import sys
import time
from pathlib import Path

import gradio as gr
from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class AppReloader(FileSystemEventHandler):
    """Handler for file system events that trigger app reload."""

    def __init__(self, app):
        self.app = app
        self.last_reload = 0
        self.reload_cooldown = 2  # seconds

    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return

        # Ignore certain file types and directories
        if any(x in event.src_path for x in [".git", "__pycache__", ".pytest_cache"]):
            return

        # Check if file is a Python file
        if not event.src_path.endswith(".py"):
            return

        # Prevent rapid reloads
        current_time = time.time()
        if current_time - self.last_reload < self.reload_cooldown:
            return

        print(f"\n🔄 Reloading due to changes in {event.src_path}")
        self.last_reload = current_time
        self.app.reload()


def run_dev_server():
    """Run the development server with hot-reloading."""
    # Add the project root to Python path
    project_root = Path(__file__).parent.parent.parent
    sys.path.insert(0, str(project_root))

    # Import the app creation function
    from app.main import create_app

    # Create the app
    app = create_app()

    # Setup file watcher
    event_handler = AppReloader(app)
    observer = Observer()
    observer.schedule(event_handler, path=str(project_root), recursive=True)
    observer.start()

    try:
        # Launch the app
        app.launch(server_name="0.0.0.0", server_port=7860, share=True, debug=True)
    except KeyboardInterrupt:
        observer.stop()
    observer.join()


if __name__ == "__main__":
    run_dev_server()
