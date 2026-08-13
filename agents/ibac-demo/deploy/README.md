# Deploy ibac-demo

All paths below are relative to the **`agents/ibac-demo`** directory in this repo (the folder that contains `src/`, `deploy/`, and `README.md`).

| Guide | Use when |
|-------|----------|
| **[Kubernetes (Helm)](k8s/README.md)** | Rancher Desktop, K3s, or any cluster: images, Helm, Acuvity CA, port-forward, updates, troubleshooting |
| **[Docker Compose](compose/README.md)** | Optional local rehearsal without Kubernetes (three containers: MCP, agent, UI) |

The **canonical full checklist** for getting the app running in-cluster is in **[k8s/README.md](k8s/README.md#full-procedure-first-install)** (section **Full procedure: first install**).

**Helm helper:** [k8s/deploy-ibac-demo.sh](k8s/deploy-ibac-demo.sh) installs the release; [k8s/deploy.sh](k8s/deploy.sh) is a thin wrapper around it for the same naming convention as **langgraph** and **google_adk** (`deploy/k8s/deploy.sh`).

**New here?** Open **[k8s/README.md](k8s/README.md)**, use the **Contents** table, and follow **steps 1 through 8** in order. Use **[compose/README.md](compose/README.md)** only if you want Docker Compose on one machine (optional). For local Python or chat UI without Kubernetes, use the root **[README.md](../README.md)** (**Start here** and **Interactive UI**).
