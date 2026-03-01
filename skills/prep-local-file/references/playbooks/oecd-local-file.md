---
name: Standard
---

# OECD Local File Playbook

Standard playbook for an OECD-compliant transfer pricing local file.

## What a Playbook Defines

A playbook is the recipe for a deliverable. It defines three things:

1. **Structure** — which sections exist, their order, and hierarchy (parent/child)
2. **Content sources** — where the default text comes from. Content is auto-resolved through the layer hierarchy (entity → group → firm → universal), so overriding content does NOT require a custom playbook.
3. **Instructions** — optional guidance for Claude on how to produce a section. Examples: "pull org structure from the file the client specifies", "use conservative language", "summarize the uploaded PDF". Most sections leave this blank; it's the hook for future customization.

**When do you need a custom playbook?** Only when you want to change **structure** — add sections, remove sections, reorder, or change section titles. To just override content, save a `.md` file at the right layer path and it auto-resolves.

## How to Read This Playbook

| Column | Description |
|---|---|
| **Section ID** | Kebab-case identifier. Nested IDs use `/` (e.g., `executive-summary/objective`). |
| **Title** | Display title for the section header. |
| **Parent** | Parent section ID, or `—` for top-level chapters. |
| **Content Source** | Default content path. Prefixes: `@references/` (Layer 1), `@library/` (Layer 2), `@group/` (Layer 3), `@entity/` (Layer 4). `(auto)` = built from structured data. |
| **Instructions** | Optional. Additional guidance for Claude when producing this section. |

## Content Resolution

When building the view JSON, Claude resolves content for each section as follows:

1. Read the content source path from the playbook (e.g., `@references/preamble/objective`)
2. Extract the relative path: `preamble/objective`
3. Check for overrides at higher layers using the same relative path (highest wins):
   - `[Group]/.records/content/[entity-id]/preamble/objective.md` → Layer 4 (entity)
   - `[Group]/.records/content/preamble/objective.md` → Layer 3 (group)
   - `.library/preamble/objective.md` → Layer 2 (firm)
   - `skills/prep-local-file/references/preamble/objective.md` → Layer 1 (universal fallback)
4. Use the highest-layer match as the element's `text` field
5. If `(auto)`, build an `auto_table` from structured data instead

**Example:** A firm saves `.library/preamble/objective.md` with their standard objective text. Next time any local file is generated, that firm text is used instead of the universal version — no playbook change needed.

## Override Hierarchy

Playbooks can exist at four levels. Highest level wins (entity → group → firm → universal):

| Level | Location | Overrides |
|---|---|---|
| 1. Universal | `skills/prep-local-file/references/playbooks/` (this file) | — |
| 2. Firm | `.library/playbooks/` | Universal |
| 3. Group | `[Group]/.records/playbooks/` | Firm + Universal |
| 4. Entity | `[Group]/.records/playbooks/[entity-id]/` | All above |

Multiple playbooks can exist at the same level. The entity's local file record in `data.json` stores a `playbook` path preference. First run: Claude scans all levels, asks the user if multiple are found, saves the choice. Subsequent runs reuse the saved preference automatically.

Override playbooks use the same format. They can:
- Add sections (new rows with custom content sources)
- Remove sections (omit the row)
- Reorder sections within a chapter
- Change section titles
- Add instructions for specific sections
- Point to different content paths (e.g., `@library/custom-objective` instead of `@references/preamble/objective`)

## Sections

| Section ID | Title | Parent | Content Source | Instructions |
|---|---|---|---|---|
| executive-summary | Executive Summary | — | `@references/preamble/executive-summary` | |
| executive-summary/objective | Objective | executive-summary | `@references/preamble/objective` | |
| executive-summary/scope | Scope | executive-summary | `@references/preamble/scope` | |
| executive-summary/work-performed | Work Performed | executive-summary | `@references/preamble/work-performed` | |
| executive-summary/transactions-under-analysis | Transactions Under Analysis | executive-summary | (auto: transactions overview table) | |
| executive-summary/summary-of-results | Summary of Results | executive-summary | `@references/preamble/summary-of-results` | |

<!-- Future chapters — uncomment and populate as implemented

| business-description | Business Description | — | `@references/business/group-overview` | |
| business-description/group-overview | Group Overview | business-description | `@references/business/group-overview` | |
| business-description/org-structure | Organisational Structure | business-description | `@references/business/org-structure` | |
| business-description/mgmt-structure | Management Structure | business-description | `@references/business/mgmt-structure` | |
| business-description/local-business | Local Business Description | business-description | `@references/business/local-business` | |
| business-description/restructurings | Business Restructurings | business-description | `@references/business/restructurings` | |
| business-description/intangible-transfers | Intangible Property Transfers | business-description | `@references/business/intangible-transfers` | |

| industry-analysis | Industry Analysis | — | `@references/industry/overview` | |
| industry-analysis/overview | Industry Overview | industry-analysis | `@references/industry/industry-analysis` | |
| industry-analysis/value-drivers | Value Drivers | industry-analysis | `@references/industry/value-drivers` | |
| industry-analysis/key-competitors | Key Competitors | industry-analysis | `@references/industry/key-competitors` | |

| functional-analysis | Functional Analysis | — | (per-transaction from blueprint) | |
| economic-analysis | Economic Analysis | — | `@references/economic-analysis/economic-analysis` | |
| recognition | Recognition of Transactions | — | `@references/recognition/commercial-rationality` | |
| conclusion | Conclusion | — | `@references/recognition/conclusion` | |

-->
