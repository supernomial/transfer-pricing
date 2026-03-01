#!/usr/bin/env python3
"""Generate a PDF local file from a view JSON and LaTeX template.

Reads the view JSON (which has all content already resolved), renders it into
LaTeX sections using the chapters/elements structure, populates the template,
and compiles to PDF via pdflatex.
"""

import argparse
import json
import os
import re
import subprocess
import sys


# ---------------------------------------------------------------------------
# LaTeX escaping
# ---------------------------------------------------------------------------

def escape_latex(text):
    """Escape special LaTeX characters in text."""
    if not isinstance(text, str):
        return str(text)
    replacements = {
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    return text


# ---------------------------------------------------------------------------
# Auto table rendering
# ---------------------------------------------------------------------------

def render_auto_table(auto_table):
    """Render an auto_table object as a LaTeX tabularx table."""
    columns = auto_table.get('columns', [])
    rows = auto_table.get('rows', [])
    if not columns or not rows:
        return ''

    ncols = len(columns)
    # First column is X (flexible), rest are l (left-aligned)
    col_spec = 'X' + 'l' * (ncols - 1) if ncols > 1 else 'X'

    parts = [f'\\begin{{tabularx}}{{\\textwidth}}{{{col_spec}}}']
    parts.append('\\toprule')
    parts.append(' & '.join(escape_latex(c) for c in columns) + ' \\\\')
    parts.append('\\midrule')
    for row in rows:
        parts.append(' & '.join(escape_latex(str(cell)) for cell in row) + ' \\\\')
    parts.append('\\bottomrule')
    parts.append('\\end{tabularx}')
    return '\n'.join(parts)


# ---------------------------------------------------------------------------
# Element rendering
# ---------------------------------------------------------------------------

def render_element(element):
    """Render a single element as LaTeX content."""
    if not element:
        return ''

    # Auto table sections
    if element.get('is_auto') and 'auto_table' in element:
        return render_auto_table(element['auto_table'])

    # Composite sections (multiple parts)
    if element.get('composite') and 'parts' in element:
        part_texts = []
        for part in element['parts']:
            text = part.get('text', '')
            if text:
                part_texts.append(escape_latex(text))
        return '\n\n'.join(part_texts)

    # Standard text sections
    text = element.get('text', '')
    if not text or text.startswith('[No ') or text.startswith('[UNRESOLVED'):
        return ''
    return escape_latex(text)


# ---------------------------------------------------------------------------
# Report body generation
# ---------------------------------------------------------------------------

def render_keys(keys, elements, parts):
    """Render all element keys and append to parts list."""
    for key in keys:
        element = elements.get(key)
        if not element:
            continue
        content = render_element(element)
        if content:
            parts.append(content)
            parts.append('')


def build_report_body(view_json):
    """Build the complete LaTeX report body from view JSON chapters and elements."""
    chapters = view_json.get('chapters', [])
    elements = view_json.get('elements', {})
    parts = []

    for chapter in chapters:
        chapter_title = chapter.get('title', '')
        parts.append(f'\\section{{{escape_latex(chapter_title)}}}')

        # Chapter-level content
        render_keys(chapter.get('keys', []), elements, parts)

        for section in chapter.get('sections', []):
            sec_title = section.get('title', '')
            parts.append(f'\\subsection{{{escape_latex(sec_title)}}}')

            # Section-level content
            render_keys(section.get('keys', []), elements, parts)

            for subsec in section.get('subsections', []):
                subsec_title = subsec.get('title', '')
                parts.append(f'\\subsubsection{{{escape_latex(subsec_title)}}}')

                # Subsection-level content
                render_keys(subsec.get('keys', []), elements, parts)

    return '\n'.join(parts)


# ---------------------------------------------------------------------------
# PDF compilation
# ---------------------------------------------------------------------------

def compile_pdf(tex_path, output_dir):
    """Compile a .tex file to PDF using pdflatex (two passes for TOC)."""
    try:
        for pass_num in range(1, 3):
            print(f"  pdflatex pass {pass_num}/2...")
            result = subprocess.run(
                ['pdflatex', '-interaction=nonstopmode',
                 '-output-directory', output_dir, tex_path],
                capture_output=True
            )
            if result.returncode != 0:
                log_text = result.stdout.decode('utf-8', errors='replace')
                print(f"Error compiling PDF. LaTeX log:\n{log_text}", file=sys.stderr)
                sys.exit(1)
        print("PDF compiled successfully")
    except FileNotFoundError:
        print("Error: pdflatex not found on PATH.", file=sys.stderr)
        print("  If on macOS: brew install --cask basictex && eval \"$(/usr/libexec/path_helper)\"",
              file=sys.stderr)
        sys.exit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='Generate PDF from view JSON')
    parser.add_argument('--view-json', required=True, help='Path to view JSON file')
    parser.add_argument('--template', required=True, help='Path to local_file.tex template')
    parser.add_argument('--output', required=True, help='Output file path for the PDF')
    args = parser.parse_args()

    # Read view JSON
    with open(args.view_json, 'r') as f:
        view_json = json.load(f)

    # Read LaTeX template
    with open(args.template, 'r') as f:
        template = f.read()

    # Extract document metadata
    doc = view_json.get('document', {})
    entity_name = doc.get('entity_name', doc.get('subtitle', 'Unknown Entity'))
    fiscal_year = doc.get('fiscal_year', 'N/A')

    # Populate template
    latex = template
    latex = latex.replace('<<ENTITY_NAME>>', escape_latex(entity_name))
    latex = latex.replace('<<FISCAL_YEAR>>', str(fiscal_year))
    latex = latex.replace('<<REPORT_BODY>>', build_report_body(view_json))

    # Derive paths from output file path
    output_dir = os.path.dirname(args.output) or '.'
    os.makedirs(output_dir, exist_ok=True)
    tex_path = args.output.replace('.pdf', '.tex')
    with open(tex_path, 'w') as f:
        f.write(latex)
    print(f"LaTeX written to {tex_path}")

    # Compile to PDF
    compile_pdf(tex_path, output_dir)

    print(f"PDF written to {args.output}")


if __name__ == '__main__':
    main()
