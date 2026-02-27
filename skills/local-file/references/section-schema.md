# Blueprint Section Schema

This defines the blueprint architecture, section key conventions, and how templates and entity blueprints work together.

## Template vs Entity Blueprint (v0.7.0)

As of schema v0.7.0, there are two blueprint types:

### Universal Template

Lives in `skills/local-file/references/blueprints/`. Defines the complete OECD Local File structure using a recursive `sections[]` / `children[]` hierarchy. Every node has an `id` (kebab-case) and `title`.

```json
{
  "schema_version": "0.7.0",
  "template_type": "universal",
  "document": "OECD Local File",
  "sections": [
    {
      "id": "executive-summary",
      "title": "Executive Summary",
      "children": [
        { "id": "objective", "title": "Objective" },
        { "id": "scope", "title": "Scope" }
      ]
    }
  ],
  "dynamic_templates": { ... }
}
```

- **`children[]`** — recursive array of child nodes (N-level depth)
- **`dynamic: true`** — marks sections that are included/excluded per entity (functional profiles, transaction categories)
- **`dynamic_templates`** — reusable child structures: `functional-profile` (4 children) and `transaction` (6 children)

### Firm Blueprint

Lives in `[working-folder]/.library/blueprints/`. Saves reusable firm-level report structures that pre-populate new entity blueprints.

```json
{
  "schema_version": "0.7.0",
  "template_type": "firm",
  "template_name": "Deloitte Standard Local File",
  "based_on": "oecd-local-file",
  "created": "2026-02-27",
  "default_covered_profiles": ["full-fledged-distributor", "limited-risk-distributor"],
  "default_covered_transactions": ["services", "goods"],
  "content": {
    "executive-summary/objective": ["@references/preamble/objective", "@library/preamble/firm-addendum"],
    "executive-summary/scope": ["@references/preamble/scope"],
    "business-description/group-overview": ["@library/business/group-overview"],
    "industry-analysis/industry-overview": []
  },
  "title_overrides": {},
  "section_notes": {
    "business-description/group-overview": "Always lead with global footprint."
  }
}
```

- **`template_type`** — `"firm"` distinguishes from universal templates and entity blueprints
- **`template_name`** — human-readable name shown in the blueprint picker
- **`based_on`** — always `"oecd-local-file"` (inherits universal structure)
- **`created`** — ISO date when the firm blueprint was saved
- **`default_covered_profiles`** — advisory list of profiles the firm commonly documents (suggested during intake, not enforced)
- **`default_covered_transactions`** — advisory list of transaction categories (same)
- **`content`** — path-style keys with only `@references/` and `@library/` content. Sections stripped of group/entity/inline content become `[]` (empty)
- **`title_overrides`** — firm-wide section title customizations
- **`section_notes`** — editorial guidance per section

Firm blueprints are created by stripping an entity blueprint (see `commands/prep-local-file.md` Notes section for stripping rules). Content is copied into entity blueprints at creation time — the assembly script never resolves firm blueprints directly.

### Entity Blueprint

Lives in `[Group]/.records/blueprints/`. Inherits structure from a template via `based_on`.

```json
{
  "schema_version": "0.7.0",
  "based_on": "oecd-local-file",
  "entity": "solara-dist-fr",
  "covered_profiles": ["full-fledged-distributor"],
  "covered_transactions": ["services", "loan-arrangements"],
  "content": {
    "executive-summary/objective": ["@references/preamble/objective"],
    "economic-analysis/functional-analysis/full-fledged-distributor/overview": ["@entity/fp-ffd-overview.md"]
  }
}
```

- **`based_on`** — template id to inherit from
- **`covered_profiles`** — which of the 22 functional profiles this entity uses
- **`covered_transactions`** — which of the 14 transaction categories apply
- **`content`** — path-style keys mapping to arrays of content layer references. **Convention:** Always include chapter-level keys (e.g., `"executive-summary"`, `"business-description"`) pointing to their intro reference files. These render between the chapter heading and the first subsection.
- **`section_notes`** — editorial reasoning per section (path-style keys)
- **`footnotes`** — per-section citation arrays (path-style keys)
- **`firm_blueprint`** — (optional) slug of the firm blueprint used as starting point (informational, script ignores it)

## Path-Style Keys

Content keys use `/`-separated ids matching the template hierarchy:

| Pattern | Example |
|---|---|
| `{chapter}/{section}` | `executive-summary/objective` |
| `{chapter}/{section}/{subsection}` | `business-description/group-overview/organizational-structure` |
| `{chapter}/{parent}/{profile}/{child}` | `economic-analysis/functional-analysis/full-fledged-distributor/overview` |
| `{chapter}/{transaction-cat}/{child}` | `economic-analysis/services/summary` |

The assembly script resolves these paths against the template's `id` tree to determine headings and numbering.

## Content Layers

Content values in the `content` object are arrays. Each element is resolved independently and concatenated:

| Prefix | Layer | Source |
|---|---|---|
| `@references/` | 1 — Universal | Plugin `skills/local-file/references/` |
| `@library/` | 2 — Firm library | Working dir `.library/` |
| `@group/` | 3 — Group-level | `[Group]/.records/content/` |
| `@entity/` | 4 — Entity files | `[Group]/.records/content/[entity-id]/` |
| (plain text) | 5 — Inline | Directly in the blueprint |

Each layer overrides the one above. Arrays enable composite sections from multiple layers.

**All content paths must resolve to individual `.md` files, never directories.** For example, use `@references/recognition/commercial-rationality`, not `@references/recognition`.

### Entity Content Files

Entity content files are Markdown files with YAML frontmatter stored in `[Group]/.records/content/[entity-id]/`:

```markdown
---
title: Industry Overview — France
section: industry-analysis/industry-overview
---

Content text here...
```

Frontmatter fields:
- **title** — display title for the content block
- **section** — path-style key this content maps to

Referenced in blueprints as `@entity/filename.md`.

## Footnotes

The `footnotes` object maps path-style keys to arrays of citation strings:

```json
"footnotes": {
  "executive-summary/objective": [
    "OECD Transfer Pricing Guidelines (2022), Chapter I, para. 1.6.",
    "Wet op de vennootschapsbelasting 1969, Article 8b."
  ]
}
```

Footnotes are rendered as numbered references at the bottom of the corresponding section.

## Legacy Naming Convention (v0.6.0)

> **Note:** As of v0.7.0, path-style keys are the primary format. The underscore-prefix conventions below are retained for backward compatibility with v0.6.0 blueprints.

| Prefix | Category | Example |
|---|---|---|
| `preamble_` | Report Preamble | `preamble_objective` |
| `executive_summary` | Executive Summary | `executive_summary` |
| `group_overview` | Business Description | `group_overview` |
| `fp_` | Functional Analysis | `fp_limited_risk_distributor_functions` |
| `tx_` | Controlled Transactions | `tx_001_summary` |
| `bm_` | Benchmark Application | `bm_benchmark_a_conclusion` |
| `transactions_not_covered_` | Closing | `transactions_not_covered_intro` |
| `appendices` | Closing | `appendices` |

## Section Types

- **content** — Text authored by the user or pulled from content layers. Stored in the blueprint's `content` object. Editable in the section editor.
- **auto** — Generated by the assembly script from structured data (transactions, benchmarks, contractual terms). NOT stored in the blueprint. Read-only in the section editor.

## Dynamic Sections

Sections marked `dynamic: true` in the template are pruned based on the entity blueprint:

- **Functional profiles** (`functional-analysis` children): Only profiles listed in `covered_profiles` are included
- **Transaction categories** (`economic-analysis` children after functional-analysis): Only categories listed in `covered_transactions` are included

After pruning, numbering is recalculated from array positions.

The `dynamic_templates` object defines the standard children for each dynamic type:

| Template | Children |
|---|---|
| `functional-profile` | overview, functions, assets, risks |
| `transaction` | summary, commercial-relations, recognition, tp-methods, method-selection, application |

## Category Detection (Legacy)

> **Note:** As of v0.7.0, the template's `sections[]`/`children[]` hierarchy is the authoritative source for report structure. Prefix-based category detection is retained for backward compatibility with v0.5.0/v0.6.0 blueprints.

The assembly script detects categories from key prefixes:

```python
if key.startswith('preamble_'):          -> "Report Preamble"
if key in BUSINESS_KEYS or ...:          -> "Business Description"
if key.startswith('industry_analysis_'): -> "Industry Analysis"
if key.startswith('fp_'):                -> "Functional Analysis"
if key.startswith('tx_'):                -> "Controlled Transactions"
if key.startswith('bm_'):               -> "Benchmark Application"
if key.startswith('transactions_not_'):  -> "Closing"
else:                                    -> "Other"
```
