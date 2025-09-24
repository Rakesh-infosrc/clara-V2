#!/usr/bin/env python3
"""
Virtual Receptionist - Main Entry Point
Clara AI Assistant with wake/sleep functionality
"""

import sys
import os
from pathlib import Path

# Add src directory to Python path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

# Import the agent module
from agent import cli, WorkerOptions, entrypoint

def main():
    """Main function to run Clara Virtual Receptionist"""
    print("🤖 Starting Clara Virtual Receptionist...")
    print("📁 Project structure organized")
    print("🎯 Clara is ready with wake/sleep functionality")
    print("💬 Say 'Hey Clara' to wake up or 'Go idle' to sleep")
    print("-" * 50)
    
    # Run the LiveKit agent
    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )

if __name__ == "__main__":
    main()