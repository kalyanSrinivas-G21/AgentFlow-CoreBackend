# backend/app/tools/__init__.py
from app.tools.base import init_tools

# Auto-initialize tools when the tools package is imported.
# This ensures Pytest and the PolicyEngine always have access to the 
# populated registry without needing to boot the FastAPI lifespan.
init_tools()