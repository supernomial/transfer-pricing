---
description: View and explore structured entity data in your transfer pricing records
argument-hint: "<entity name or filter>"
---

# /view-data -- View Entity Data

## Step 0: Validate subscription

Before doing anything else, run:

```bash
python3 skills/local-file/scripts/gateway.py validate
```

- Exit code 0 → proceed normally.
- Exit code 1 → stop immediately and show the user the error printed to stderr. Do not proceed with any other steps.

View and explore the structured data stored in your transfer pricing records.

## Invocation

```
/view-data [entity name or filter]
```

## Workflow

### Step 1b: Load Context

Before presenting data, silently load available memory:
1. Read `.supernomial/me.json` if it exists — adapt presentation to user preferences
2. If a group is identified, read `[Group]/Records/memory.json` — enrich data view with client context
3. Read `_library/memory.json` if it exists — apply firm conventions

(To be implemented)
