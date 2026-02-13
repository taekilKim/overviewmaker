try:
    # Vercel/package import path
    from .generate import app
except Exception:
    # Local fallback
    from generate import app
