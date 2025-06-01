"""
Run script for the AI Personal Trainer application with Gradio implementation.
"""

import os
import socket
import subprocess
import sys
import time
from typing import List

from dotenv import load_dotenv


def is_port_in_use(port: int) -> bool:
    """Check if a port is already in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("localhost", port)) == 0


def run_gradio(args: List[str] = None):
    """Run Gradio application with hot-reloading."""
    if args is None:
        args = []

    # Base command for running the dev server
    cmd = [
        "gradio",
        "app/main.py",
    ]

    # Add any additional arguments
    cmd.extend(args)

    # Run the command
    subprocess.run(cmd)


def check_couchdb_running():
    """Check if CouchDB container is running using docker-compose."""
    try:
        # First check if container exists and is running
        result = subprocess.run(
            ["docker-compose", "ps", "couchdb"],
            capture_output=True,
            text=True,
            timeout=5,
        )

        # Check if container exists and is running
        if "couchdb" not in result.stdout:
            print("CouchDB container not found")
            return False

        # Check if container is healthy
        health_result = subprocess.run(
            [
                "docker",
                "inspect",
                "-f",
                "{{.State.Health.Status}}",
                "formava_ai_trainer_couchdb",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )

        is_healthy = health_result.stdout.strip() == "healthy"
        if not is_healthy:
            print(f"CouchDB health status: {health_result.stdout.strip()}")

        return is_healthy

    except subprocess.TimeoutExpired:
        print("Timeout checking CouchDB container status")
        return False
    except subprocess.CalledProcessError as e:
        print(f"Error checking CouchDB status: {e}")
        return False


def check_couchdb_exists():
    """Check if CouchDB container exists (running or stopped) using docker-compose."""
    try:
        result = subprocess.run(
            ["docker-compose", "ps", "-a", "couchdb"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return "couchdb" in result.stdout
    except subprocess.TimeoutExpired:
        print("Timeout checking CouchDB container existence")
        return False
    except subprocess.CalledProcessError:
        return False


def inspect_container():
    """Inspect the CouchDB container for debugging."""
    try:
        result = subprocess.run(
            ["docker", "inspect", "formava_ai_trainer_couchdb"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        print("\nContainer inspection:")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error inspecting container: {e}")


def check_container_logs():
    """Check the CouchDB container logs for debugging."""
    try:
        result = subprocess.run(
            ["docker", "logs", "formava_ai_trainer_couchdb"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        print("\nContainer logs:")
        print(result.stdout)
    except subprocess.CalledProcessError as e:
        print(f"Error checking container logs: {e}")


def stop_couchdb():
    """Stop and remove the CouchDB container."""
    print("Stopping and removing existing CouchDB container...")
    try:
        # First try docker-compose down
        subprocess.run(
            ["docker-compose", "down", "couchdb"],
            check=True,
            capture_output=True,
        )
        time.sleep(2)  # Give Docker time to clean up
    except subprocess.CalledProcessError as e:
        print(f"Error stopping CouchDB container: {e}")
        print("Attempting to force remove...")
        try:
            # Try to remove the container directly
            subprocess.run(
                ["docker", "rm", "-f", "formava_ai_trainer_couchdb"],
                check=True,
                capture_output=True,
            )
            # Also try to remove the volume
            subprocess.run(
                ["docker", "volume", "rm", "formava_ai_trainer_couchdb_data"],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"Error force removing container/volume: {e}")


def wait_for_couchdb(max_retries=30, retry_interval=2):
    """Wait for CouchDB to be ready and healthy."""
    print("Waiting for CouchDB to be ready...")
    for i in range(max_retries):
        if check_couchdb_running():
            print("CouchDB is ready and healthy!")
            return True

        # If we're past the first few attempts, show more debug info
        if i > 2:
            print(f"\nAttempt {i+1}/{max_retries} - Checking container status...")
            inspect_container()
            check_container_logs()

        print(f"Waiting for CouchDB to be ready... (attempt {i+1}/{max_retries})")
        time.sleep(retry_interval)

    print("\nCouchDB failed to become healthy within the timeout period")
    return False


def start_couchdb():
    """Start CouchDB container using docker-compose if not already running."""
    COUCHDB_PORT = 5984

    # Check if port is in use
    if is_port_in_use(COUCHDB_PORT):
        print(
            f"Port {COUCHDB_PORT} is already in use. Checking if it's our CouchDB instance..."
        )
        if check_couchdb_running():
            print("CouchDB is already running and healthy.")
            return
        else:
            print(
                "Port is in use by another process. Attempting to stop and restart CouchDB..."
            )
            stop_couchdb()

    if not check_couchdb_running():
        print("Starting CouchDB container using docker-compose...")
        try:
            # First ensure any existing container is stopped
            stop_couchdb()

            # Start the container
            subprocess.run(
                ["docker-compose", "up", "-d", "couchdb"],
                check=True,
            )

            # Wait for CouchDB to be ready
            if not wait_for_couchdb():
                raise Exception(
                    "CouchDB failed to become healthy within the timeout period"
                )

        except subprocess.CalledProcessError as e:
            print(f"Error starting CouchDB container: {e}")
            print("Attempting to recover...")
            stop_couchdb()
            raise
        except Exception as e:
            print(f"Unexpected error: {e}")
            stop_couchdb()
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
    try:
        start_couchdb()
    except Exception as e:
        print(f"Failed to start CouchDB: {e}")
        print("Please ensure no other service is using port 5984 and try again.")
        return

    # Run the Gradio app
    run_gradio()


if __name__ == "__main__":
    # Get any additional arguments passed to the script
    args = sys.argv[1:]
    main()
