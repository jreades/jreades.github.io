"""Build the section index at the top of the CV page from the generated sections.

Runs as a Quarto pre-render step after build_pubs.py and build_career.py, and reads their
output so the list of links can never drift from the sections actually on the page.
"""
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GEN = os.path.join(ROOT, '_generated')
SECTION = re.compile(r'<section class="pubgroup" id="([^"]+)">\s*<h2 class="lab">([^<]+)')
LINES = [('Career', 'career.html'), ('Publications', 'publications.html')]


def line(label, name):
    with open(os.path.join(GEN, name), encoding='utf-8') as f:
        links = ''.join(f'<a class="title-link" href="#{i}">{h}</a>' for i, h in SECTION.findall(f.read()))
    return f'<p><span class="lab">{label}</span><span class="links">{links}</span></p>' if links else ''


def main():
    body = '\n'.join(filter(None, (line(label, name) for label, name in LINES)))
    with open(os.path.join(GEN, 'cv-index.html'), 'w', encoding='utf-8') as f:
        f.write(f'<nav class="cv-index" aria-label="Sections on this page">\n{body}\n</nav>\n')
    print(f'build_cv_index: {body.count("<a ")} links -> _generated/cv-index.html')


if __name__ == '__main__':
    main()
