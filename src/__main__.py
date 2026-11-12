"""
Package entry point — enables ``python -m src``.

Delegates unconditionally to ``src.cli.main()``.  All argument parsing,
validation, and dispatch live in ``cli.py``; this file is intentionally
kept to a single function call.
"""

from src.cli import main

if __name__ == "__main__":
    main()