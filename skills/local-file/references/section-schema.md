# Blueprint Section Schema

This defines the complete set of section keys for a local file blueprint, their naming conventions, and how they map to the report structure.

## Chapters Architecture (v0.6.0)

As of schema v0.6.0, the blueprint's `chapters[]` array is the authoritative source for report structure and section ordering. Each chapter groups related sections into a named container:

```json
{
  "id": "business-description",
  "title": "Business Description",
  "sections": ["executive_summary", "group_overview", "entity_introduction"]
}
```

- Chapters define the top-level headings in all output formats (HTML, LaTeX, PDF)
- Section order within a chapter is determined by the `sections` array, not by key prefix
- A section key must appear in exactly one chapter
- Sections not listed in any chapter are omitted from the report

The section key naming conventions below remain useful for readability and for identifying section purpose, but they no longer drive report structure.

### Footnotes

The `footnotes` object on the blueprint maps section keys to arrays of citation strings:

```json
"footnotes": {
  "preamble_objective": [
    "OECD Transfer Pricing Guidelines (2022), Chapter I, para. 1.6.",
    "Wet op de vennootschapsbelasting 1969, Article 8b."
  ]
}
```

Footnotes are rendered as numbered references at the bottom of the corresponding section.

## Naming Convention

Section keys use prefixes to indicate their category. These prefixes serve as naming conventions for readability and identification.

| Prefix | Category | Example |
|---|---|---|
| `preamble_` | Report Preamble | `preamble_objective` |
| `executive_summary` | Executive Summary | `executive_summary` |
| `group_overview` | Business Description | `group_overview` |
| `entity_introduction` | Business Description | `entity_introduction` |
| `management_` | Business Description | `management_structure` |
| `business_` | Business Description | `business_description` |
| `local_` | Business Description | `local_reporting` |
| `intangible_` | Business Description | `intangible_transfers` |
| `industry_analysis_` | Industry Analysis | `industry_analysis_primary` |
| `fp_` | Functional Analysis | `fp_limited_risk_distributor_functions` |
| `tx_` | Controlled Transactions | `tx_001_summary` |
| `bm_` | Benchmark Application | `bm_benchmark_a_conclusion` |
| `transactions_not_covered_` | Closing | `transactions_not_covered_intro` |
| `appendices` | Closing | `appendices` |

## Report Preamble

| Key | Label | Type | Typical Layer |
|---|---|---|---|
| `preamble_objective` | Objective | content | Layer 1 — standard boilerplate |
| `preamble_scope` | Scope | content | Layer 4 — entity-specific |
| `preamble_work_performed` | Work Performed | content | Layer 1 or 2 |
| `preamble_transactions_overview` | Transactions Under Analysis | auto | Script builds from data |
| `preamble_summary_of_results` | Summary of Results | content | Layer 1 template + data |

## Business Description

| Key | Label | Type | Typical Layer |
|---|---|---|---|
| `executive_summary` | Executive Summary | content | Layer 4 |
| `group_overview` | Group Overview | content | Layer 3 or 4 |
| `entity_introduction` | Entity Introduction | content | Composite (Layer 3 + 4) |
| `management_structure` | Management Structure | content | Layer 3 or 4 |
| `management_org_chart` | Organization Chart | content | Layer 4 |
| `local_reporting` | Local Reporting | content | Layer 4 |
| `business_description` | Business Description & Strategy | content | Layer 4 |
| `business_restructurings` | Business Restructurings | content | Layer 4 |
| `intangible_transfers` | Intangible Transfers | content | Layer 4 |

## Industry Analysis

Dynamic — depends on blueprint. Up to 3 industry analyses.

| Key pattern | Label | Type | Typical Layer |
|---|---|---|---|
| `industry_analysis_primary` | Primary Industry | content | Layer 2 or 3 |
| `industry_analysis_secondary` | Secondary Industry | content | Layer 2 or 3 |
| `industry_analysis_tertiary` | Tertiary Industry | content | Layer 2 or 3 |

## Functional Analysis

Dynamic — one set of 4 sections per unique functional profile in the covered transactions.

| Key pattern | Label | Type | Typical Layer |
|---|---|---|---|
| `fp_{slug}_overview` | [Profile Name] — Overview | content | Layer 2 or 3 |
| `fp_{slug}_functions` | [Profile Name] — Functions | content | Layer 2 or 3 |
| `fp_{slug}_assets` | [Profile Name] — Assets | content | Layer 2 or 3 |
| `fp_{slug}_risks` | [Profile Name] — Risks | content | Layer 2 or 3 |

Where `{slug}` matches the profile type slug (e.g., `limited_risk_distributor`, `full_fledged_manufacturer`).

## Controlled Transactions

Dynamic — one set per covered transaction. Transaction ID uses underscores (e.g., `tx_001`).

| Key pattern | Label | Type | Typical Layer |
|---|---|---|---|
| `tx_{id}_summary` | Transaction Summary | content | Layer 4 |
| `tx_{id}_contractual_terms_intro` | Contractual Terms — Intro | content | Layer 1 or 4 |
| `tx_{id}_contractual_terms` | Contractual Terms — Table | auto | Data-driven |
| `tx_{id}_characteristics_intro` | Characteristics — Intro | content | Layer 1 or 4 |
| `tx_{id}_characteristics` | Characteristics — Table | auto | Data-driven (conditional) |
| `tx_{id}_economic_circumstances_intro` | Economic Circumstances — Intro | content | Layer 1 or 4 |
| `tx_{id}_economic_circumstances` | Economic Circumstances — Table | auto | Data-driven |
| `tx_{id}_business_strategies` | Business Strategies | content | Layer 4 |
| `tx_{id}_far_variations` | FAR Variations | content | Layer 4 |
| `tx_{id}_recognition` | Recognition Analysis | content | Layer 4 |
| `tx_{id}_recognition_specific` | Type-specific Test | content | Layer 4 (conditional) |
| `tx_{id}_recognition_conclusion` | Recognition Conclusion | content | Layer 4 |
| `tx_{id}_method_selection` | Method Selection | content | Layer 2 or 4 |
| `tx_{id}_application_intro` | Application Introduction | content | Layer 4 |
| `tx_{id}_conclusion` | Transaction Conclusion | content | Layer 4 |

## Benchmark Application

Dynamic — one set per benchmark used by covered transactions.

| Key pattern | Label | Type | Typical Layer |
|---|---|---|---|
| `bm_{id}_allocation_intro` | Allocation — Intro | content | Layer 4 |
| `bm_{id}_allocation` | Allocation — Table | auto | Data-driven |
| `bm_{id}_search_strategy_intro` | Search Strategy — Intro | content | Layer 2 or 4 |
| `bm_{id}_search_strategy` | Search Strategy — Table | auto | Data-driven |
| `bm_{id}_search_results_intro` | Search Results — Intro | content | Layer 2 or 4 |
| `bm_{id}_search_results` | Search Results — Table | auto | Data-driven |
| `bm_{id}_adjustments_intro` | Comparability Adjustments — Intro | content | Layer 4 |
| `bm_{id}_adjustments` | Comparability Adjustments — Table | auto | Data-driven |
| `bm_{id}_conclusion` | Benchmark Conclusion | content | Layer 4 |

## Closing

| Key | Label | Type | Typical Layer |
|---|---|---|---|
| `transactions_not_covered_intro` | Transactions Not Covered — Intro | content | Layer 1 or 4 |
| `transactions_not_covered` | Not Covered — Table | auto | Data-driven |
| `appendices` | Appendices | content | Layer 4 |

## Section Types

- **content** — Text authored by the user or pulled from content layers. Stored in the blueprint's `sections` object. Editable in the section editor.
- **auto** — Generated by the assembly script from structured data (transactions, benchmarks, contractual terms). NOT stored in the blueprint. Read-only in the section editor.

## Category Detection (Legacy)

> **Note:** As of v0.6.0, `chapters[]` is the authoritative source for report structure. Prefix-based category detection is retained for backward compatibility with v0.5.0 blueprints that lack a `chapters` array.

The assembly script detects categories from key prefixes:

```python
if key.startswith('preamble_'):          → "Report Preamble"
if key in BUSINESS_KEYS or ...:          → "Business Description"
if key.startswith('industry_analysis_'): → "Industry Analysis"
if key.startswith('fp_'):                → "Functional Analysis"
if key.startswith('tx_'):                → "Controlled Transactions"
if key.startswith('bm_'):                → "Benchmark Application"
if key.startswith('transactions_not_'):  → "Closing"
else:                                    → "Other"
```
