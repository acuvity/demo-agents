# tests/

Local scoring scripts that measure intent-action alignment for each tool call
made by the agent. These are independent of the Acuvity Gateway - they run
entirely offline using HuggingFace cross-encoder models.

## Files

| File | Purpose |
|------|---------|
| `score_results.py` | Parses `docs/results.md`, scores each tool call, writes `docs/scores.md` |
| `intent_score.py` | Hardcoded scenario cases from `results.md` - useful for quick spot-checks |
| `model_comparison.py` | Scores the same cases across 5 public cross-encoder models, writes `docs/model_comparison.md` |

## How scoring works

Each tool call the agent makes is scored as a `(context, action)` pair:

- **context** - the full user prompt (loaded from `prompt-scenarios/advanced-prompts.txt`)
- **action** - `[TOOL] name\n[ARGS] {...}\n[DESC] description` (same format used in production)

The cross-encoder outputs a score in `[0, 1]`:
- `> 0.5` - action appears aligned with user intent
- `< 0.5` - action appears misaligned (potential injection or attack)

## Running after each agent run

Use `run_and_score.sh` at the project root - it runs the agent and scores automatically:

```bash
bash run_and_score.sh
```

This overwrites `docs/results.md` with fresh agent output and regenerates
`docs/scores.md` with alignment scores.

## Running the scorer standalone

If you already have a `docs/results.md` and just want to re-score:

```bash
uv run tests/score_results.py
# or with a different prompts type
uv run tests/score_results.py --prompts-type scenario
```

## Running spot-checks

To score specific hardcoded cases without needing a fresh run:

```bash
uv run tests/intent_score.py
```

## Running the model comparison

Scores the same cases across 5 public cross-encoder models and writes a
comparison table to `docs/model_comparison.md`. Models are downloaded on
first run (~130 MB to ~570 MB each) and cached locally.

```bash
uv run tests/model_comparison.py
```

## Notes

- All scripts use `transformers` + `torch` only - no Acuvity dependencies.
- The default scoring model is `cross-encoder/ms-marco-MiniLM-L-12-v2` (~130 MB, no auth).
- `score_results.py` and `intent_score.py` support swapping in `acuvity/intent-action`
  (purpose-trained for this format) by changing `MODEL_ID` at the top of each file.
  That model requires a HuggingFace token with access to the `acuvity` org.
