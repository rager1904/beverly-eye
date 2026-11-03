# Docker-free Google Colab test environment

Open [UbuntuCare in Colab](https://colab.research.google.com/github/rager1904/beverly-eye/blob/main/docs/colab/UbuntuCare_Online_Smoke_Test.ipynb) and run the cells in order. No existing public URL and no local Docker installation are required. The default launcher now runs Linux processes directly inside the Colab VM; read-only cgroups no longer block the application.

## Launch sequence

1. Clone the source and create `ColabRuntime`.
2. Install native PostgreSQL/pgvector, Redis, Java, Node, Python dependencies, Keycloak, Qdrant, Neo4j, MinIO (compiled from its official tagged source), Ollama and cloudflared. Dependencies are separate from the notebook kernel. Build the frontend. First setup may take 15–30+ minutes.
3. Apply migrations and provision authentication; start all 15 application entrypoints, the gateway, Celery worker/scheduler, and frontend. Wait for readiness and verify both demo accounts through the frontend.
4. Create a Cloudflare Quick Tunnel from the Colab VM, verify public login, and display a clickable temporary URL. No URL input prompt is used.
5. Run the read-only API checks. Optional synthetic writes remain off by default. Set `STOP_DEMO = True` in the final cell to stop only launcher-owned subprocesses.

Doctor email: `john.mwamba@uh.gov.zm`. Admin email: `admin@ubuntucare.gov.zm`. Shared **synthetic-demo-only** password: `UbuntuCare2024!`. Anyone with the public link and these known credentials can access the demo. Never upload real patient data. The generated database, auth-administration and storage secrets remain private to the runtime; logs can contain those secrets and must not be shared.

## Included and excluded

The runtime starts PostgreSQL, Redis, Keycloak, Qdrant, Neo4j, MinIO, Ollama (`qwen2.5:1.5b`), gateway, EMR/patient flow, hospital, appointments, telemedicine, laboratory, pharmacy, surveillance, community health, supply chain, imaging, notifications, agents, tiny CPU Whisper ASR, TTS, RAG, worker, scheduler and frontend. Native services bind only to loopback; only frontend HTTP is tunneled. Email/password login is supported; public Keycloak SSO is not configured.

Starting a process is **not feature completion**. Laboratory, pharmacy and imaging currently expose health-only shells. External messaging, DHIS2, NHIMA and other provider integrations require credentials/configuration. The scheduler enqueues only tasks registered in this repository; unfinished task names are omitted. TTS uses external Edge/Google providers and currently has an audible-tone fallback, so an HTTP health response does not prove speech synthesis. Small models are suitable for functional testing, not medical accuracy evaluation.

Production-only ELK, Grafana, Prometheus, Portainer and Nginx are excluded. Weaviate is excluded because Qdrant is the selected vector backend. The entire production Compose stack is not a realistic single Colab workload.

## Resources, reruns and failures

At least 10 GiB RAM and 25 GiB free disk are required; more memory is preferable. Colab resources are variable, downloads can fail, and runtimes are temporary. See [Colab resource limits](https://research.google.com/colaboratory/faq.html#resource-limits). This is a temporary development experiment, not commercial hosting; it does not evade Colab limits or keep sessions alive.

Keep the same notebook kernel/runtime object for reruns. Startup refuses occupied ports belonging to another launcher. Inspect `runtime.status()` and the named private log under `/content/ubuntucare-native/logs/` when startup fails. If a kernel restart loses subprocess ownership, use a fresh Colab runtime. Runtime files and data are lost when Colab deletes the VM. No local-computer process is required or managed.

The earlier `docker-compose.colab.yml` is retained as a legacy Linux VM override; the notebook does not use it.

## Validation

`python -m unittest discover -s tests/unit -p test_colab_notebook.py -v` checks notebook syntax, no-URL-input flow, process ownership, early failure handling, archive safety, service ports/imports and the migration chain. These are offline regression checks; they do not establish live Colab/model functionality.
