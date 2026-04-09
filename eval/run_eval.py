"""MemoryBench: Run a 5-session eval and score memory retrieval.

Usage:
    python eval/run_eval.py                           # use default memory-rule.md
    python eval/run_eval.py --rule path/to/rule.md    # use custom rule
    python eval/run_eval.py --model claude-sonnet-4-6  # pick model
    python eval/run_eval.py --verbose                  # show full responses
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import anthropic

from checkpoints import CHECKPOINTS, score_session, total_score

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SESSIONS_DIR = Path(__file__).parent / "sessions"
DEFAULT_RULE = Path(__file__).parent / "baseline_rule.md"
DEFAULT_MODEL = "claude-sonnet-4-6"
MAX_TOKENS = 4096

# The save_memory tool that Claude can call during sessions
MEMORY_TOOL = {
    "name": "save_memory",
    "description": (
        "Save a memory to the structured memory system. Use this when you "
        "learn something worth remembering for future sessions: architectural "
        "decisions, patterns, gotchas, debugging lessons, conventions."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "filename": {
                "type": "string",
                "description": "Descriptive filename, e.g. 'auth-middleware-pattern.md'",
            },
            "memory_type": {
                "type": "string",
                "enum": ["knowledge", "task", "context", "reflection"],
                "description": "Type of memory",
            },
            "title": {
                "type": "string",
                "description": "Short title for the memory",
            },
            "content": {
                "type": "string",
                "description": "The memory content (markdown)",
            },
            "tags": {
                "type": "array",
                "items": {"type": "string"},
                "description": "Tags for categorization",
            },
        },
        "required": ["filename", "memory_type", "title", "content"],
    },
}


# ---------------------------------------------------------------------------
# Memory store (accumulates across sessions within one eval run)
# ---------------------------------------------------------------------------

class MemoryStore:
    """In-memory store that simulates .claude/memory/ across sessions."""

    def __init__(self):
        self.memories: list[dict] = []

    def save(self, entry: dict) -> str:
        """Save a memory entry. Returns confirmation message."""
        self.memories.append(entry)
        return f"Saved memory: {entry.get('title', 'untitled')} ({entry.get('memory_type', 'unknown')})"

    def format_for_prompt(self) -> str:
        """Format all memories as context for the next session's system prompt."""
        if not self.memories:
            return "No memories saved yet."

        lines = ["# Accumulated Memories\n"]
        for i, mem in enumerate(self.memories, 1):
            lines.append(f"## Memory {i}: {mem.get('title', 'Untitled')}")
            lines.append(f"**Type:** {mem.get('memory_type', 'unknown')}")
            if mem.get("tags"):
                lines.append(f"**Tags:** {', '.join(mem['tags'])}")
            lines.append(f"\n{mem.get('content', '')}\n")
            lines.append("---\n")

        return "\n".join(lines)

    def count(self) -> int:
        return len(self.memories)


# ---------------------------------------------------------------------------
# Session runner
# ---------------------------------------------------------------------------

def build_system_prompt(rule_content: str, memory_store: MemoryStore) -> str:
    """Build the system prompt with memory rule + accumulated memories."""
    parts = [
        "You are a senior software engineer helping build a Flask REST API project.",
        "You have access to a persistent memory system. Use the save_memory tool to "
        "record important decisions, patterns, and lessons learned for future sessions.",
        "",
        "# Memory System Instructions",
        "",
        rule_content,
        "",
        "# Context from Previous Sessions",
        "",
        memory_store.format_for_prompt(),
    ]
    return "\n".join(parts)


def run_session(
    client: anthropic.Anthropic,
    model: str,
    session_num: int,
    rule_content: str,
    memory_store: MemoryStore,
    verbose: bool = False,
) -> dict:
    """Run a single session and return results.

    Returns:
        {
            "session": int,
            "response": str,          # Claude's text response
            "input_tokens": int,
            "output_tokens": int,
            "memories_saved": int,    # memories written this session
            "checkpoints": dict,      # checkpoint_name -> bool
            "duration_s": float,
        }
    """
    # Load session prompt
    session_file = SESSIONS_DIR / f"s{session_num}_{'setup' if session_num == 1 else ['feature', 'debug', 'reuse', 'retrieval'][session_num - 2]}.md"
    user_prompt = session_file.read_text()

    system_prompt = build_system_prompt(rule_content, memory_store)

    if verbose:
        print(f"\n{'='*60}")
        print(f"SESSION {session_num}")
        print(f"{'='*60}")
        print(f"Memories available: {memory_store.count()}")

    start = time.time()
    total_input = 0
    total_output = 0
    full_response = ""
    memories_this_session = 0

    # Conversation loop (handle tool use)
    messages = [{"role": "user", "content": user_prompt}]

    while True:
        response = client.messages.create(
            model=model,
            max_tokens=MAX_TOKENS,
            system=system_prompt,
            tools=[MEMORY_TOOL],
            messages=messages,
        )

        total_input += response.usage.input_tokens
        total_output += response.usage.output_tokens

        # Process response blocks
        tool_results = []
        for block in response.content:
            if block.type == "text":
                full_response += block.text
            elif block.type == "tool_use":
                if block.name == "save_memory":
                    result = memory_store.save(block.input)
                    memories_this_session += 1
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })

        # If no tool use, we're done
        if response.stop_reason != "tool_use":
            break

        # Feed tool results back
        messages.append({"role": "assistant", "content": response.content})
        messages.append({"role": "user", "content": tool_results})

    duration = time.time() - start

    # Score checkpoints
    checkpoint_results = score_session(session_num, full_response)

    if verbose:
        print(f"\nResponse ({len(full_response)} chars):")
        print(full_response[:500] + ("..." if len(full_response) > 500 else ""))
        print(f"\nTokens: {total_input} in / {total_output} out")
        print(f"Memories saved: {memories_this_session}")
        if checkpoint_results:
            print("Checkpoints:")
            for name, passed in checkpoint_results.items():
                status = "PASS" if passed else "FAIL"
                print(f"  [{status}] {name}")

    return {
        "session": session_num,
        "response": full_response,
        "input_tokens": total_input,
        "output_tokens": total_output,
        "memories_saved": memories_this_session,
        "checkpoints": checkpoint_results,
        "duration_s": duration,
    }


# ---------------------------------------------------------------------------
# Full eval run
# ---------------------------------------------------------------------------

def run_eval(
    rule_path: Path,
    model: str = DEFAULT_MODEL,
    verbose: bool = False,
) -> dict:
    """Run all 5 sessions and return aggregate results.

    Returns:
        {
            "rule_path": str,
            "model": str,
            "sessions": [session_result, ...],
            "total_input_tokens": int,
            "total_output_tokens": int,
            "total_tokens": int,
            "total_memories": int,
            "retrieval_accuracy": float,   # 0.0 - 1.0
            "composite_score": float,      # accuracy / log2(tokens)
            "checkpoint_details": dict,
        }
    """
    client = anthropic.Anthropic()
    rule_content = rule_path.read_text()
    memory_store = MemoryStore()

    session_results = []
    all_checkpoints: dict[int, dict[str, bool]] = {}

    for session_num in range(1, 6):
        result = run_session(
            client, model, session_num, rule_content, memory_store, verbose
        )
        session_results.append(result)
        if result["checkpoints"]:
            all_checkpoints[session_num] = result["checkpoints"]

    # Aggregate
    total_input = sum(r["input_tokens"] for r in session_results)
    total_output = sum(r["output_tokens"] for r in session_results)
    total_tokens = total_input + total_output
    total_memories = memory_store.count()
    accuracy = total_score(all_checkpoints)

    # Composite: accuracy / log2(tokens). Higher = better.
    # Guard against 0 tokens (shouldn't happen)
    composite = accuracy / math.log2(total_tokens) if total_tokens > 1 else 0.0

    return {
        "rule_path": str(rule_path),
        "model": model,
        "sessions": session_results,
        "total_input_tokens": total_input,
        "total_output_tokens": total_output,
        "total_tokens": total_tokens,
        "total_memories": total_memories,
        "retrieval_accuracy": accuracy,
        "composite_score": composite,
        "checkpoint_details": {
            str(k): v for k, v in all_checkpoints.items()
        },
    }


def print_summary(results: dict) -> None:
    """Print a human-readable summary of eval results."""
    print("\n" + "=" * 60)
    print("MEMORYBENCH RESULTS")
    print("=" * 60)
    print(f"Model:               {results['model']}")
    print(f"Rule:                {results['rule_path']}")
    print(f"Total tokens:        {results['total_tokens']:,}")
    print(f"  Input:             {results['total_input_tokens']:,}")
    print(f"  Output:            {results['total_output_tokens']:,}")
    print(f"Memories saved:      {results['total_memories']}")
    print(f"Retrieval accuracy:  {results['retrieval_accuracy']:.1%}")
    print(f"Composite score:     {results['composite_score']:.6f}")
    print()

    print("Per-session breakdown:")
    for r in results["sessions"]:
        s = r["session"]
        tok = r["input_tokens"] + r["output_tokens"]
        mem = r["memories_saved"]
        cp = r["checkpoints"]
        if cp:
            passed = sum(1 for v in cp.values() if v)
            total = len(cp)
            print(f"  S{s}: {tok:>6,} tokens | {mem} memories | {passed}/{total} checkpoints")
        else:
            print(f"  S{s}: {tok:>6,} tokens | {mem} memories | (no checkpoints)")

    print()
    print("Checkpoint details:")
    for session_key, checks in results["checkpoint_details"].items():
        for name, passed in checks.items():
            status = "PASS" if passed else "FAIL"
            print(f"  [{status}] {name}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="MemoryBench: evaluate memory system effectiveness")
    parser.add_argument("--rule", type=Path, default=DEFAULT_RULE,
                        help="Path to memory-rule.md to evaluate")
    parser.add_argument("--model", default=DEFAULT_MODEL,
                        help=f"Claude model to use (default: {DEFAULT_MODEL})")
    parser.add_argument("--verbose", action="store_true",
                        help="Show full session responses")
    parser.add_argument("--output", type=Path, default=None,
                        help="Write full results JSON to this file")

    args = parser.parse_args()

    if not args.rule.exists():
        print(f"Error: rule file not found: {args.rule}", file=sys.stderr)
        print(f"Create it or copy the baseline: cp src/anamnesis/skeleton/rules/memory-rule.md eval/baseline_rule.md")
        return 1

    print(f"Running MemoryBench with {args.model}...")
    print(f"Rule: {args.rule}")
    print()

    results = run_eval(args.rule, args.model, args.verbose)
    print_summary(results)

    if args.output:
        # Strip full responses to keep JSON manageable
        output = {k: v for k, v in results.items() if k != "sessions"}
        output["sessions"] = [
            {k: v for k, v in s.items() if k != "response"}
            for s in results["sessions"]
        ]
        args.output.write_text(json.dumps(output, indent=2))
        print(f"\nResults written to {args.output}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
