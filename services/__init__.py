"""Service package.

Intentionally avoids re-exporting concrete services to prevent eager import chains
that can trigger circular imports in packaged builds.
"""
