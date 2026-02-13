"""Compatibility entrypoint.

This project now uses FastAPI + web UI.
Any platform looking for `app.py:app` should load the FastAPI app.
"""

try:
    from api.generate import app
except Exception:
    from generate import app
