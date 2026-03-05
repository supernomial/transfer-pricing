#!/usr/bin/env python3
"""Generate a PDF local file from a view JSON and LaTeX template.

Reads the view JSON (which has all content already resolved), renders it into
LaTeX sections using the chapters/elements structure, populates the template,
and compiles to PDF via pdflatex.

If pdflatex is not installed, automatically installs TinyTeX to
[working_dir]/.supernomial/latex/ for a portable LaTeX environment.
"""

import argparse
import glob
import json
import os
import platform
import re
import shutil
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
        '\\': r'\textbackslash{}',
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
    # All columns use X (flexible width) for even distribution
    col_spec = 'X' * ncols

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
# TinyTeX auto-install
# ---------------------------------------------------------------------------

TINYTEX_PACKAGES = [
    'booktabs', 'tabularx', 'longtable', 'fancyhdr', 'hyperref',
    'parskip', 'geometry', 'lmodern', 'titlesec', 'xcolor',
    'tools', 'etoolbox', 'url',
]


def _find_working_dir(output_path):
    """Derive the user's working directory from the output path.

    The output path is inside the user's group folder, e.g.:
    /Users/joe/Transfer Pricing/Acme/4. Deliverables/FY2024/.../report.pdf
    The working dir is the root that contains .supernomial/ — walk up until found,
    or fall back to two levels above the output file.
    """
    d = os.path.dirname(os.path.abspath(output_path))
    while d != os.path.dirname(d):  # stop at filesystem root
        if os.path.isdir(os.path.join(d, '.supernomial')):
            return d
        d = os.path.dirname(d)
    # Fallback: go up from output dir until we find a reasonable root
    return os.path.dirname(os.path.dirname(os.path.abspath(output_path)))


def _local_pdflatex(working_dir):
    """Return path to locally installed pdflatex, or None."""
    base = os.path.join(working_dir, '.supernomial', 'latex')
    # TinyTeX puts binaries in bin/<platform>/
    candidates = glob.glob(os.path.join(base, 'bin', '*', 'pdflatex'))
    if candidates:
        return candidates[0]
    # Also check direct bin/
    direct = os.path.join(base, 'bin', 'pdflatex')
    if os.path.isfile(direct):
        return direct
    return None


def _install_tinytex(working_dir):
    """Download and install TinyTeX to .supernomial/latex/."""
    latex_dir = os.path.join(working_dir, '.supernomial', 'latex')
    os.makedirs(latex_dir, exist_ok=True)

    system = platform.system()
    print("Installing LaTeX (TinyTeX) for PDF generation... this may take a minute.")

    try:
        if system == 'Darwin' or system == 'Linux':
            env = os.environ.copy()
            env['TINYTEX_DIR'] = latex_dir
            result = subprocess.run(
                ['sh', '-c', 'curl -sL https://yihui.org/tinytex/install-unx.sh | sh'],
                env=env, capture_output=True, timeout=300
            )
            if result.returncode != 0:
                stderr = result.stderr.decode('utf-8', errors='replace')
                print(f"TinyTeX installation failed:\n{stderr}", file=sys.stderr)
                return None
        else:
            print("Automatic LaTeX installation is not supported on this platform.",
                  file=sys.stderr)
            print("Please install a LaTeX distribution (e.g., MiKTeX) manually.",
                  file=sys.stderr)
            return None

        # Find the installed pdflatex
        pdflatex = _local_pdflatex(working_dir)
        if not pdflatex:
            print("TinyTeX installed but pdflatex binary not found.", file=sys.stderr)
            return None

        # Install required packages
        tlmgr = os.path.join(os.path.dirname(pdflatex), 'tlmgr')
        if os.path.isfile(tlmgr):
            print("Installing required LaTeX packages...")
            subprocess.run(
                [tlmgr, 'install'] + TINYTEX_PACKAGES,
                capture_output=True, timeout=120
            )

        print("LaTeX installation complete.")
        return pdflatex

    except subprocess.TimeoutExpired:
        print("LaTeX installation timed out. Please try again.", file=sys.stderr)
        return None
    except Exception as e:
        print(f"LaTeX installation failed: {e}", file=sys.stderr)
        return None


def ensure_pdflatex(output_path):
    """Return a path to pdflatex, installing TinyTeX if necessary."""
    # 1. Check system PATH
    system_pdflatex = shutil.which('pdflatex')
    if system_pdflatex:
        return system_pdflatex

    # 2. Check local install
    working_dir = _find_working_dir(output_path)
    local = _local_pdflatex(working_dir)
    if local:
        return local

    # 3. Install TinyTeX
    installed = _install_tinytex(working_dir)
    if installed:
        return installed

    print("Could not find or install pdflatex.", file=sys.stderr)
    print("To install manually:", file=sys.stderr)
    print("  macOS:   brew install --cask basictex", file=sys.stderr)
    print("  Ubuntu:  sudo apt-get install texlive-latex-base", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# PDF compilation
# ---------------------------------------------------------------------------

def _find_build_dir(output_path):
    """Find or create a shared LaTeX build directory in .records/.latex-build/.

    Walks up from the output path to find the working directory (contains
    .supernomial/), then uses .records/.latex-build/ under the group folder.
    Falls back to a .latex-build/ dir next to the output.
    """
    d = os.path.dirname(os.path.abspath(output_path))
    # Walk up to find the working dir root (has .supernomial/)
    working_dir = None
    check = d
    while check != os.path.dirname(check):
        if os.path.isdir(os.path.join(check, '.supernomial')):
            working_dir = check
            break
        check = os.path.dirname(check)

    if working_dir:
        # The group folder is the first directory under working_dir in the output path
        rel = os.path.relpath(d, working_dir)
        group = rel.split(os.sep)[0]
        build_dir = os.path.join(working_dir, group, '.records', '.latex-build')
    else:
        build_dir = os.path.join(d, '.latex-build')

    os.makedirs(build_dir, exist_ok=True)
    return build_dir


def compile_pdf(pdflatex_path, tex_path, build_dir):
    """Compile a .tex file to PDF using pdflatex (two passes for TOC)."""
    for pass_num in range(1, 3):
        print(f"  pdflatex pass {pass_num}/2...")
        result = subprocess.run(
            [pdflatex_path, '-interaction=nonstopmode',
             '-output-directory', build_dir, tex_path],
            capture_output=True
        )
        if result.returncode != 0:
            log_text = result.stdout.decode('utf-8', errors='replace')
            # Extract the most useful error lines
            error_lines = [l for l in log_text.split('\n') if l.startswith('!')]
            if error_lines:
                print("PDF compilation failed:", file=sys.stderr)
                for line in error_lines[:5]:
                    print(f"  {line}", file=sys.stderr)
            else:
                print(f"PDF compilation failed. See .log file for details.", file=sys.stderr)
            sys.exit(1)
    print("PDF compiled successfully")


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
    latex = latex.replace('<<FISCAL_YEAR>>', escape_latex(str(fiscal_year)))
    latex = latex.replace('<<REPORT_BODY>>', build_report_body(view_json))

    # Build in a shared temp directory, copy only PDF to deliverables
    build_dir = _find_build_dir(args.output)
    tex_path = os.path.join(build_dir, 'build.tex')

    with open(tex_path, 'w') as f:
        f.write(latex)
    print(f"LaTeX written to {tex_path}")

    # Find or install pdflatex
    pdflatex_path = ensure_pdflatex(args.output)

    # Compile to PDF in build directory
    compile_pdf(pdflatex_path, tex_path, build_dir)

    # Copy PDF to final output location
    output_dir = os.path.dirname(args.output) or '.'
    os.makedirs(output_dir, exist_ok=True)
    built_pdf = os.path.join(build_dir, 'build.pdf')
    shutil.copy2(built_pdf, args.output)

    print(f"PDF written to {args.output}")


if __name__ == '__main__':
    main()
