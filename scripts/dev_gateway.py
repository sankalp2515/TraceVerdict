"""Run the Gateway API locally with dev-only keys (never use these anywhere else).

Console dev build reads VITE_API_KEY=dev-public-key from apps/console/.env.development.
"""

import os

import uvicorn

os.environ.setdefault("ASG_API_KEYS", "dev:dev-project-key:project,devadmin:dev-admin-key:admin")
os.environ.setdefault("ASG_PUBLIC_KEY", "dev-public-key")
os.environ.setdefault("ASG_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
os.environ.setdefault("ASG_PUBLIC_RATE_LIMIT_PER_MIN", "120")

if __name__ == "__main__":
    uvicorn.run("asg_gateway.app:app", host="127.0.0.1", port=int(os.environ.get("PORT", "8000")), log_level="warning")
