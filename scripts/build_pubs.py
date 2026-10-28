"""Build the web publications list from data/*.bib, grouped by the `output` field.

Runs as a Quarto pre-render step and writes _generated/publications.html, which
publications.qmd includes. Entries without an `output` field fall back to a group
derived from the BibTeX entry type. Fields starting with TODO are never rendered.
"""
import glob
import html
import os
import re

import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BIB_GLOB = os.path.join(ROOT, 'data', '*.bib')
OUT = os.path.join(ROOT, '_generated', 'publications.html')
ME = 'reades'

# Display order and heading for each `output` value.
GROUPS = [
    ('journal-article', 'Journal articles'),
    ('book', 'Books'),
    ('chapter', 'Book chapters'),
    ('report-chapter', 'Report chapters'),
    ('report', 'Reports'),
    ('white-paper', 'White papers'),
    ('thesis', 'Theses'),
    ('conference-paper', 'Conference papers'),
    ('software', 'Software'),
    ('book-review', 'Book reviews'),
    ('other', 'Other outputs'),
    ('talk', 'Talks'),
]
FALLBACK = {
    'article': 'journal-article', 'book': 'book', 'incollection': 'chapter',
    'inbook': 'chapter', 'techreport': 'report', 'phdthesis': 'thesis',
    'mastersthesis': 'thesis',
}


def load(path):
    parser = BibTexParser(common_strings=True, customization=convert_to_unicode)
    parser.ignore_nonstandard_types = False
    parser.homogenise_fields = False
    with open(path, encoding='utf-8') as f:
        return bibtexparser.load(f, parser).entries


def clean(s):
    s = re.sub(r'[{}]', '', s or '')
    s = s.replace('\\&', '&').replace('--', '–')
    s = s.replace('``', '“').replace("''", '”').replace('`', '‘').replace("'", '’')
    return re.sub(r'\s+', ' ', s).strip()


def initials(given):
    parts = re.split(r'[\s.]+', given.strip())
    return ' '.join(p[0] + '.' for p in
                    (q for part in parts for q in part.split('-')) if p)


def author_html(name):
    name = clean(name)
    if ',' in name:
        last, given = [x.strip() for x in name.split(',', 1)]
    else:
        bits = name.split()
        last, given = bits[-1], ' '.join(bits[:-1])
    out = html.escape(f'{last}, {initials(given)}'.strip(', '))
    return f'<strong>{out}</strong>' if ME in last.lower() else out


def authors_html(e):
    names = [a for a in re.split(r'\s+and\s+', e.get('author', '')) if a.strip() and a != 'others']
    parts = [author_html(n) for n in names]
    if len(parts) > 1:
        return ', '.join(parts[:-1]) + ' and ' + parts[-1]
    return parts[0] if parts else ''


def visible(e, key):
    v = clean(e.get(key, ''))
    return '' if not v or v == '0' or 'TODO' in v else v


def link(e):
    if visible(e, 'doi'):
        d = visible(e, 'doi')
        return f'<a class="pub-link" href="https://doi.org/{html.escape(d)}">DOI</a>'
    if visible(e, 'url'):
        return f'<a class="pub-link" href="{html.escape(visible(e, "url"))}">{"Slides" if e["output"] == "talk" else "Link"}</a>'
    return ''


def item_html(e):
    out = e['output']
    title = html.escape(visible(e, 'title'))
    year = html.escape(visible(e, 'year'))
    bits = [f'{authors_html(e)} ({year})', f'<span class="pub-title">{title}</span>']
    if out == 'talk':
        venue = visible(e, 'howpublished')
        if venue:
            bits.append(html.escape(venue))
    else:
        venue = visible(e, 'journal') or visible(e, 'booktitle')
        pubr = visible(e, 'publisher') or visible(e, 'institution') or visible(e, 'school')
        if venue:
            vol = visible(e, 'volume')
            num = visible(e, 'number')
            v = f'<em>{html.escape(venue)}</em>'
            if vol:
                v += f', {html.escape(vol)}' + (f'({html.escape(num)})' if num else '')
            if visible(e, 'pages'):
                v += f', pp. {html.escape(visible(e, "pages"))}'
            bits.append(v)
        elif pubr:
            bits.append(html.escape(pubr))
    text = '. '.join(bits) + '.'
    ln = link(e)
    return f'<li>{text} {ln}</li>'


def main():
    entries = []
    for path in sorted(glob.glob(BIB_GLOB)):
        entries += load(path)
    known = {g for g, _ in GROUPS}
    by_group = {}
    for e in entries:
        e['output'] = clean(e.get('output')) or FALLBACK.get(e['ENTRYTYPE'].lower(), 'other')
        by_group.setdefault(e['output'], []).append(e)

    order = GROUPS + [(g, g.replace('-', ' ').capitalize()) for g in by_group if g not in known]
    sections = []
    for key, heading in order:
        items = sorted(by_group.get(key, []), key=lambda e: (clean(e.get('year', '0')), clean(e.get('month', ''))), reverse=True)
        if not items:
            continue
        lis = '\n'.join(item_html(e) for e in items)
        sections.append(
            f'<section class="pubgroup" id="{key}">\n'
            f'<h2 class="lab">{heading}<span class="count">{len(items)}</span><a class="to-top title-link" href="#">Top ↑</a></h2>\n'
            f'<ol class="publist">\n{lis}\n</ol>\n</section>'
        )
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(sections) + '\n')
    print(f'build_pubs: {len(entries)} entries, {len(sections)} groups -> {os.path.relpath(OUT, ROOT)}')


if __name__ == '__main__':
    main()
