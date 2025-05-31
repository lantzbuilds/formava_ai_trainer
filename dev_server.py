import os
import subprocess
import sys
import time

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer


class AppReloader(FileSystemEventHandler):
    def __init__(self):
        self.process = None
        self.start_app()

    def start_app(self):
        if self.process:
            self.process.terminate()
            self.process.wait()
        print("Starting application...")
        self.process = subprocess.Popen([sys.executable, "app.py"])

    def on_modified(self, event):
        if event.src_path.endswith(".py"):
            print(f"Detected change in {event.src_path}")
            self.start_app()


def main():
    path = "."
    event_handler = AppReloader()
    observer = Observer()
    observer.schedule(event_handler, path, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        if event_handler.process:
            event_handler.process.terminate()
    observer.join()


if __name__ == "__main__":
    main()
