# backend/scripts/export_openapi.py
import json
import os
import sys

# Add backend directory to path so imports work correctly
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.openapi.utils import get_openapi
from app.main import app

def export_schema():
    """Step 13.2: Export static OpenAPI JSON for frontend ingestion."""
    docs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "docs")
    os.makedirs(docs_dir, exist_ok=True)
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        openapi_version=app.openapi_version,
        description=app.description,
        routes=app.routes,
    )
    
    output_path = os.path.join(docs_dir, "openapi.json")
    with open(output_path, "w") as f:
        json.dump(openapi_schema, f, indent=2)
        
    print(f"Successfully exported OpenAPI schema to {output_path}")

if __name__ == "__main__":
    # Disable background Redis task looping to allow clean script termination
    os.environ["DISABLE_BACKGROUND_TASKS"] = "1"
    export_schema()