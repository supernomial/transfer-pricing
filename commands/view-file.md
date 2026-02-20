---
description: View and list generated local files and documentation
argument-hint: "<entity name or file>"
---

# /view-file -- View Generated Files

## Step 0: Validate subscription

Before doing anything else, run:

```bash
python3 skills/local-file/scripts/gateway.py validate
```

- Exit code 0 → proceed normally.
- Exit code 1 → stop immediately and show the user the error printed to stderr. Do not proceed with any other steps.

View and list generated transfer pricing local files and documentation from the Deliverables folder.

## Invocation

```
/view-file [entity name or file]
```

## Workflow

### Step 1b: Load Context

Before presenting data, silently load available memory:
1. Read `.supernomial/me.json` if it exists — adapt presentation to user preferences
2. If a group is identified, read `[Group]/Records/memory.json` — enrich data view with client context
3. Read `_library/memory.json` if it exists — apply firm conventions

(To be implemented)
