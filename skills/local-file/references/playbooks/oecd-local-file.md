# OECD Local File Playbook

Standard playbook for an OECD-compliant transfer pricing local file. Defines sections, ordering, and content sources for each section.

## How to Read This Playbook

- **Section ID**: Kebab-case identifier. Nested IDs use `/` (e.g., `executive-summary/objective`).
- **Title**: Display title for the section header.
- **Parent**: Parent section ID, or `—` for top-level chapters.
- **Content Sources**: Where Claude pulls content. Prefixes: `@references/` (Layer 1 universal), `@library/` (Layer 2 firm), `@group/` (Layer 3), `@entity/` (Layer 4). `(auto)` means Claude builds from structured data.

## Firm Override

A firm can create `.library/playbooks/my-firm.md` in the same format. When present, it takes precedence over this standard playbook. Firm playbooks can:
- Add `@library/` content sources to any section (appended after standard sources)
- Reorder sections within a chapter
- Add firm-specific sections
- Remove sections by omitting them

## Sections

| Section ID | Title | Parent | Content Sources |
|---|---|---|---|
| executive-summary | Executive Summary | — | `@references/preamble/executive-summary` |
| executive-summary/objective | Objective | executive-summary | `@references/preamble/objective` |
| executive-summary/scope | Scope | executive-summary | `@references/preamble/scope` |
| executive-summary/work-performed | Work Performed | executive-summary | `@references/preamble/work-performed` |
| executive-summary/transactions-under-analysis | Transactions Under Analysis | executive-summary | (auto: transactions overview table) |
| executive-summary/summary-of-results | Summary of Results | executive-summary | `@references/preamble/summary-of-results` |

<!-- Future chapters — uncomment and populate as implemented

| business-description | Business Description | — | `@references/business/group-overview` |
| business-description/group-overview | Group Overview | business-description | `@references/business/group-overview` |
| business-description/org-structure | Organisational Structure | business-description | `@references/business/org-structure` |
| business-description/mgmt-structure | Management Structure | business-description | `@references/business/mgmt-structure` |
| business-description/local-business | Local Business Description | business-description | `@references/business/local-business` |
| business-description/restructurings | Business Restructurings | business-description | `@references/business/restructurings` |
| business-description/intangible-transfers | Intangible Property Transfers | business-description | `@references/business/intangible-transfers` |

| industry-analysis | Industry Analysis | — | `@references/industry/overview` |
| industry-analysis/overview | Industry Overview | industry-analysis | `@references/industry/industry-analysis` |
| industry-analysis/value-drivers | Value Drivers | industry-analysis | `@references/industry/value-drivers` |
| industry-analysis/key-competitors | Key Competitors | industry-analysis | `@references/industry/key-competitors` |

| functional-analysis | Functional Analysis | — | (per-transaction from blueprint) |
| economic-analysis | Economic Analysis | — | `@references/economic-analysis/economic-analysis` |
| recognition | Recognition of Transactions | — | `@references/recognition/commercial-rationality` |
| conclusion | Conclusion | — | `@references/recognition/conclusion` |

-->
