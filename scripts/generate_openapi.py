#!/usr/bin/env python
"""
Generate OpenAPI schema from FastAPI app and save to docs/swagger.json
"""

import json
import sys
from pathlib import Path

# Add repo root to path so we can import src
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

from src.api.server import app

def generate_openapi():
    """Generate OpenAPI schema from FastAPI app."""
    openapi_schema = app.openapi()
    
    # Add servers configuration
    openapi_schema["servers"] = [
        {
            "url": "https://vahan-rakshak.onrender.com",
            "description": "Production server (Render)"
        },
        {
            "url": "http://localhost:8000",
            "description": "Local development server"
        }
    ]
    
    # Pretty print with 2-space indentation
    openapi_json = json.dumps(openapi_schema, indent=2)
    
    # Write to docs/swagger.json
    swagger_path = repo_root / "docs" / "swagger.json"
    swagger_path.parent.mkdir(parents=True, exist_ok=True)
    
    with swagger_path.open("w", encoding="utf-8") as f:
        f.write(openapi_json)
    
    print(f"✓ OpenAPI schema generated successfully")
    print(f"  Location: {swagger_path}")
    print(f"  Size: {len(openapi_json)} bytes")
    print(f"  Endpoints: {len(openapi_schema.get('paths', {}))} paths documented")
    
    return swagger_path

if __name__ == "__main__":
    try:
        swagger_path = generate_openapi()
        print(f"\n✓ Schema saved to: {swagger_path}")
        print(f"  View at: http://localhost:8000/docs")
    except Exception as e:
        print(f"✗ Failed to generate OpenAPI schema: {e}")
        sys.exit(1)
