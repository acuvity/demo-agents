# Deploy ibac-demo

All paths below are relative to the **`agents/ibac-demo`** directory in this repo (the folder that contains `src/`, `deploy/`, and `README.md`).

| Guide | Use when |
|-------|----------|
| **[Kubernetes (Helm)](k8s/README.md)** | Rancher Desktop, K3s, or any cluster: images, Helm, Acuvity CA, port-forward, updates, troubleshooting |
| **[Docker Compose](compose/README.md)** | Optional local rehearsal without Kubernetes (three containers: MCP, agent, UI) |

The **canonical full checklist** for getting the app running in-cluster is in **[k8s/README.md](k8s/README.md#full-procedure-first-install)** (section **Full procedure: first install**).
