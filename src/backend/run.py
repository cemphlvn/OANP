"""
OANP Backend — Entry point

Usage:
    uv run python run.py
    # or via root package.json:
    npm run backend
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "../.."))

from dotenv import load_dotenv

# Load .env from project root
root_env = os.path.join(os.path.dirname(__file__), "../../.env")
if os.path.exists(root_env):
    load_dotenv(root_env, override=True)


def validate_config():
    """Check that minimum required config is present."""
    errors = []

    has_openai = bool(os.getenv("OPENAI_API_KEY"))
    has_anthropic = bool(os.getenv("ANTHROPIC_API_KEY"))

    if not has_openai and not has_anthropic:
        errors.append(
            "No LLM API key configured. Set OPENAI_API_KEY or ANTHROPIC_API_KEY in .env"
        )

    return errors


def main():
    errors = validate_config()
    if errors:
        print("Configuration errors:")
        for err in errors:
            print(f"  - {err}")
        print("\nCopy .env.example to .env and fill in your API keys:")
        print("  cp .env.example .env")
        sys.exit(1)

    import uvicorn

    host = os.getenv("OANP_HOST", "0.0.0.0")
    port = int(os.getenv("OANP_PORT", "8123"))

    print(f"\n  OANP Backend starting on http://{host}:{port}")
    print(f"  API docs: http://localhost:{port}/docs")
    print(f"  WebSocket: ws://localhost:{port}/ws/{{session_id}}\n")

    uvicorn.run(
        "src.backend.main:app",
        host=host,
        port=port,
        reload=True,
    )


if __name__ == "__main__":
    main()
