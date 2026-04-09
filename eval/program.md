# MemoryBench Optimization Program

You are optimizing `memory-rule.md` — the behavioral instructions that control
how an AI coding assistant saves and retrieves memories across sessions.

## What you're optimizing

The eval runs 5 coding sessions sequentially. Between sessions, the AI loses
its conversation context (simulating separate Claude Code sessions). The ONLY
continuity is through the memory system: memories saved in earlier sessions
are injected into later sessions via the system prompt.

## What the sessions test

- **S1 (Setup):** Build a Flask API. No prior context needed.
- **S2 (Feature):** Add rate limiting. Should recall S1's architecture.
- **S3 (Debug):** Fix a race condition. Should produce a learning.
- **S4 (Reuse):** Similar task. Should reuse S3's lesson proactively.
- **S5 (Retrieval):** Summarize everything. Should recall all key facts.

## What the metric measures

```
composite = retrieval_accuracy / log2(total_tokens)
```

- **retrieval_accuracy:** Does Claude reference the right prior knowledge?
  11 checkpoints across sessions 2-5 test specific recall.
- **total_tokens:** All input+output tokens across 5 sessions. Lower is better.

## What levers you have

Modify the memory-rule.md to change:

1. **Save triggers** — What should Claude save? When? How aggressively?
2. **Save format** — What metadata/structure makes memories retrievable?
3. **Retrieval triggers** — When should Claude check its memories?
4. **Retrieval strategy** — How should Claude use memories in responses?
5. **Consolidation** — How should Claude organize/compress memories?
6. **Pruning** — What can be skipped to save tokens?

## What to avoid

- Don't make the rule so long it wastes input tokens on every session
- Don't make the rule so vague that Claude doesn't save useful things
- Don't add task-specific instructions (the rule must be general-purpose)
- Don't remove the core structure (types, frontmatter) — modify, don't gut

## Strategy hints

- The biggest wins come from **retrieval**: Claude saving things is easy,
  Claude actually USING saved memories in later sessions is the hard part
- Explicit instructions like "before responding, check your memories for
  relevant context" tend to help
- Compact memories retrieve better than verbose ones
- Tags and structured metadata help Claude find relevant memories
- The memory format itself costs tokens — optimize for signal-to-noise
