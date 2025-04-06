#!/usr/bin/env python3
"""
Script to restart the Streamlit service with proper hot reloading settings.
"""

import os
import signal
import subprocess
import sys
import time

import psutil


def find_streamlit_processes():
    """Find all running Streamlit processes."""
    streamlit_processes = []
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            # Check if the process is a Streamlit process
            if "streamlit" in proc.info["name"].lower() or (
                proc.info["cmdline"]
                and "streamlit" in " ".join(proc.info["cmdline"]).lower()
            ):
                streamlit_processes.append(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    return streamlit_processes


def kill_streamlit_processes():
    """Kill all running Streamlit processes."""
    processes = find_streamlit_processes()
    if not processes:
        print("No Streamlit processes found.")
        return

    print(f"Found {len(processes)} Streamlit processes. Terminating...")
    for proc in processes:
        try:
            proc.terminate()
            print(f"Terminated process {proc.info['pid']}")
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            print(f"Could not terminate process {proc.info['pid']}")

    # Wait for processes to terminate
    time.sleep(2)

    # Check if any processes are still running
    remaining = find_streamlit_processes()
    if remaining:
        print(f"{len(remaining)} processes still running. Force killing...")
        for proc in remaining:
            try:
                proc.kill()
                print(f"Killed process {proc.info['pid']}")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                print(f"Could not kill process {proc.info['pid']}")


def start_streamlit():
    """Start Streamlit with hot reloading enabled."""
    print("Starting Streamlit with hot reloading enabled...")

    # Command to run Streamlit with hot reloading
    cmd = [
        "streamlit",
        "run",
        "app.py",
        "--server.runOnSave=true",
        "--server.fileWatcherType=watchdog",
        "--logger.level=debug",
    ]

    # Start the process
    process = subprocess.Popen(cmd)
    print(f"Started Streamlit with PID {process.pid}")
    return process


def main():
    """Main function to restart Streamlit."""
    print("Restarting Streamlit service...")

    # Kill existing Streamlit processes
    kill_streamlit_processes()

    # Start a new Streamlit process
    process = start_streamlit()

    print("Streamlit restarted successfully!")
    print("Press Ctrl+C to stop the service.")

    try:
        # Keep the script running
        process.wait()
    except KeyboardInterrupt:
        print("\nStopping Streamlit...")
        process.terminate()
        process.wait()
        print("Streamlit stopped.")


if __name__ == "__main__":
    main()
