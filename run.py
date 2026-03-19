"""
Intent Engine - Entry Point

This script serves as the main entry point for the Intent Engine application
after its transition to a structured package format.
"""

import sys
import os

# Add the current directory to sys.path to ensure 'app' can be imported
sys.path.append(os.path.abspath(os.path.dirname(__file__)))


def run_api():
    """Run the FastAPI server."""
    import uvicorn

    uvicorn.run("app.main_api:app", host="0.0.0.0", port=8000, reload=True)


def run_worker():
    """Run the background worker."""
    # arq worker.WorkerSettings
    # arq usually expects a command line call, but we can wrap it if needed
    print("To run the worker, use: arq app.worker.WorkerSettings")


def run_cli():
    """Run the CLI interface."""
    from app.main import main

    main()


if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1]
        if command == "api":
            run_api()
        elif command == "worker":
            run_worker()
        elif command == "cli":
            sys.argv.pop(1)
            run_cli()
        else:
            print(f"Unknown command: {command}")
            print("Usage: python run.py [api|worker|cli]")
    else:
        run_api()
