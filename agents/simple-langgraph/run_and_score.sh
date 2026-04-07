#!/bin/bash
# Runs the agent and automatically scores tool call alignment after each run.
#
# What it does:
#   1. Runs run.sh (sets up proxy, validates env vars, runs main.py)
#   2. Captures all output to docs/results.md
#   3. Runs tests/score_results.py to parse tool calls and write docs/scores.md
#
# Usage:
#   bash run_and_score.sh
#
# All env vars from run.sh apply here (ACUVITY_TOKEN, APEX_URL, LLM_PROVIDER, etc.)
# Optional:
#   PROMPTS_TYPE=scenario  (default: scenario)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
RESULTS_FILE="$SCRIPT_DIR/docs/results.md"
PROMPTS_TYPE="${PROMPTS_TYPE:-scenario}"

mkdir -p "$SCRIPT_DIR/docs"

echo "Running agent (output saved to docs/results.md) ..."
echo ""

# Run the agent - capture stdout+stderr to results.md and also show on terminal
bash "$SCRIPT_DIR/run.sh" 2>&1 | tee "$RESULTS_FILE"

echo ""
echo "========================================"
echo "Scoring tool calls from results.md ..."
echo "========================================"
echo ""

cd "$SCRIPT_DIR" && PROMPTS_TYPE="$PROMPTS_TYPE" uv run tests/score_results.py
