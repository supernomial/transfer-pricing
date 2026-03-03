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

### Step 5: Create folder instructions

If the file `CLAUDE.md` does **not** already exist in the working folder root, create it with the following content. If it already exists, skip this step — never overwrite user customizations.

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

## For Claude

When working in this folder:
- **Find an entity's working document:** look in `[Group]/.records/views/` for `[entity-id]_FY[year].json` (source of truth) and `.html` (preview)
- **Find the final deliverable:** look in `[Group]/4. Deliverables/FY[Year]/Local File/[Country]/[Entity Name]/` for the PDF
- **Deliverables = PDF only.** Never put HTML, LaTeX temp files, or working files in the deliverables folder.
- **Preview HTML** lives in `.records/views/` next to the JSON — not in deliverables
- **Editing a section** for a specific entity: update the view JSON in `.records/views/` directly. Content `.md` files in `.records/content/` are for reusable group/firm content only.
- **Entity and transaction data** is in `[Group]/.records/data.json`
```

### Step 6: Verify the key works

Run:

```bash
python3 auth/gateway.py validate --working-dir .
```

(The `--working-dir .` flag tells the script where to find the saved key. Never mention this flag to the user.)

- **Exit code 0**: Tell the user: "You're all set! Run `/prep-local-file` to get started."
- **Exit code 1**: Show the error message from stderr to the user. Do not add technical details — the message is already user-friendly.
