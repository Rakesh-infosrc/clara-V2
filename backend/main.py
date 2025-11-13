#!/usr/bin/env python3
"""
Virtual Receptionist - Main Entry Point
Clara AI Assistant with wake/sleep functionality
"""
def main():
    """Main function to run Clara Virtual Receptionist"""
    print("🤖 Starting Clara Virtual Receptionist...")
    print("📁 Project structure organized")
    print("🎯 Clara is ready with wake/sleep functionality")
    print("💬 Say 'Hey Clara' to wake up or 'Go idle' to sleep")
    print("-" * 50)
    
    # Run the LiveKit agent
    import sys
    from pathlib import Path

    src_dir = Path(__file__).parent / "src"
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from src.agent import cli, WorkerOptions, entrypoint

    cli.run_app(
        WorkerOptions(
            entrypoint_fnc=entrypoint,
        )
    )

if __name__ == "__main__":
    main()