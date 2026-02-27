---
description: Prepare a complete OECD-compliant transfer pricing local file — from intake to final PDF/Word deliverable
argument-hint: "<entity name or data file>"
---

# /prep-local-file -- Prepare Transfer Pricing Local File

## Step 0: Validate subscription

Before doing anything else, run:

```bash
python3 auth/gateway.py validate --working-dir .
```

- Exit code 0 → proceed normally.
- Exit code 1 → stop immediately and show the user the error from stderr in business-friendly language. If the error mentions running /setup, direct the user there. Never show script names, flags, file paths, or error codes to the user.

> If you see unfamiliar placeholders or need to check which tools are connected, see [CONNECTORS.md](../CONNECTORS.md).

Prepare a complete transfer pricing local file for a specific entity. This command handles the full workflow: intake, data gathering, structuring documentation, and generating the final deliverable (PDF or Word).

**Important**: This assists with transfer pricing documentation workflows but does not provide tax advice. All output should be reviewed by qualified transfer pricing professionals before submission to tax authorities.

## Invocation

```
/prep-local-file <entity name or data file>
```

## Workflow

**Efficiency rules — follow these throughout the entire workflow:**
- Do NOT explore or list the plugin folder structure. All paths are given explicitly below — use them directly.
- Do NOT read generated output files back after the script runs. The script prints success/failure to stdout. Only re-read if the script reported an error.
- Do NOT copy sample data from `data/examples/` into the working folder. Use `--data` and `--blueprint` to point the script at any path directly.
- After generating any file (HTML preview, PDF), **present it to the user** so it appears in the Cowork side panel.
- Keep conversation concise. Users are professionals — skip filler, get to substance.

**Language rules — always use business-friendly language:**
- NEVER say "JSON", "data warehouse", "blueprint", "schema", "template", "populate", "resolve references", "records folder" or other technical terms in conversation with the user.
- Instead say: "your file data", "the report", "your records", "the report structure", "update your data", "generate the report".
- NEVER describe internal architecture (content layers, reference resolution, script flags) unless the user specifically asks how it works.
- Say "I'll update the data and regenerate the preview" — not "I'll update the group JSON and run the assembly script with --format html".
- When presenting X-ray mode results, use the human-readable labels: "Standard content", "From your firm library", "Group-wide (shared across reports)", "Specific to this entity".

### Step 1: Resolve Working Directory

Check that the user has a folder selected. Try listing the contents of the working directory.

- **Folder available**: Proceed. The selected folder is the working directory — all client data, records, and deliverables go here.
- **No folder available**: Stop and tell the user: "It looks like no working folder was selected. Please go back to the Cowork home screen, click **'Work in a folder'** at the bottom of the input box, select your transfer pricing folder (e.g., Documents/Transfer Pricing), and then start a new task with /prep-local-file."

**Important:** The folder must be selected on the Cowork home screen BEFORE starting a task. Once a command is running, the folder picker is no longer accessible. Do NOT proceed without a writable folder. Do NOT write anything to the plugin folder — it is read-only.

### Step 1b: Load Style Guide

Before any conversation or content writing, load the style guides:
1. Read `skills/local-file/references/style-guide.md` — always apply Part 1 (conversation tone)
2. Check `.library/style-guide.md` in the user's selected folder — if found, use it for report writing style (overrides Part 2 of plugin default)
3. If no user style guide, apply Part 2 of the plugin default for report writing

Conversation tone is always from the plugin. Report writing style is user-overridable.

### Step 2: Intake

This is the most important step. Like an associate receiving instructions from a partner, gather everything needed before doing any work.

#### 2a. Parse what the user already provided

Check what came with the command invocation:
- Did they mention a group, entity, country, or year in the command text or chat?
- Did they upload a file? (prior year local file, Excel with data, client-provided draft)
- Did they paste text? (instructions, specific content to include)

Extract as much as possible from what's already provided. Only ask for what's missing.

#### 2b. Identify the group

Check the working directory for existing groups:
- **No groups exist**: Ask for the group/client name. This is a new client — will need full setup.
- **One group exists**: Assume it, confirm briefly ("I see Acme Group in your working directory. Is this the right client?")
- **Multiple groups exist**: Ask which one, listing what's available.

#### 2b-quick. Quick-start (new users only)

When the working directory has **NO existing groups**, offer two paths:

> This looks like a fresh start. Would you like to:
>
> **A. Quick-start** (recommended) — I'll ask one set of questions and get you to a working draft fast.
>
> **B. Guided walkthrough** — We'll go step by step through each part of the report setup.

**If the user picks Quick-start:**

1. Ask ONE compound question:
   > To get started, I need a few things:
   > - Client/group name
   > - Entity name and country of incorporation
   > - Fiscal year
   > - What types of intercompany transactions does this entity have? (e.g., purchase of goods, management fees, royalties, IP license)
   > - What's the entity's role? (e.g., limited-risk distributor, full-fledged manufacturer, contract R&D provider)

2. From the answers, create:
   - Group folder + `.records/` structure
   - `data.json` with group, entity, and transactions (placeholder amounts)
   - Entity blueprint with ONLY universal `@references/` content for all sections + chapter-level intro keys

   **CRITICAL: Do NOT create entity content files, firm library files, or group content files during quick-start.**
   Do NOT write any `.md` files to `.records/content/`, `.library/`, or `@group/` paths.
   Do NOT generate or draft section text — every content value must be a `@references/...` array.
   The user adds firm, group, and entity content later by explicitly requesting it.
   The only files created are `data.json` and the entity blueprint JSON.

3. Generate and present the **Workspace Editor** immediately (`--format combined`).

4. Tell the user: "Here's your draft — everything marked as standard content. You can start refining from here. Click into any section to customize it, or tell me what to update."

**If the user picks Guided walkthrough:** Continue with Step 2c below.

#### 2c. Identify year and entity

- Ask for fiscal year if not already provided
- Check the group's records for existing entities:
  - **Entities exist**: Show them ("I see Acme Netherlands B.V. and Acme Manufacturing Ltd. Which entity, or would you like to add a new one?")
  - **No entities**: Ask for entity name, country of incorporation

#### 2d. Scan what exists in the working directory

**First, load memory files** (if they exist) to personalize the session and skip redundant questions:

- **Personal preferences** (`.supernomial/me.json`): Read this file in the working directory root. Adapt tone, approach, and defaults based on the user's personal preferences (e.g., preferred TP method terminology, communication style, default currency).
- **Group/client memory** (`[Group]/.records/memory.json`): Surface relevant client context — audit status, upcoming deadlines, key contacts, domain knowledge, prior decisions. Use this to enrich the welcome: "Welcome back — I remember [relevant context from memory]."
- **Firm conventions** (`.library/memory.json`): Apply firm-wide conventions — naming standards, preferred methods, house style notes, recurring instructions.

Use memory to **skip questions already answered** in prior sessions. For example, if memory records "OECD 2022 guidelines" as the applicable framework, do not ask which version. If memory notes the partner's preferences, apply them without re-asking.

**Then scan the working directory** for this group and report findings:
- **Records** (`.records/data.json`): How many entities, how many transactions, what data is available
- **Notes on objects**: If `data.json` has `notes` arrays on group, entities, or transactions, surface them: "I see some notes from last time — [summary of relevant notes]"
- **Session log** (`.records/session-log.json`): If it exists, read the most recent entry and use it to:
  - Welcome the user back with context: "Welcome back — last time we worked on [entity], [summary]. We left off with [pending items]."
  - Skip questions that were already answered (don't re-ask about group, entity, or year if the session log is clear)
  - Highlight pending items: "Last time we noted [pending item] — has that been resolved?"
- **Blueprint notes** (`.records/blueprints/`): If a blueprint has `section_notes`, mention relevant ones during the intake
- **Prior year deliverables** (`4. Deliverables/`): "I found a 2023 local file for this entity" — this is the most common starting point (rollforward)
- **Source documents** (`2. Source Files/`): "I see financial statements and contracts uploaded"
- **Working files** (`3. Working Papers/`): "There's a draft from [date] for this entity"
- **Existing blueprint** (`.records/blueprints/`): "There's a report already configured for this entity"

If nothing exists, say so: "This is a fresh start — no prior work found for this entity."

#### 2e. Acknowledge reference materials

If the user uploaded files or pasted text:
- Acknowledge what was received: "I see you've attached [filename]. I'll use this as a reference."
- Classify the material: Is it a prior year local file? Client-provided data? Instructions from the partner?
- Important: reference materials inform the work, but structured data still gets entered into the records properly.

#### 2g. Check for firm blueprints

Check `[working-folder]/.library/blueprints/` for `.json` files with `"template_type": "firm"`.

- **No firm blueprints found:** Skip. The entity will use `based_on: "oecd-local-file"` (universal template only).
- **One firm blueprint found:** Auto-select it. Mention in the intake summary:
  > **Starting point**: Your firm's standard report structure ("[template_name]") — common sections pre-filled.
- **Multiple firm blueprints found:** Ask which starting point to use, listing options:
  > Which report structure should we start from?
  > - **OECD Standard** — Start fresh with universal content only
  > - **[template_name 1]** — [brief description based on content density]
  > - **[template_name 2]** — [brief description]

#### 2f. Present intake summary and confirm

Before doing any work, present a clear summary:

```
## Intake Summary

**Group**: Acme Group (existing client — 2 entities, 3 transactions on file)
**Entity**: Acme Netherlands B.V., FY 2024
**Starting point**: 2023 local file found in working directory (rollforward)
**Reference material**: You uploaded an Excel with updated transaction amounts
**Blueprint**: No existing blueprint — I'll create one

**My plan**:
1. Rollforward the 2023 structure as the starting point
2. Update transaction data from the uploaded Excel
3. Create a blueprint for this entity
4. Generate the 2024 local file

Shall I proceed?
```

Wait for the user to confirm before moving to Step 3.

### Section Order Principle

When collecting information (Steps 3–4) and building the blueprint, **always follow the order of sections as defined in the blueprint**. The blueprint is the single source of truth for what goes into the report and in what order.

This means:
- Ask the user about group-level information first (group overview), then entity-level (entity introduction), then transaction-level (controlled transactions), and so on — mirroring the report structure.
- When presenting information back to the user, follow the same order.
- Do NOT hardcode section names or order in this command — the blueprint defines them. As sections are added, removed, or reordered in the blueprint structure, the conversation flow naturally adapts.

**Why:** Humans think about documents top-to-bottom. If the final report starts with the group overview and ends with the transactions table, the conversation should flow in the same order. This keeps the user oriented — they always know where they are in the process relative to the final output.

### Views — One Pipeline

The user works primarily in the Workspace Editor during preparation, with PDF as the final deliverable:

| View | Format flag | Purpose | When to generate |
|---|---|---|---|
| **Workspace Editor** | `--format combined` | All-in-one workspace: dashboard, editor, notes, X-ray, review/signoff | Primary view during Steps 3–5, after each data update |
| **Final PDF** | `--format pdf` | Submission-ready deliverable | Step 5 (generation) |

The Workspace Editor replaces the separate dashboard, editor, and report views with a single integrated workspace. The user can edit content, manage notes and comments, toggle X-ray mode, review and sign off sections, and save changes — all in one view.

Legacy views (overview dashboard, intake preview, report view, section editor) still work via `--format html` and `--format report` for backward compatibility but are no longer the primary workflow.

### Live Preview (Workspace Editor)

Throughout Steps 3–4, after each meaningful data update (new entity added, transactions entered, section content written), **regenerate the Workspace Editor** so the user can see the current state in the Cowork side panel:

```bash
python3 skills/local-file/scripts/assemble_local_file.py \
  --data "[selected-folder]/[Group Name]/.records/data.json" \
  --blueprint "[selected-folder]/[Group Name]/.records/blueprints/local-file-[entity-id].json" \
  --references "skills/local-file/references/" \
  --library "[selected-folder]/.library/" \
  --group-content "[selected-folder]/[Group Name]/.records/content/" \
  --entity-content "[selected-folder]/[Group Name]/.records/content/[entity-id]/" \
  --template "skills/local-file/assets/combined_view.html" \
  --brand "assets/brand.css" \
  --output "[selected-folder]/[Group Name]/" \
  --format combined \
  --blueprints-dir "[selected-folder]/[Group Name]/.records/blueprints/"
```

This is the same assembly script with `--format combined`. It reads the current records and blueprint, populates the Workspace Editor template, and writes a single `.html` file. Zero tokens — pure Python string replacement. Cowork renders HTML with full styling in the side panel.

### Section Dashboard (Legacy)

Replaced by the Workspace Editor for new workflows. Shows all sections organized by category (Report Preamble, Business Description, Industry Analysis, Functional Analysis, Controlled Transactions, Benchmark Application, Closing) with completion status badges and content layer indicators:

```bash
python3 skills/local-file/scripts/assemble_local_file.py \
  --data "[selected-folder]/[Group Name]/.records/data.json" \
  --blueprint "[selected-folder]/[Group Name]/.records/blueprints/local-file-[entity-id].json" \
  --references "skills/local-file/references/" \
  --library "[selected-folder]/.library/" \
  --group-content "[selected-folder]/[Group Name]/.records/content/" \
  --entity-content "[selected-folder]/[Group Name]/.records/content/[entity-id]/" \
  --template "skills/local-file/assets/section_dashboard.html" \
  --brand "assets/brand.css" \
  --output "[selected-folder]/[Group Name]/" \
  --format html
```

This replaces the full-page intake preview as the default view during preparation. Users see progress at a glance and ask Claude to work on specific sections.

### Section Editor (Legacy)

When the user asks to work on a specific section (e.g., "Let's work on the group overview"), generate the section editor:

```bash
python3 skills/local-file/scripts/assemble_local_file.py \
  --data "[selected-folder]/[Group Name]/.records/data.json" \
  --blueprint "[selected-folder]/[Group Name]/.records/blueprints/local-file-[entity-id].json" \
  --references "skills/local-file/references/" \
  --library "[selected-folder]/.library/" \
  --group-content "[selected-folder]/[Group Name]/.records/content/" \
  --entity-content "[selected-folder]/[Group Name]/.records/content/[entity-id]/" \
  --template "skills/local-file/assets/section_editor.html" \
  --brand "assets/brand.css" \
  --output "[selected-folder]/[Group Name]/" \
  --format html \
  --section group_overview
```

The section editor shows the content layer badge, source path, section note, and an editable textarea. The user edits and clicks "Send updates" to copy changes to clipboard.

**When to regenerate:**
- After creating or updating the records (Step 3)
- After adding or updating blueprint sections (Step 4)
- Before presenting the final confirmation (Step 4 end)

**After generating, always present the file to the user** so it appears in the Cowork side panel. Do NOT read the generated file back — the script prints success/failure, and re-reading wastes tokens.

The preview shows section-by-section status (Complete/Pending badges), entity details, and the transactions table. It helps the user see progress without reading back through the conversation.

### Report View (Legacy)

Once sections have content, generate the **report view** — a document-style preview that dynamically renders all blueprint sections with category headers and hierarchical numbering, and includes a toggleable X-ray mode:

```bash
python3 skills/local-file/scripts/assemble_local_file.py \
  --data "[selected-folder]/[Group Name]/.records/data.json" \
  --blueprint "[selected-folder]/[Group Name]/.records/blueprints/local-file-[entity-id].json" \
  --references "skills/local-file/references/" \
  --library "[selected-folder]/.library/" \
  --group-content "[selected-folder]/[Group Name]/.records/content/" \
  --entity-content "[selected-folder]/[Group Name]/.records/content/[entity-id]/" \
  --template "skills/local-file/assets/report_view.html" \
  --brand "assets/brand.css" \
  --output "[selected-folder]/[Group Name]/" \
  --format report
```

**X-ray mode** (toggled via a button in the top bar) annotates each section with:
- **Layer color** (left border): slate gray = Universal (`@references/`), purple = Firm Library (`@library/`), purple = Group-wide (`@group/`), blue = Entity-specific (`@entity/` files or plain text)
- **Impact label**: tells the user whether editing affects only this report, all reports in this group, or all clients
- **Source path**: for referenced content (`@references/...` or `@library/...`), shows the file origin

This helps the user understand how the report is assembled before committing to the final PDF. They can see which pieces are shared across reports and where changes would propagate.

**When to generate:**
- After all sections are populated (end of Step 4), before final PDF
- When the user explicitly asks to see the report view or asks "where does this content come from"
- When the user clicks "Report view" in the intake preview navigation

**After generating, always present the file to the user.**

### Step 3: Build/Update the Records

Based on the intake, update the group's records (`.records/data.json`):

**New client flow:**
1. Create the client folder structure: `1. Admin/`, `2. Source Files/`, `3. Working Papers/`, `4. Deliverables/`, `.records/`
2. Create `.records/data.json` with group object
3. Add entity objects
4. Gather transaction data from the user or reference materials
5. Confirm all structured data with the user before saving

**Existing client flow (rollforward):**
1. Load existing records
2. Update/add data based on new year's information
3. Show what changed vs. prior year
4. Confirm updates with the user before saving

For transaction data, gather:
- Transaction type (purchase of goods, management fee, royalty, IP license, etc.)
- Counterparty entity (must exist in the records)
- Amount and currency
- Transfer pricing method applied

Allow the user to add multiple transactions iteratively.

**Field names in data.json — use these exactly:**
- Transactions: `from_entity`, `to_entity`, `from_entity_profile`, `to_entity_profile`
- Local files: `entity` (not `entity_id`)
- All IDs are kebab-case slugs matching the object's `id` field

**Capture notes as you go:** During this step, if the user explains context, reasoning, or mentions pending items (e.g., "this amount is preliminary" or "the CFO wants conservative language"), save these as `notes` on the relevant object in `data.json`. Don't ask permission — just capture naturally. Notes are optional arrays of strings on any object (group, entity, transaction).

### Step 3b: Collect Functional Profile Content

For each transaction, the entity's functional profile needs content for the report. There are 22 profile types, each with 4 content blocks (Profile Overview, Functions, Assets, Risks). **Do NOT ask for each sub-topic individually** — that would be 660 questions across all profiles. Instead:

**Approach: conversational, batch-style, with drafts**

1. **Read the reference checklist.** For the profile type (e.g., `limited-risk-distributor`), read `skills/local-file/references/functional-profiles/limited-risk-distributor.md` to get the sub-topic bullet points.

2. **Present all topics in one prompt.** Combine the entity context you already have with the checklist and present it conversationally. Example:

   > "For the functional analysis of Acme Netherlands as a **limited-risk distributor**, I need to describe its functions, assets, and risks. Here's what I'd typically cover:
   >
   > **Functions:** order processing, limited marketing, inventory management (with return clauses), customer interface, logistics coordination, admin, and market feedback to the principal.
   >
   > **Assets:** limited inventory with return rights, trade receivables, minimal fixed assets, IT systems, office space.
   >
   > **Risks:** limited market risk (routine return), limited inventory risk (buy-back), limited credit risk, minimal FX risk, operational risk only.
   >
   > Can you tell me what's specific to this entity? Or I can draft paragraphs based on what I already know and you can refine them."

3. **Draft proactively.** If you have enough context (from prior year files, uploaded documents, or earlier conversation), draft the paragraphs yourself and ask the user to review. This is the preferred path — the user edits a draft rather than starting from scratch.

4. **Collect in batches, not one-by-one.** Cover Functions, Assets, and Risks together in one exchange. If the user gives partial info, fill in reasonable defaults from the reference checklist and note what's assumed.

5. **Store as content blocks.** Save each paragraph as a content file:
   - Firm-reusable profiles → `.library/functional-profiles/[slug]/functions.md` (Layer 2)
   - Group-customized profiles → `[Group]/.records/content/functional-profiles/[slug]/functions.md` (Layer 3)
   - Entity-specific → `[Group]/.records/content/[entity-id]/fp-[slug]-functions.md` (Layer 4, referenced as `@entity/fp-[slug]-functions`)

6. **Don't over-ask.** The 22 × 4 = 88 content blocks are the maximum across ALL profile types. Most entities use 1-2 profile types. Most of the content should be drafted by Claude and reviewed by the user — not dictated field by field.

**Reuse principle:** If the user has already described a limited-risk distributor for another entity or group, offer to reuse that content: "I see you've described a limited-risk distributor before for [other entity]. Want to start from that?"

### Step 4: Build/Update the Blueprint

Create or update the blueprint for this entity and deliverable. The blueprint defines the **sections and their order** — this is the source of truth for the report structure.

**Quick-start blueprints:** When coming from the quick-start path (Step 2b-quick), the blueprint must contain ONLY `@references/...` content arrays. Do NOT pre-populate sections with `@entity/` references or draft content. Empty sections use `[]`. The user decides when to add content beyond the universal layer.

**If a firm blueprint was selected in Step 2g**, use it as the starting point:
1. Read the firm blueprint from `.library/blueprints/{slug}.json`
2. Copy its `content` object as the initial content for the entity blueprint
3. Copy `title_overrides` and `section_notes`
4. Use `default_covered_profiles` / `default_covered_transactions` as suggestions ("Your firm typically documents these profiles — do they apply here?")
5. Pre-populated sections (those with `@references/` or `@library/` content) are **not re-asked** — skip them in the walkthrough
6. Empty sections (`[]`) are walked through normally with the user
7. Add `"firm_blueprint": "{slug}"` as metadata on the entity blueprint
8. The entity blueprint always keeps `based_on: "oecd-local-file"` — firm content is copied at creation time, not resolved at assembly time

**Otherwise (no firm blueprint, or OECD Standard chosen):**

1. Determine which sections the local file needs (follow the standard blueprint section order)
2. Walk through sections in order with the user, resolving each content source:
   - `@references/...` for universal OECD content (Layer 1)
   - `@library/...` for firm library content (Layer 2)
   - `@group/...` for group-customized content shared across entities (Layer 3)
   - `@entity/...` for entity-specific content files (Layer 4) — stored in `[Group]/.records/content/[entity-id]/`
   - Plain text for inline entity-specific content (Layer 5)
   - Array for composite sections — combine content from multiple layers in one section (e.g., `["@references/preamble/objective", "@entity/objective-addendum"]`). Each element is resolved independently.
   - **Cascade rule:** If the user wants to customize firm library content for this group, copy it to `@group/` and edit there. If they want to further customize for one entity, save as `@entity/` file. For sections needing both shared and specific content, use composite arrays.
3. If rollforward: start from prior year's blueprint, update section by section in order
4. Confirm the complete blueprint with the user before proceeding to generation

**Reference paths must point to files, not directories.** Use `@references/recognition/commercial-rationality` — not `@references/recognition`.

**Always include chapter-level keys.** Every top-level chapter (`executive-summary`, `business-description`, `industry-analysis`, `economic-analysis`) must have a key in `content`. Reference the standard chapter intro files:
```
"executive-summary": ["@references/preamble/executive-summary"],
"business-description": ["@references/business/business-description"],
"industry-analysis": ["@references/industry/industry-analysis"],
"economic-analysis": ["@references/economic-analysis/economic-analysis"]
```

**Capture section notes:** If the user explains *why* a section should be written a certain way (e.g., "the partner wants emphasis on decentralized decision-making"), save it in the blueprint's `section_notes` object. These editorial notes persist across sessions so future work on this blueprint has full context.

**CHECKPOINT — Firm blueprint offer (do NOT skip):**
After the blueprint is confirmed, before Step 5, check `.library/blueprints/`.
- **No firm blueprints exist**: MUST ask the save question:
  > "Would you like to save this report structure as a reusable starting point? Next time you start a new client, I'll pre-fill the common sections. Takes one second."
- **Firm blueprints already exist**: Skip.

Also triggered by the user saying "save this as a template" at any point.

**To create the firm blueprint:**
1. Read the entity blueprint
2. Strip per the firm blueprint stripping rules (see Notes section below)
3. Ask for a name → derive slug (kebab-case)
4. Write to `[working-folder]/.library/blueprints/{slug}.json`
5. Confirm: "Saved as '[name]'. I'll offer this whenever you start a new local file."

### Step 5: Assemble and Generate (Script)

This step is handled by a **deterministic Python script**, not by Claude directly. This ensures consistent output, minimizes token usage, and reduces review time.

Run the assembly script to generate the final PDF:
```bash
python3 skills/local-file/scripts/assemble_local_file.py \
  --data "[selected-folder]/[Group Name]/.records/data.json" \
  --blueprint "[selected-folder]/[Group Name]/.records/blueprints/local-file-[entity-id].json" \
  --references "skills/local-file/references/" \
  --library "[selected-folder]/.library/" \
  --group-content "[selected-folder]/[Group Name]/.records/content/" \
  --entity-content "[selected-folder]/[Group Name]/.records/content/[entity-id]/" \
  --template "skills/local-file/assets/local_file.tex" \
  --output "[selected-folder]/[Group Name]/4. Deliverables/FY[Year]/Local-Files/[Country]/[Entity Name]/" \
  --format pdf
```

The script handles:
1. Reading the records and blueprint
2. Resolving all `@references/` and `@library/` content references
3. Populating the LaTeX template with resolved values
4. Compiling to PDF using `pdflatex`
5. Saving output to the correct folder

Claude does NOT assemble the document manually. Claude prepares the inputs (records + blueprint), then calls the script.

**Output formats, same script:**
- `--format combined` → Workspace Editor — all-in-one workspace with dashboard, editor, notes, X-ray **← primary view during Steps 3–5**
- `--format pdf` → final deliverable (LaTeX → PDF) **← Step 5 generation**
- `--format html` → legacy dashboard/editor views (backward compat)
- `--format report` → legacy annotated report view (backward compat)
- `--format md` → fallback preview (markdown, if HTML rendering ever fails)

After the script completes, **present the output file to the user** — do NOT read it back with a file read tool.

### Step 6: Deliver, Save Session, and Next Steps

**6a. Save session log and consolidate memory:**

Before presenting next steps, append a session entry to `[Group Name]/.records/session-log.json`. If the file doesn't exist, create it as an array with one entry. If it exists, append to the array.

```json
{
  "date": "[today's date, ISO format]",
  "command": "prep-local-file",
  "entity": "[entity-id]",
  "summary": "[1-2 sentence overview of what was accomplished]",
  "decisions": ["[key decision 1]", "[key decision 2]"],
  "pending": ["[item still needed]", "[follow-up required]"]
}
```

Keep entries concise — this is a professional engagement log, not a conversation transcript. If no decisions were made or nothing is pending, use empty arrays.

**Then consolidate memory files.** After writing the session log, review and clean up each memory file that was read or updated during the session:
- Merge duplicate entries (same fact captured in different words)
- Remove outdated deadlines (more than 3 months past)
- Cap each category at roughly 15 entries — keep the most relevant, drop the least useful
- Remove lifecycle entries older than 30 days unless marked as permanent
- Write the cleaned memory back to the same file

**Continuous logging:** Do NOT wait until the end of the session to update the session log. Throughout the conversation, append to the session log after any data change, file generation, or important decision. Users close chats randomly — if the session ends unexpectedly, the log should still reflect what happened up to that point.

**6b. Present to user:**

Show the user:
- Where the final deliverable is saved (full path)
- Summary of what was included (sections, data points)
- Suggest next steps:
  - "Would you like to review the output?"
  - "Would you like to prepare a local file for another entity in this group?"
  - "Would you like to update any sections?"

Do NOT mention the session log in conversation — it's invisible to the user. They just experience continuity next time.

## Output Format

The intake summary (Step 2f) should always follow the format shown above. The final deliverable follows the LaTeX template structure.

### Handling Pasted Updates from the Editor

The editor has a **"Send updates"** button. When the user clicks it, only the **changed fields** are copied to their clipboard (not the entire form). If the user pastes this into the chat, it looks like:

```json
{
  "_source": "preview_edit",
  "_entity_id": "acme-nl",
  "_fiscal_year": "2024",
  "_currency": "EUR",
  "_summary": [
    "Purchase of finished goods: amount changed to EUR 14,400,000"
  ],
  "transactions": [
    {"name": "Purchase of finished goods", "counterparty": "Acme Manufacturing Ltd.", "amount": 14400000},
    {"name": "Management fee", "counterparty": "Acme Manufacturing Ltd.", "amount": 350000},
    {"name": "Royalty payment", "counterparty": "Acme Manufacturing Ltd.", "amount": 780000}
  ]
}
```

**Key differences from v1:**
- `_summary` is a human-readable list of what changed — use this to confirm with the user
- `sections` is only present if section text was actually modified (omitted if unchanged)
- `transactions` is only present if any transaction was added, removed, or modified (omitted if unchanged)
- If neither `sections` nor `transactions` is present, there are no changes

**When you receive this JSON:**

1. **Identify it** by the `"_source": "preview_edit"` field
2. **Read the `_summary`** — this tells you exactly what changed in plain language
3. **Apply section changes** (if `sections` key exists): update the blueprint's `content` object. Keys may be path-style (`executive-summary/objective`) or legacy underscore-style (`executive_summary_objective`) — handle both
4. **Apply transaction changes** (if `transactions` key exists):
   - Match by transaction name
   - Update amounts if changed
   - For new transaction names (not in current data), ask the user to confirm the counterparty entity and direction (buy/sell), then add
   - For transactions removed from the list, confirm with the user before deleting
5. **Update the data and regenerate the preview** so the user sees the updated state
6. **Confirm in business language**: "Updated — the purchase of finished goods is now EUR 14.4M. The preview has been refreshed."

**Important:** The `counterparty` field contains the display name, not the entity ID. Match it against entity names in the data. If no match is found, ask the user.

**Do NOT** echo the raw JSON back to the user. Summarize in natural language using the `_summary` field.

### Handling Pasted Updates from the Workspace Editor

The Workspace Editor has a **Save** button. When the user clicks it, a human-readable summary is copied to their clipboard and the full JSON payload is stored in the HTML file. If the user pastes the summary into the chat, it looks like:

```
Mark 1. Executive Summary as reviewed
Updated 2.1 Group Overview with new content
Change document stage to Review
```

**Parsing the paste:**

1. **Check for `<!-- COWORK_DATA` markers first** (backward compat with older versions). Extract the JSON from between `<!-- COWORK_DATA` and `COWORK_DATA -->`.
2. **Check for raw JSON** with `"_source": "combined_view"` (backward compat).
3. **Summary-only paste (current format):** If the paste contains human-readable summary lines (e.g., "Mark X as reviewed", "Updated X with new content", "Change document stage to...") but no JSON:
   a. Find the Workspace Editor HTML file in the entity's deliverable folder (the `.html` file matching `Workspace_Editor_FY*.html` or `Expert_Mode_FY*.html`)
   b. Read the HTML file and extract the text content from the `<div id="cowork-payload">` element
   c. Parse that text as JSON
   d. Apply the changes from the JSON payload

When the JSON is obtained (from any of the three paths above), proceed with applying changes as described below.

**Important:** The payload only contains fields that actually changed — not a full dump of all state. If the user only marked a section as reviewed, the payload will only contain `section_status` for that one section.

**When you receive this JSON:**

1. **Identify it** by the `"_source": "combined_view"` field
2. **Read the `_summary`** array to understand what was changed
3. **Show the summary to the user**: "I see you made these changes in the Workspace Editor: [summary items]"
4. **Apply changes to the data files:**
   - `sections` → overwrite matching keys in blueprint `content` (these are Layer 4/5 edits — entity-specific text). Keys may be path-style (`executive-summary/objective`) or legacy underscore-style
   - `section_notes` → overwrite matching keys in blueprint `section_notes`
   - `footnotes` → overwrite matching keys in blueprint `footnotes`
   - `section_status` → merge into the `local_file` object's `section_status` in `data.json` (find the local_file matching `_entity_id`)
   - `stage` → set `local_file.status` in `data.json`
   - `document_meta.title` → set `local_file.document_title` in `data.json`
   - `document_meta.subtitle` → set `local_file.document_subtitle` in `data.json`
   - `document_meta.meta` → set `local_file.document_meta` in `data.json`
5. **Save** updated `data.json` and blueprint JSON
6. **Re-run assembly** with `--format combined` to refresh the Workspace Editor
7. **Confirm with bullet points**:

> Applied your changes:
> - Updated the Scope section with new content
> - Marked Executive Summary as reviewed
> - Changed document stage to Review
>
> Workspace Editor refreshed.

Use the `_summary` array items as the bullet points. Each array item becomes one bullet.

**Key differences from the legacy editor payload:**
- `_source` is `"combined_view"` (not `"preview_edit"`)
- Includes `section_status`, `stage`, `footnotes`, and `document_meta` (not just sections and transactions)
- `sections` contains Layer 4 text content (entity-specific), not transaction data
- No `transactions` field — transaction edits happen in the chat, not in the Workspace Editor

**Do NOT** echo the raw JSON back to the user. Summarize in natural language using the `_summary` field.

## Notes

- This command handles both **new local files** and **rollforward of existing files**
- The most common use case is rollforward — always check for prior year work first
- Data is preserved in the records JSON for reuse across deliverables
- Reference materials (uploaded files, pasted text) inform the work but structured data must be entered into the records
- The workflow can be interrupted and resumed — the records, blueprints, notes, and session log persist between sessions
- Always confirm with the user before writing to the records or generating output
- **Notes are additive** — update or add notes during a session, but never delete them without the user's explicit request
- **Session log is append-only** — never modify past entries, only add new ones
- **Notes travel with data** — if records are shared or copied to another system, context follows automatically
- **Memory files persist across sessions** — personal, group, and firm context is automatically captured and used for continuity

### Firm Blueprint Stripping Rules

When saving an entity blueprint as a firm blueprint, apply these rules to extract only reusable firm-level content:

| Keep | Strip |
|---|---|
| `@references/` content references | `@group/` references |
| `@library/` content references | `@entity/` references |
| `title_overrides` (firm-wide) | Plain text (inline content) |
| `section_notes` (editorial) | `group`, `entity`, `fiscal_year`, `deliverable` fields |
| `default_covered_profiles` / `default_covered_transactions` (advisory, from entity's `covered_*`) | `covered_profiles` / `covered_transactions` (entity-specific) |

Sections that had only group/entity/inline content become `[]` (empty array) — they show up as empty boxes in the Workspace Editor, signaling "content expected here."

The resulting firm blueprint uses `template_type: "firm"` and `based_on: "oecd-local-file"`. See `skills/local-file/references/section-schema.md` for the full schema.
