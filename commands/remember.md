---
description: Save a preference, convention, or piece of context that persists across sessions
argument-hint: "<what to remember>"
---

# /remember -- Save Context for Future Sessions

## Step 0: Validate subscription

Before doing anything else, run:

```bash
python3 skills/local-file/scripts/gateway.py validate
```

- Exit code 0 → proceed normally.
- Exit code 1 → stop immediately and show the user the error printed to stderr. Do not proceed with any other steps.

Save something you want Claude to keep in mind across sessions — a preference, a convention, a piece of context, or a note about a client.

## Invocation

```
/remember <what to remember>
```

## Workflow

### Step 1: Resolve working folder

Confirm a working folder is selected. If not, tell the user to select one first.

### Step 1b: Load existing memory

Silently read all available memory files to understand current context:
1. Read `.supernomial/me.json` if it exists
2. If a group is identified from context, read `[Group]/Records/memory.json`
3. Read `_library/memory.json` if it exists

Do NOT mention loading these files to the user.

### Step 2: Parse the request

Extract what the user wants remembered from their argument or message. Identify the core fact, preference, or convention.

### Step 3: Classify and route

Determine where this memory belongs using the classification tree:

| If it is about... | Save to... |
|---|---|
| The user personally (working style, communication preferences, personal context) | `.supernomial/me.json` |
| A specific client or group (contacts, deadlines, client preferences, domain knowledge) | `[Group]/Records/memory.json` |
| A firm-wide convention (house style, methodology preferences, standard workflows) | `_library/memory.json` |
| A specific data object (transaction caveat, entity flag, benchmark note) | `notes` array on the relevant object in `data.json` |
| A specific report section (editorial reasoning, partner feedback) | `section_notes` in the relevant blueprint |

If ambiguous between group-level and firm-level, ask briefly: "Is this specific to [client name] or something you'd like across all clients?"

### Step 4: Save in timestamp format

Add the entry using the standard timestamp format: `"YYYY-MM-DD | content"`. Create the memory file if it does not exist, using the appropriate schema from `data/examples/`.

### Step 5: Confirm naturally

Respond with a brief, natural confirmation. Examples:
- "Got it — I'll keep that in mind."
- "Noted."
- "I'll remember that for next time."

## Language Rules

- NEVER show file paths or technical terms to the user.
- NEVER say "memory file", "JSON", "saved to memory", "data.json", or any implementation detail.
- NEVER narrate your internal process. Just do it and confirm.
- If the memory file does not exist yet, create it silently — do not ask the user about file creation.
