# Google Colab frontend and online smoke test

Open `UbuntuCare_Online_Smoke_Test.ipynb` in [Google Colab](https://colab.research.google.com/) by uploading the notebook, or from a GitHub-hosted copy use **Open in Colab**.

The notebook automatically clones `https://github.com/rager1904/beverly-eye.git` from `main` into a fresh temporary directory on each run. It starts only the frontend, API gateway, EMR, PostgreSQL, Redis, Keycloak, and migrations; it does not start the ASR, TTS, RAG, or agent-worker AI services. It uses Docker host networking, host networking for image-build `RUN` steps, and a VFS storage driver to avoid Colab's restricted bridge/iptables setup. If the runtime still denies nested Docker, the notebook prints the relevant `dockerd` or Compose log tail; use a Docker-enabled VM or hosted development environment instead.

It creates a temporary demo admin account and exposes the frontend with a public Cloudflare Quick Tunnel URL. Use the email/password form (SSO is not configured for the one-tunnel demo). The URL and credentials are printed in notebook output; do not share them or save/share the notebook with outputs. This is for synthetic demo data only, not real patient data or production. Run the final cleanup cell when finished.
