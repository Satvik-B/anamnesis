# MemoryBench

Automated evaluation and optimization of memory-rule.md, inspired by
[autoresearch](https://github.com/karpathy/autoresearch).

## How it works

```
┌─────────────────────────────────────────────────────────┐
│                   OPTIMIZATION LOOP                     │
│                                                         │
│  1. Agent reads current memory-rule.md + past results   │
│  2. Agent proposes a modification                       │
│  3. Eval runs 5 coding sessions with fresh memory       │
│     - S1: Setup → S2: Feature → S3: Debug →             │
│       S4: Reuse → S5: Retrieval                         │
│     - Memory accumulates across sessions                │
│  4. Score = retrieval_accuracy / log2(total_tokens)     │
│  5. Keep if score improved, discard if not              │
│  6. Repeat                                              │
└─────────────────────────────────────────────────────────┘
```

## Quick start

### 1. Install dependencies

```bash
cd ~/self-work/anamnesis
pip install anthropic
```

### 2. Set API key

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
```

### 3. Create baseline rule

```bash
cp src/anamnesis/skeleton/rules/memory-rule.md eval/baseline_rule.md
```

### 4. Run a single eval (test your setup)

```bash
cd eval
python run_eval.py --rule baseline_rule.md --verbose
```

This runs 5 sessions, shows responses, and prints scores. Takes ~2-3 minutes
and costs ~$0.50-1.00 in API credits (depends on model).

### 5. Run the optimization loop

```bash
python optimize.py --iterations 10
```

This will:
- Evaluate the baseline first (iteration 0)
- Run 10 optimization iterations
- Each iteration: propose change → eval → keep/discard
- Save results to `results.tsv` and snapshots to `history/`

For overnight runs:

```bash
nohup python optimize.py --iterations 50 > optimize.log 2>&1 &
```

## Files

| File | Description |
|------|-------------|
| `run_eval.py` | Runs 5 sessions, scores checkpoints, reports results |
| `optimize.py` | Outer loop: modify rule → eval → keep/discard |
| `checkpoints.py` | 11 assertion functions that test memory retrieval |
| `program.md` | Instructions for the optimization agent |
| `baseline_rule.md` | Starting memory-rule.md (copy from skeleton) |
| `current_rule.md` | Best rule so far (auto-managed by optimizer) |
| `results.tsv` | Experiment log (iteration, score, tokens, kept) |
| `sessions/` | 5 scripted eval sessions |
| `history/` | Snapshot of every attempted rule + results JSON |

## Models

| Model | Speed | Cost per eval | Best for |
|-------|-------|---------------|----------|
| `claude-sonnet-4-6` | ~2 min | ~$0.50 | Default, fast iteration |
| `claude-opus-4-6` | ~5 min | ~$3.00 | Higher quality, final runs |
| `claude-haiku-4-5` | ~1 min | ~$0.10 | Quick sanity checks |

Override with `--model`:

```bash
python optimize.py --model claude-opus-4-6 --iterations 5
```

## Cost estimate

| Iterations | Model | Time | Cost |
|-----------|-------|------|------|
| 1 (single eval) | Sonnet | 2-3 min | ~$0.50 |
| 10 | Sonnet | 30-40 min | ~$7 |
| 50 (overnight) | Sonnet | 3-4 hours | ~$35 |
| 10 | Opus | 1 hour | ~$35 |

## Interpreting results

```
MEMORYBENCH RESULTS
=================================
Retrieval accuracy:  72.7%       ← 8/11 checkpoints passed
Total tokens:        28,432      ← across all 5 sessions
Composite score:     0.049123    ← accuracy / log2(tokens)
```

- **Retrieval accuracy** is the primary signal — is memory actually helping?
- **Total tokens** penalizes bloated rules/memories
- **Composite score** balances both — this is what the optimizer maximizes

## Adding new sessions or checkpoints

1. Add a session file in `sessions/` following the naming convention
2. Add checkpoint functions in `checkpoints.py`
3. Register them in the `CHECKPOINTS` dict
