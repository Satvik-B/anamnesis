---
type: meta
created: 2026-03-12
---

# Memory Archive

This directory holds memory files that have been retired from the active index.

## Why files end up here

- **Stale**: Not accessed in >90 days — moved during INDEX.md consolidation
- **Completed**: Project contexts for finished work
- **Split detail**: Oversized files that were split; the summary stays active,
  the detail lives here

## Structure

```
archive/
├── README.md           # This file
├── YYYY-MM/           # Monthly archive buckets (e.g., 2026-03/)
│   └── <file>.md      # Archived memory files with original frontmatter
└── detail/            # Detail files split from oversized summaries
    └── <topic>-detail.md
```

## Rules

- Archived files keep their original frontmatter (type, tags, created date)
- They are removed from INDEX.md active tables but remain grep-searchable
- To restore: move file back to its original location and re-add to INDEX.md
- Monthly directories are created as needed (don't pre-create empty ones)
