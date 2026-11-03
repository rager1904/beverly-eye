# Google Colab frontend and online smoke test

Open `UbuntuCare_Online_Smoke_Test.ipynb` in [Google Colab](https://colab.research.google.com/) by uploading the notebook, or from a GitHub-hosted copy use **Open in Colab**.

The notebook automatically clones `https://github.com/rager1904/beverly-eye.git` from `main` into a fresh temporary directory on each run. If the runtime permits containers, it starts only the frontend, API gateway, EMR, PostgreSQL, Redis, Keycloak, and migrations; it does not start the ASR, TTS, RAG, or agent-worker AI services.

Some Colab runtimes mount `/sys/fs/cgroup` read-only. Docker/runc cannot start build containers in that environment, and notebook flags cannot grant the missing host permission. The launcher detects this and stops before building. To test the frontend, run the core Compose stack on a Docker-enabled VM and expose only port 3000 with a tunnel:

```bash
docker compose up -d --build frontend api-gateway emr
cloudflared tunnel --url http://localhost:3000
```

Then skip the local-launch cells in Colab and use the tunnel's public frontend URL in the authenticated checks. Use a test deployment and synthetic data only.

It creates a temporary demo admin account and exposes the frontend with a public Cloudflare Quick Tunnel URL. Use the email/password form (SSO is not configured for the one-tunnel demo). The URL and credentials are printed in notebook output; do not share them or save/share the notebook with outputs. This is for synthetic demo data only, not real patient data or production. Run the final cleanup cell when finished.
