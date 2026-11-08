"""Select the backend or frontend process for the shared Railway image."""

from __future__ import annotations

import os
from pathlib import Path
import sys


def main() -> None:
    role = os.environ.get("UBUNTUCARE_RAILWAY_ROLE") or os.environ.get("RAILWAY_SERVICE_NAME")
    if role == "backend":
        os.execv(sys.executable, [sys.executable, "scripts/railway/start_backend.py"])

    if role == "frontend":
        frontend_dir = Path("/app/frontend")
        server = frontend_dir / "server.js"
        if not server.is_file():
            raise RuntimeError("The shared Railway image is missing the Next.js standalone server.")
        os.environ.setdefault("PORT", "3000")
        os.environ.setdefault("HOSTNAME", "0.0.0.0")
        os.chdir(frontend_dir)
        os.execv("/usr/local/bin/node", ["node", str(server)])

    raise RuntimeError(
        "Set UBUNTUCARE_RAILWAY_ROLE to 'backend' or 'frontend' for this service."
    )


if __name__ == "__main__":
    main()
