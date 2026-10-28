"""Build the roles, education and service sections of the CV page.

Merges data/career.yml (hand-maintained, wins) with data/orcid-career.json (mirror of
ORCID). An ORCID item that matches a manual one (same organisation, and same role or same
start year) is dropped; complete items with no match are added. Runs as a Quarto pre-render
step and writes _generated/career.html, which publications.qmd includes.

`--report` prints, as Markdown, where ORCID and career.yml disagree or ORCID is incomplete,
so the ORCID record can be fixed; it writes no HTML.
"""
import difflib
import html
import json
import os
import re
import sys

import yaml

from sync_orcid import ROOT, ignored, norm

MANUAL = os.path.join(ROOT, 'data', 'career.yml')
MIRROR = os.path.join(ROOT, 'data', 'orcid-career.json')
OUT = os.path.join(ROOT, '_generated', 'career.html')

SECTION_OF_KIND = {
    'employment': 'employment', 'invited-position': 'employment',
    'education': 'education', 'qualification': 'education',
    'service': 'service', 'membership': 'service', 'distinction': 'service',
    'funding': 'funding',
}
# (key, heading) in display order
SECTIONS = [
    ('academic', 'Academic roles'),
    ('industry', 'Industry experience'),
    ('education', 'Education'),
    ('funding', 'Grants'),
    ('teaching', 'Teaching'),
    ('supervised', 'PhDs supervised'),
    ('examined', 'PhDs examined'),
    ('service', 'Service and memberships'),
]


def load_manual():
    with open(MANUAL, encoding='utf-8') as f:
        data = yaml.safe_load(f)
    items = []
    for section in ('employment', 'education', 'funding', 'teaching', 'supervised', 'examined', 'service'):
        for i in data.get(section, []):
            items.append({**i, 'section': section, 'source': 'manual'})
    return items, data.get('peer_review', [])


def load_orcid():
    if not os.path.exists(MIRROR):
        return []
    with open(MIRROR, encoding='utf-8') as f:
        raw = json.load(f)
    skip = ignored()
    return [{**i, 'section': SECTION_OF_KIND[i['kind']], 'source': 'orcid'}
            for i in raw if str(i['put_code']) not in skip]


def same_org(a, b):
    a, b = norm(a), norm(b)
    return bool(a) and bool(b) and (a in b or b in a)


STOP = {'in', 'of', 'the', 'and'}


def words(s):
    return [w for w in norm(s).split() if w not in STOP]


def same_role(a, b):
    """Same words, or one is a leading part of the other ('PhD' / 'PhD in Town Planning')."""
    a, b = words(a), words(b)
    short, long_ = sorted((a, b), key=len)
    return bool(short) and long_[:len(short)] == short


def matches(manual, o):
    if manual['section'] != o['section'] or not same_org(manual.get('org', ''), o['org']):
        return False
    if same_role(manual['role'], o['role']):
        return True
    gap = None if o['start'] is None else abs(o['start'] - manual.get('start', 0))
    return gap == 0 or (gap == 1 and not o['role'])


def span(i):
    s, e = i.get('start'), i.get('end')
    if s is None and e is None:
        return ''
    if s == e:
        return str(s)
    return f'{s or ""}–{e or ""}'


def label(i):
    return ', '.join(x for x in (i['role'], i.get('org')) if x)


def merge():
    manual, peer_review = load_manual()
    orcid = load_orcid()
    merged, report = list(manual), []
    for o in orcid:
        m = next((m for m in manual if matches(m, o)), None)
        if m is None:
            if not o['role'] or o['start'] is None:
                what = 'role' if not o['role'] else 'start year'
                report.append(f'- ORCID {o["kind"]} at {o["org"]} (put-code {o["put_code"]}) has no {what}; not shown.')
            else:
                merged.append(o)
                report.append(f'- Added from ORCID: {label(o)} ({span(o)}). Move it into career.yml to edit it.')
            continue
        for field in ('role', 'start', 'end'):
            theirs, ours = o[field], m.get(field)
            if theirs is None and field != 'end' or theirs == '':
                continue
            differs = not same_role(theirs, ours) if field == 'role' else theirs != ours
            if differs:
                report.append(f'- {label(m)}: career.yml has {field} {ours or "(current)"}, ORCID has {theirs or "(current)"}.')
    return merged, peer_review, report


def sort_key(i):
    if i.get('start') is None and i.get('end') is None:
        return (False, 0, 0)  # undated (supervision lists) keep their order, after dated items
    return (i.get('end') is None, i.get('end') or 0, i.get('start') or 0)


def item_html(i):
    parts = [f'<strong>{html.escape(i["role"])}</strong>']
    parts += [html.escape(x) for x in (i.get('dept'), i.get('org')) if x]
    note = f'<span class="note">{html.escape(i["note"])}</span>' if i.get('note') else ''
    return (f'<li><span class="what">{", ".join(parts)}{note}</span>'
            f'<span class="when">{span(i)}</span></li>')


def section_html(key, heading, body):
    return (f'<section class="pubgroup" id="{key}">\n<h2 class="lab">{heading}<a class="to-top title-link" href="#">Top ↑</a></h2>\n'
            f'<ul class="publist career">\n{body}\n</ul>\n</section>')


def main():
    merged, peer_review, report = merge()
    if '--report' in sys.argv:
        print('\n'.join(report) if report else 'No differences between career.yml and ORCID.')
        return
    groups = {
        'academic': [i for i in merged if i['section'] == 'employment' and i.get('sector') != 'industry'],
        'industry': [i for i in merged if i.get('sector') == 'industry'],
        'education': [i for i in merged if i['section'] == 'education'],
        'funding': [i for i in merged if i['section'] == 'funding'],
        'teaching': [i for i in merged if i['section'] == 'teaching'],
        'supervised': [i for i in merged if i['section'] == 'supervised'],
        'examined': [i for i in merged if i['section'] == 'examined'],
        'service': [i for i in merged if i['section'] == 'service'],
    }
    sections = []
    for key, heading in SECTIONS:
        items = sorted(groups[key], key=sort_key, reverse=True)
        if items:
            sections.append(section_html(key, heading, '\n'.join(item_html(i) for i in items)))
    if peer_review:
        names = ', '.join(f'<em>{html.escape(n)}</em>' for n in peer_review)
        sections.append(section_html('peer-review', 'Peer review', f'<li><span class="what">{names}</span></li>'))
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write('\n'.join(sections) + '\n')
    print(f'build_career: {len(merged)} items, {len(report)} ORCID notes -> {os.path.relpath(OUT, ROOT)}')
    for line in report:
        print(' ', line)


if __name__ == '__main__':
    main()
