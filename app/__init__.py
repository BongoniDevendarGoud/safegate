"""
SafeGate Application Package
=============================
This is the root package for SafeGate: a self-hosted, fail-closed AI upload gateway.

Sub-packages:
    models/   - SQLAlchemy ORM database models and Pydantic request/response schemas
    pipeline/ - The ordered screening stages (intake, hashing, frames, NSFW, Gemini, deepfake, decision)
    routes/   - FastAPI route controllers for uploads, dashboard moderation, and audit verification
    security/ - Security hardening, API key authentication, rate limiting, and CORS headers
"""
__version__ = "0.1.0"
