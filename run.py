"""
Run script for the AI Personal Trainer application with improved hot-reloading support.
"""

import os
import subprocess
import sys
import time
from typing import List

import streamlit as st
from dotenv import load_dotenv


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


def check_couchdb_running():
    """Check if CouchDB container is running."""
    try:
        result = subprocess.run(
            ["docker", "ps", "--filter", "name=couchdb", "--format", "{{.Names}}"],
            capture_output=True,
            text=True,
            timeout=5,  # Add a 5-second timeout
        )
        return "couchdb" in result.stdout
    except subprocess.TimeoutExpired:
        print("Timeout checking CouchDB container status")
        return False
    except subprocess.CalledProcessError:
        return False


def check_couchdb_exists():
    """Check if CouchDB container exists (running or stopped)."""
    try:
        result = subprocess.run(
            [
                "docker",
                "ps",
                "-a",
                "--filter",
                "name=couchdb",
                "--format",
                "{{.Names}}",
            ],
            capture_output=True,
            text=True,
            timeout=5,  # Add a 5-second timeout
        )
        return "couchdb" in result.stdout
    except subprocess.TimeoutExpired:
        print("Timeout checking CouchDB container existence")
        return False
    except subprocess.CalledProcessError:
        return False


def start_couchdb():
    """Start CouchDB container if not already running."""
    if not check_couchdb_running():
        if check_couchdb_exists():
            print("Starting existing CouchDB container...")
            try:
                subprocess.run(
                    ["docker", "start", "couchdb"],
                    check=True,
                )
                # Wait for CouchDB to be ready
                print("Waiting for CouchDB to be ready...")
                time.sleep(5)  # Give CouchDB time to start
            except subprocess.CalledProcessError as e:
                print(f"Error starting existing CouchDB container: {e}")
                raise
        else:
            print("Creating new CouchDB container...")
            couchdb_user = os.getenv("COUCHDB_USER", "admin")
            couchdb_password = os.getenv("COUCHDB_PASSWORD", "password")

            try:
                subprocess.run(
                    [
                        "docker",
                        "run",
                        "-d",
                        "--name",
                        "couchdb",
                        "-p",
                        "5984:5984",
                        "-e",
                        f"COUCHDB_USER={couchdb_user}",
                        "-e",
                        f"COUCHDB_PASSWORD={couchdb_password}",
                        "couchdb:latest",
                    ],
                    check=True,
                )

                # Wait for CouchDB to be ready
                print("Waiting for CouchDB to be ready...")
                time.sleep(5)  # Give CouchDB time to start

            except subprocess.CalledProcessError as e:
                print(f"Error creating CouchDB container: {e}")
                raise


def check_docker_running():
    """Check if Docker Desktop is running."""
    try:
        # Try to get Docker version - this will fail if Docker Desktop isn't running
        result = subprocess.run(
            ["docker", "version"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        return False


def main():
    """Main function to run the application."""
    # Load environment variables
    load_dotenv()

    # Check if Docker Desktop is running
    if not check_docker_running():
        print(
            "Docker Desktop is not running. Please start Docker Desktop and try again."
        )
        return

    # Check and start CouchDB if needed
    start_couchdb()

    # Run the Streamlit app
    run_streamlit()


if __name__ == "__main__":
    # Get any additional arguments passed to the script
    args = sys.argv[1:]
    main()
