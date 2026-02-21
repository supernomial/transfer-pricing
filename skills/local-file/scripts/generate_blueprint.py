#!/usr/bin/env python3
"""
Generate a transfer pricing local file blueprint from group records.

Given a group records JSON, an entity ID, and a set of transactions,
this script auto-generates a complete blueprint JSON with all sections
ordered per the section schema.

The blueprint contains only content-type sections. Auto-type sections
(e.g. contractual_terms tables, search_strategy tables) are omitted —
those are generated at assembly time by the assembly script.

Usage:
    python3 generate_blueprint.py \
        --data path/to/group.json \
        --entity acme-nl \
        --fiscal-year 2024 \
        --transactions tx-001,tx-002,tx-003 \
        --output path/to/blueprint.json

    python3 generate_blueprint.py --example --output path/to/blueprint.json

Why a script and not Claude:
    - Deterministic: same input always produces same output
    - Consistent: every blueprint follows the exact section schema
    - Fast: no AI tokens spent on structural scaffolding
"""

import argparse
import json
import os
import sys


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_json(path):
    """Load and return a JSON file."""
    if not os.path.exists(path):
        print(f"Error: File not found: {path}", file=sys.stderr)
        sys.exit(1)
    with open(path, 'r') as f:
        return json.load(f)


def find_entity(data, entity_id):
    """Find an entity by ID in the records."""
    for entity in data.get('entities', []):
        if entity.get('id') == entity_id:
            return entity
    print(f"Error: Entity '{entity_id}' not found in records.", file=sys.stderr)
    available = [e.get('id') for e in data.get('entities', [])]
    if available:
        print(f"  Available entities: {', '.join(available)}", file=sys.stderr)
    sys.exit(1)


def find_transactions(data, tx_ids):
    """Find transactions by ID list. Returns list in same order as tx_ids."""
    tx_map = {tx['id']: tx for tx in data.get('transactions', [])}
    result = []
    for tx_id in tx_ids:
        if tx_id in tx_map:
            result.append(tx_map[tx_id])
        else:
            print(f"Warning: Transaction '{tx_id}' not found in records.", file=sys.stderr)
    return result


def get_entity_transactions(data, entity_id):
    """Get all transactions involving this entity."""
    return [
        tx for tx in data.get('transactions', [])
        if tx.get('from_entity') == entity_id or tx.get('to_entity') == entity_id
    ]


def slug_to_underscores(slug):
    """Convert a hyphenated slug to underscores: 'tx-001' -> 'tx_001'."""
    return slug.replace('-', '_')


def humanize_profile(profile_slug):
    """Convert a profile slug to a human-readable name.

    'limited-risk-distributor' -> 'Limited Risk Distributor'
    """
    return profile_slug.replace('-', ' ').title()


# Financial transaction types that omit characteristics
FINANCIAL_TYPES = {
    'loan-arrangement', 'cash-pooling', 'financial-guarantees',
    'factoring', 'hybrid-instruments', 'asset-management',
}

# Known TP methods that map to reference files
METHOD_REFERENCES = {
    'tnmm': '@references/methods/tnmm',
    'cup': '@references/methods/cup',
    'cost-plus': '@references/methods/cost-plus',
    'resale-price': '@references/methods/resale-price',
    'profit-split': '@references/methods/profit-split',
    'valuation': '@references/methods/valuation',
}


# ---------------------------------------------------------------------------
# Section generators
# ---------------------------------------------------------------------------

def generate_preamble_sections():
    """Generate the Report Preamble sections (content type only)."""
    return {
        'preamble_objective': '@references/preamble/objective',
        'preamble_scope': '[Scope]',
        'preamble_work_performed': '@references/preamble/work-performed',
        'preamble_summary_of_results': '[Summary of Results]',
    }


def generate_business_description_sections():
    """Generate the Business Description sections."""
    return {
        'executive_summary': '[Executive Summary]',
        'group_overview': '[Group Overview]',
        'entity_introduction': '[Entity Introduction]',
        'management_structure': '[Management Structure]',
        'management_org_chart': '[Organization Chart]',
        'local_reporting': '[Local Reporting]',
        'business_description': '[Business Description]',
        'business_restructurings': '[Business Restructurings]',
        'intangible_transfers': '[Intangible Transfers]',
    }


def generate_industry_sections():
    """Generate the Industry Analysis sections."""
    return {
        'industry_analysis_primary': '[Industry Analysis]',
    }


def generate_functional_analysis_sections(transactions):
    """Generate Functional Analysis sections for each unique profile.

    Collects all unique functional profiles (from_entity_profile and
    to_entity_profile) across the covered transactions, then generates
    4 content sections per profile.
    """
    seen = []
    for tx in transactions:
        for profile in [tx.get('from_entity_profile'), tx.get('to_entity_profile')]:
            if profile and profile not in seen:
                seen.append(profile)

    sections = {}
    for profile in seen:
        slug = slug_to_underscores(profile)
        name = humanize_profile(profile)
        sections[f'fp_{slug}_overview'] = f'[{name} -- Overview]'
        sections[f'fp_{slug}_functions'] = f'[{name} -- Functions]'
        sections[f'fp_{slug}_assets'] = f'[{name} -- Assets]'
        sections[f'fp_{slug}_risks'] = f'[{name} -- Risks]'

    return sections


def generate_transaction_sections(transactions):
    """Generate Controlled Transactions sections for each transaction.

    Emits content-type sections only. Auto-type sections (contractual_terms,
    characteristics, economic_circumstances) are omitted.
    """
    sections = {}
    for tx in transactions:
        tx_id = slug_to_underscores(tx['id'])
        tx_type = tx.get('transaction_type', '')
        is_financial = tx_type in FINANCIAL_TYPES

        sections[f'{tx_id}_summary'] = '[Summary]'
        sections[f'{tx_id}_contractual_terms_intro'] = '[Contractual Terms]'
        # OMIT {tx_id}_contractual_terms — auto type

        if not is_financial:
            sections[f'{tx_id}_characteristics_intro'] = '[Characteristics]'
            # OMIT {tx_id}_characteristics — auto type

        sections[f'{tx_id}_economic_circumstances_intro'] = '[Economic Circumstances]'
        # OMIT {tx_id}_economic_circumstances — auto type

        sections[f'{tx_id}_business_strategies'] = '[Business Strategies]'
        sections[f'{tx_id}_far_variations'] = '[FAR Variations]'
        sections[f'{tx_id}_recognition'] = '[Recognition Analysis]'
        sections[f'{tx_id}_recognition_specific'] = '[Type-specific Test]'
        sections[f'{tx_id}_recognition_conclusion'] = '[Recognition Conclusion]'

        # Method selection — map to reference if known
        tp_method = tx.get('tp_method', '')
        method_ref = METHOD_REFERENCES.get(tp_method, '[Method Selection]')
        sections[f'{tx_id}_method_selection'] = method_ref

        sections[f'{tx_id}_application_intro'] = '[Application Introduction]'
        sections[f'{tx_id}_conclusion'] = '[Conclusion]'

    return sections


def generate_benchmark_sections(transactions, data):
    """Generate Benchmark Application sections for each unique benchmark.

    Collects unique benchmark IDs from the covered transactions, then
    generates content-type sections per benchmark. Auto-type sections
    (allocation, search_strategy, search_results, adjustments) are omitted.
    """
    seen = []
    for tx in transactions:
        bm_id = tx.get('benchmark')
        if bm_id and bm_id not in seen:
            seen.append(bm_id)

    sections = {}
    for bm_id in seen:
        slug = slug_to_underscores(bm_id)
        sections[f'bm_{slug}_allocation_intro'] = '[Allocation]'
        # OMIT bm_{slug}_allocation — auto type
        sections[f'bm_{slug}_search_strategy_intro'] = '[Search Strategy]'
        # OMIT bm_{slug}_search_strategy — auto type
        sections[f'bm_{slug}_search_results_intro'] = '[Search Results]'
        # OMIT bm_{slug}_search_results — auto type
        sections[f'bm_{slug}_adjustments_intro'] = '[Comparability Adjustments]'
        # OMIT bm_{slug}_adjustments — auto type
        sections[f'bm_{slug}_conclusion'] = '[Benchmark Conclusion]'

    return sections


def generate_closing_sections():
    """Generate the Closing sections (content type only)."""
    return {
        'transactions_not_covered_intro': '[Transactions Not Covered]',
        # OMIT transactions_not_covered — auto type
        'appendices': '[Appendices]',
    }


# ---------------------------------------------------------------------------
# Blueprint assembly
# ---------------------------------------------------------------------------

def generate_blueprint(data, entity_id, fiscal_year, transactions):
    """Generate a complete blueprint JSON structure.

    Walks the section schema in order and generates all content-type
    sections for the given entity and transactions.
    """
    group = data.get('group', {})
    group_id = group.get('id', '') if isinstance(group, dict) else str(group)

    sections = {}
    sections.update(generate_preamble_sections())
    sections.update(generate_business_description_sections())
    sections.update(generate_industry_sections())
    sections.update(generate_functional_analysis_sections(transactions))
    sections.update(generate_transaction_sections(transactions))
    sections.update(generate_benchmark_sections(transactions, data))
    sections.update(generate_closing_sections())

    return {
        'schema_version': '0.5.0',
        'group': group_id,
        'entity': entity_id,
        'deliverable': 'local-file',
        'fiscal_year': str(fiscal_year),
        'sections': sections,
        'section_notes': {},
    }


# ---------------------------------------------------------------------------
# --example flag logic
# ---------------------------------------------------------------------------

def pick_example_defaults(data):
    """Pick sensible defaults for --example mode.

    Returns (entity_id, fiscal_year, transaction_ids).
    """
    # Prefer entity with a local_file record
    local_files = data.get('local_files', [])
    if local_files:
        lf = local_files[0]
        entity_id = lf.get('entity')
        fiscal_year = lf.get('fiscal_year', '2024')
        covered = lf.get('covered_transactions', [])
        if covered:
            return entity_id, fiscal_year, covered

    # Fallback: first entity, pick 2-3 transactions covering at least 2 types
    entities = data.get('entities', [])
    if not entities:
        print("Error: No entities found in sample data.", file=sys.stderr)
        sys.exit(1)

    entity_id = entities[0]['id']
    entity_txs = get_entity_transactions(data, entity_id)

    if not entity_txs:
        print(f"Error: No transactions found for entity '{entity_id}'.", file=sys.stderr)
        sys.exit(1)

    # Pick transactions covering at least 2 types, up to 3 total
    selected = []
    types_seen = set()
    for tx in entity_txs:
        tx_type = tx.get('transaction_type', '')
        if len(selected) < 3 or (tx_type not in types_seen and len(types_seen) < 2):
            selected.append(tx['id'])
            types_seen.add(tx_type)
        if len(selected) >= 3 and len(types_seen) >= 2:
            break

    return entity_id, '2024', selected


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description='Generate a transfer pricing local file blueprint from group records'
    )
    parser.add_argument('--data', help='Path to group records JSON')
    parser.add_argument('--entity', help='Entity ID to generate blueprint for')
    parser.add_argument('--fiscal-year', help='Fiscal year')
    parser.add_argument('--transactions',
                        help='Comma-separated transaction IDs, or "all"')
    parser.add_argument('--output', help='Output file path for blueprint JSON')
    parser.add_argument('--example', action='store_true',
                        help='Use sample data with default entity and transactions')
    args = parser.parse_args()

    # --- Resolve data path ---
    if args.example:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        plugin_root = os.path.dirname(os.path.dirname(os.path.dirname(script_dir)))
        data_path = os.path.join(plugin_root, 'data', 'examples', 'sample-group.json')
        if not os.path.exists(data_path):
            print(f"Error: Sample data not found at {data_path}", file=sys.stderr)
            sys.exit(1)
    elif args.data:
        data_path = args.data
    else:
        print("Error: Either --data or --example is required.", file=sys.stderr)
        sys.exit(1)

    print(f"Loading records: {data_path}")
    data = load_json(data_path)

    # --- Resolve entity, fiscal year, transactions ---
    if args.example:
        entity_id, fiscal_year, tx_ids = pick_example_defaults(data)
        # Allow overrides even in example mode
        if args.entity:
            entity_id = args.entity
        if args.fiscal_year:
            fiscal_year = args.fiscal_year
        if args.transactions:
            if args.transactions == 'all':
                tx_ids = [tx['id'] for tx in get_entity_transactions(data, entity_id)]
            else:
                tx_ids = [t.strip() for t in args.transactions.split(',')]
        print(f"Example mode: entity={entity_id}, fiscal_year={fiscal_year}, "
              f"transactions={', '.join(tx_ids)}")
    else:
        if not args.entity:
            print("Error: --entity is required (or use --example).", file=sys.stderr)
            sys.exit(1)
        if not args.fiscal_year:
            print("Error: --fiscal-year is required (or use --example).", file=sys.stderr)
            sys.exit(1)
        entity_id = args.entity
        fiscal_year = args.fiscal_year
        if not args.transactions:
            print("Error: --transactions is required (or use --example).", file=sys.stderr)
            sys.exit(1)
        if args.transactions == 'all':
            tx_ids = [tx['id'] for tx in get_entity_transactions(data, entity_id)]
        else:
            tx_ids = [t.strip() for t in args.transactions.split(',')]

    # --- Validate entity exists ---
    find_entity(data, entity_id)

    # --- Load transactions ---
    transactions = find_transactions(data, tx_ids)
    if not transactions:
        print("Error: No valid transactions found.", file=sys.stderr)
        sys.exit(1)
    print(f"Generating blueprint for {entity_id} with {len(transactions)} transaction(s)")

    # --- Generate blueprint ---
    blueprint = generate_blueprint(data, entity_id, fiscal_year, transactions)

    # --- Output ---
    output_json = json.dumps(blueprint, indent=2, ensure_ascii=False)

    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, 'w') as f:
            f.write(output_json)
            f.write('\n')
        print(f"\nDone! Blueprint written to: {args.output}")
        print(f"  Sections: {len(blueprint['sections'])}")
    else:
        print(output_json)


if __name__ == '__main__':
    main()
