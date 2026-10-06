"""Run the Gateway API locally with dev-only keys (never use these anywhere else).

Console dev build reads VITE_API_KEY=dev-public-key from apps/console/.env.development.
"""

import os
from pathlib import Path

import uvicorn

os.environ.setdefault("ASG_API_KEYS", "dev:dev-project-key:project,devadmin:dev-admin-key:admin")
os.environ.setdefault("ASG_PUBLIC_KEY", "dev-public-key")
os.environ.setdefault("ASG_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
os.environ.setdefault("ASG_PUBLIC_RATE_LIMIT_PER_MIN", "120")
# Own database: evaluation runs write to data/asg.db and would otherwise spend the demo agent's daily judge budget.
os.environ.setdefault("ASG_DB_PATH", str(Path(__file__).resolve().parents[1] / "data" / "dev-gateway.db"))

if __name__ == "__main__":
    uvicorn.run("asg_gateway.app:app", host="127.0.0.1", port=int(os.environ.get("PORT") or "8000"), log_level="warning")
