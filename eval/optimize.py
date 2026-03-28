"""MemoryBench Optimizer: autoresearch-style loop for memory-rule.md.

Repeatedly modifies memory-rule.md, evaluates, and keeps improvements.
Inspired by https://github.com/karpathy/autoresearch

Usage:
    python eval/optimize.py                          # run optimization loop
    python eval/optimize.py --iterations 20          # run 20 iterations
    python eval/optimize.py --model claude-sonnet-4-6 # use specific model
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
import time
from datetime import datetime
from pathlib import Path

import anthropic

from run_eval import run_eval, print_summary

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EVAL_DIR = Path(__file__).parent
BASELINE_RULE = EVAL_DIR / "baseline_rule.md"
CURRENT_RULE = EVAL_DIR / "current_rule.md"
RESULTS_TSV = EVAL_DIR / "results.tsv"
HISTORY_DIR = EVAL_DIR / "history"
PROGRAM_MD = EVAL_DIR / "program.md"
DEFAULT_MODEL = "claude-sonnet-4-6"


# ---------------------------------------------------------------------------
# Optimization agent
# ---------------------------------------------------------------------------

def propose_modification(
    client: anthropic.Anthropic,
    model: str,
    current_rule: str,
    past_results: list[dict],
) -> str:
    """Ask Claude to propose a modification to memory-rule.md.

    Returns the full modified memory-rule.md content.
    """
    # Build context from past results
    history_text = "No prior experiments yet." if not past_results else ""
    for r in past_results[-10:]:  # last 10 results
        kept = "KEPT" if r.get("kept") else "DISCARDED"
        history_text += (
            f"\nIteration {r['iteration']} [{kept}]: "
            f"accuracy={r['retrieval_accuracy']:.1%}, "
            f"tokens={r['total_tokens']:,}, "
            f"composite={r['composite_score']:.6f}, "
            f"memories={r['total_memories']}, "
            f"change=\"{r.get('change_summary', 'N/A')}\""
        )

    program = PROGRAM_MD.read_text() if PROGRAM_MD.exists() else ""

    system = (
        "You are an optimization agent for a memory system used by AI coding assistants. "
        "Your job is to modify a memory-rule.md file to improve how effectively the AI "
        "saves and retrieves memories across coding sessions.\n\n"
        "The metric is: retrieval_accuracy / log2(total_tokens)\n"
        "- retrieval_accuracy: fraction of checkpoints passed (does Claude recall prior knowledge?)\n"
        "- total_tokens: sum across 5 sessions (lower is better)\n"
        "- Composite score: higher is better\n\n"
        "You want Claude to:\n"
        "1. Save the RIGHT things (architectural decisions, gotchas, failure patterns)\n"
        "2. Retrieve them effectively in later sessions\n"
        "3. Not waste tokens on unnecessary context\n\n"
        f"{program}"
    )

    user = (
        f"## Current memory-rule.md\n\n```markdown\n{current_rule}\n```\n\n"
        f"## Past experiment results\n{history_text}\n\n"
        "## Your task\n\n"
        "Propose a modification to memory-rule.md that should improve the composite score. "
        "Think about:\n"
        "- Are the save triggers too aggressive (saving noise) or too passive (missing key info)?\n"
        "- Is the retrieval guidance clear enough? Does Claude know WHEN to check memories?\n"
        "- Is the format/structure helping or hurting retrieval?\n"
        "- Are there redundant sections that waste context tokens?\n\n"
        "Return ONLY the complete modified memory-rule.md content (no explanation, no code fences). "
        "Also include a one-line comment at the very top starting with '<!-- CHANGE: ' describing "
        "what you modified and why, e.g.:\n"
        "<!-- CHANGE: Added explicit 'check memories before responding' instruction to improve retrieval -->\n"
    )

    response = client.messages.create(
        model=model,
        max_tokens=8192,
        system=system,
        messages=[{"role": "user", "content": user}],
    )

    return response.content[0].text


def extract_change_summary(rule_content: str) -> str:
    """Extract the <!-- CHANGE: ... --> comment from the rule."""
    for line in rule_content.splitlines():
        if line.strip().startswith("<!-- CHANGE:"):
            return line.strip().removeprefix("<!-- CHANGE:").removesuffix("-->").strip()
    return "No change description"


# ---------------------------------------------------------------------------
# Results logging
# ---------------------------------------------------------------------------

def init_results_tsv():
    """Create results.tsv with headers if it doesn't exist."""
    if not RESULTS_TSV.exists():
        with open(RESULTS_TSV, "w", newline="") as f:
            writer = csv.writer(f, delimiter="\t")
            writer.writerow([
                "iteration", "timestamp", "retrieval_accuracy",
                "total_tokens", "composite_score", "total_memories",
                "kept", "change_summary",
            ])


def append_result(iteration: int, results: dict, kept: bool, change_summary: str):
    """Append a row to results.tsv."""
    with open(RESULTS_TSV, "a", newline="") as f:
        writer = csv.writer(f, delimiter="\t")
        writer.writerow([
            iteration,
            datetime.now().isoformat(timespec="seconds"),
            f"{results['retrieval_accuracy']:.4f}",
            results["total_tokens"],
            f"{results['composite_score']:.6f}",
            results["total_memories"],
            kept,
            change_summary,
        ])


def load_past_results() -> list[dict]:
    """Load past results from results.tsv."""
    if not RESULTS_TSV.exists():
        return []

    results = []
    with open(RESULTS_TSV) as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            results.append({
                "iteration": int(row["iteration"]),
                "retrieval_accuracy": float(row["retrieval_accuracy"]),
                "total_tokens": int(row["total_tokens"]),
                "composite_score": float(row["composite_score"]),
                "total_memories": int(row["total_memories"]),
                "kept": row["kept"] == "True",
                "change_summary": row["change_summary"],
            })
    return results


# ---------------------------------------------------------------------------
# Main optimization loop
# ---------------------------------------------------------------------------

def run_optimization(
    iterations: int = 10,
    model: str = DEFAULT_MODEL,
    verbose: bool = False,
):
    """Run the optimization loop."""
    client = anthropic.Anthropic()

    # Ensure directories exist
    HISTORY_DIR.mkdir(exist_ok=True)
    init_results_tsv()

    # Initialize with baseline if no current rule exists
    if not CURRENT_RULE.exists():
        if not BASELINE_RULE.exists():
            print("Error: No baseline_rule.md found. Copy your memory-rule.md:")
            print(f"  cp src/anamnesis/skeleton/rules/memory-rule.md {BASELINE_RULE}")
            return 1
        shutil.copy(BASELINE_RULE, CURRENT_RULE)

    past_results = load_past_results()
    start_iteration = len(past_results) + 1
    best_score = max((r["composite_score"] for r in past_results), default=0.0)

    print(f"MemoryBench Optimizer")
    print(f"Model: {model}")
    print(f"Starting iteration: {start_iteration}")
    print(f"Best score so far: {best_score:.6f}")
    print(f"Planned iterations: {iterations}")
    print()

    # If this is the first run, evaluate the baseline first
    if start_iteration == 1:
        print("=" * 60)
        print("BASELINE EVAL (iteration 0)")
        print("=" * 60)

        baseline_results = run_eval(CURRENT_RULE, model, verbose)
        print_summary(baseline_results)

        best_score = baseline_results["composite_score"]
        append_result(0, baseline_results, True, "baseline")

        # Save baseline snapshot
        shutil.copy(CURRENT_RULE, HISTORY_DIR / "iter_000_baseline.md")

        past_results = load_past_results()
        start_iteration = 1

    for i in range(start_iteration, start_iteration + iterations):
        print(f"\n{'='*60}")
        print(f"ITERATION {i}")
        print(f"{'='*60}")

        # 1. Propose modification
        print("Proposing modification...")
        current_content = CURRENT_RULE.read_text()
        proposed = propose_modification(client, model, current_content, past_results)
        change_summary = extract_change_summary(proposed)
        print(f"Change: {change_summary}")

        # Save proposed rule temporarily
        proposed_path = EVAL_DIR / "proposed_rule.md"
        proposed_path.write_text(proposed)

        # 2. Evaluate
        print("Evaluating...")
        try:
            results = run_eval(proposed_path, model, verbose)
        except Exception as e:
            print(f"Eval failed: {e}")
            append_result(i, {
                "retrieval_accuracy": 0, "total_tokens": 0,
                "composite_score": 0, "total_memories": 0,
            }, False, f"EVAL FAILED: {e}")
            continue

        print_summary(results)

        # 3. Keep or discard
        new_score = results["composite_score"]
        kept = new_score > best_score

        if kept:
            print(f"\n>>> KEEPING: {new_score:.6f} > {best_score:.6f} (+{new_score - best_score:.6f})")
            best_score = new_score
            shutil.copy(proposed_path, CURRENT_RULE)
        else:
            print(f"\n>>> DISCARDING: {new_score:.6f} <= {best_score:.6f}")

        # 4. Log
        append_result(i, results, kept, change_summary)

        # Save snapshot
        iter_label = f"iter_{i:03d}_{'kept' if kept else 'discarded'}"
        shutil.copy(proposed_path, HISTORY_DIR / f"{iter_label}.md")

        # Save full results JSON
        output = {k: v for k, v in results.items() if k != "sessions"}
        output["sessions"] = [
            {k: v for k, v in s.items() if k != "response"}
            for s in results["sessions"]
        ]
        (HISTORY_DIR / f"{iter_label}.json").write_text(json.dumps(output, indent=2))

        # Clean up
        proposed_path.unlink(missing_ok=True)

        past_results = load_past_results()

        print(f"\nBest score: {best_score:.6f}")

    print(f"\n{'='*60}")
    print("OPTIMIZATION COMPLETE")
    print(f"{'='*60}")
    print(f"Best composite score: {best_score:.6f}")
    print(f"Best rule saved at: {CURRENT_RULE}")
    print(f"Full history at: {HISTORY_DIR}/")
    print(f"Results log: {RESULTS_TSV}")

    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="MemoryBench Optimizer: autoresearch-style loop for memory-rule.md"
    )
    parser.add_argument("--iterations", type=int, default=10,
                        help="Number of optimization iterations (default: 10)")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Claude model (default: {DEFAULT_MODEL})")
    parser.add_argument("--verbose", action="store_true",
                        help="Show full session responses")

    args = parser.parse_args()
    return run_optimization(args.iterations, args.model, args.verbose)


if __name__ == "__main__":
    sys.exit(main())
