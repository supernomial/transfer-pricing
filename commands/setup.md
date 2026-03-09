---
description: Connect your Supernomial API key
argument-hint: "<your API key>"
---

# /setup — Connect Your API Key

This command saves your Supernomial API key so the plugin can authenticate with the server. It does **not** run the subscription check first — the whole point is to set up the key before other commands can validate.

**CRITICAL: Never show technical details to the user.** No script names, file paths, flags, exit codes, or JSON. Run scripts silently — only show the user the business-friendly result. If something fails, translate the error into a helpful next step.

## Steps

### Step 1: Extract the API key

The user's message contains their API key as the argument after `/transfer-pricing:setup`. Extract it.

If no key was provided, tell the user:
> "Please paste your API key after the command, like this: `/transfer-pricing:setup sk_live_abc123...`
> You can get your key at [cowork.supernomial.co/settings](https://cowork.supernomial.co/settings)."

Then stop.

### Step 2: Validate the format

The key must start with `sk_live_`. If it doesn't, tell the user:
> "That doesn't look like a valid API key. Keys start with `sk_live_`. Check your key at [cowork.supernomial.co/settings](https://cowork.supernomial.co/settings)."

Then stop.

### Step 3: Check for a working folder

Verify the user has a folder selected by listing the working directory contents.

- **No folder available**: Tell the user: "Please select a working folder first. Go to the Cowork home screen, click **'Work in a folder'** at the bottom of the input box, select your transfer pricing folder, and then run this command again."
- **Folder available**: Proceed.

### Step 4: Save the key

1. Create the `.supernomial/` directory in the working folder if it doesn't exist
2. Write the following to `.supernomial/config.json`:

```json
{
  "api_key": "sk_live_..."
}
```

Replace `sk_live_...` with the actual key from the user's message.

### Step 4b: Create memory folders

Create these directories in the working folder if they don't already exist:

1. `.supernomial/my-memory/`
2. `.library/firm-memory/`

No starter files needed — Claude creates topic files on demand.

### Step 5: Create folder instructions

Always write the following content to `CLAUDE.md` in the working folder root — overwrite if it already exists. User customizations are stored in memory files, not here.

```markdown
# Transfer Pricing Workspace

This folder is managed by the Supernomial transfer pricing plugin.

## How This Folder Works

Each client group has this layout:

- **1. Admin/** — administrative documents
- **2. Source Files/** — uploaded source documents
- **3. Working Papers/** — analysis and working documents
- **4. Deliverables/** — final PDF reports only

Working documents (interactive previews, project data) are stored in each group's `.records/` folder and don't clutter the deliverables.

Firm-wide resources (style guides, playbooks, reusable content) live in `.library/` at the root.

## Memory

This workspace remembers context across sessions using 5 memory scopes. Each scope is a folder of topic files (e.g. `contacts.md`, `methods.md`, `deadlines.md`) with date-stamped entries.

| Scope | Location | What goes here |
|---|---|---|
| Personal | `.supernomial/my-memory/` | Your name, role, preferences, conventions |
| Firm | `.library/firm-memory/` | Firm policies, standard methods, naming conventions |
| Group | `[Group]/.records/group-memory/` | Client decisions, deadlines, contacts |
| Entity | `[Group]/.records/entity-memory/[entity-id]/` | Entity-specific facts (CFO, fiscal year, conventions) |
| Deliverable | `[Group]/.records/file-memory/[entity-id]_FY[year]/` | Report-specific notes (sign-off, review status) |

**Before every response:** List the topic files in relevant memory folders. If any topic seems relevant to the user's message, read it. Start with personal + firm, add group/entity/deliverable when the context is clear.

**After learning something worth keeping:** Update the right memory file with a date-stamped entry (`### YYYY-MM-DD`). Create new topic files as needed. Keep entries factual — decisions, facts, preferences. Not session logs.

## For Claude

When working in this folder:
- **Find an entity's working document:** look in `[Group]/.records/views/` for `[entity-id]_FY[year].json` (source of truth) and `.html` (preview)
- **Find the final deliverable:** look in `[Group]/4. Deliverables/FY[Year]/Local File/[Country]/[Entity Name]/` for the PDF
- **Deliverables = PDF only.** Never put HTML, LaTeX temp files, or working files in the deliverables folder.
- **Preview HTML** lives in `.records/views/` next to the JSON — not in deliverables
- **Editing a section** for a specific entity: update the view JSON in `.records/views/` directly. Content `.md` files in `.records/content/` are for reusable group/firm content only.
- **Entity and transaction data** is in `[Group]/.records/data.json`

## Communication Style

Users are transfer pricing professionals — not developers. Talk like a knowledgeable colleague, not a software tool.

- **Use business language.** Say "I'll review the playbook and set up the report structure" — not "I'll read the schema references and generate the view JSON." Say "building the preview" — not "rendering the HTML from the JSON." Say "checking your project data" — not "reading data.json."
- **Never mention** file formats (.json, .html, .md, .tex), script names, variable names, folder paths, flags, or exit codes in your messages to the user.
- **Keep updates short.** "Setting up the Lotus group and preparing the local file" is enough. Don't narrate every internal step.
- **Errors = next steps.** If something fails, tell the user what to do — not what went wrong technically.
```

### Step 6: Verify the key works

Run:

```bash
python3 auth/gateway.py validate --working-dir .
```

(The `--working-dir .` flag tells the script where to find the saved key. Never mention this flag to the user.)

- **Exit code 0**: Tell the user: "You're all set! Run `/prep-local-file` to get started."
- **Exit code 1**: Show the error message from stderr to the user. Do not add technical details — the message is already user-friendly.
