#!/usr/bin/env bash
# Wrapper for parity with langgraph / google_adk (they use deploy/k8s/deploy.sh).
# All behavior lives in deploy-ibac-demo.sh; same usage and environment variables.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec "${SCRIPT_DIR}/deploy-ibac-demo.sh" "$@"
