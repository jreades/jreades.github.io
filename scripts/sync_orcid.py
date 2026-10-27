"""Write data/orcid.bib from the public ORCID record.

Runs in .github/workflows/sync-orcid.yml (and by hand). The file is regenerated in
full on every run, in a stable order, so a git diff shows only what changed on ORCID.

Anything already in another data/*.bib (matched by DOI or near-identical title) is
skipped, so curating an entry means copying it into pubs.bib or talks.bib. Works listed
in data/orcid-ignore.txt (put-codes or DOIs, one per line, '#' for comments) are skipped.
"""
import difflib
import glob
import html
import json
import os
import re
import sys
import urllib.request

import bibtexparser
from bibtexparser.bparser import BibTexParser

ORCID_ID = '0000-0002-1443-9263'
API = f'https://pub.orcid.org/v3.0/{ORCID_ID}'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'data')
OUT = os.path.join(DATA, 'orcid.bib')
IGNORE = os.path.join(DATA, 'orcid-ignore.txt')
SIMILAR = 0.9  # title similarity above which two entries are the same work

# ORCID work type -> (BibTeX entry type, `output` group used by build_pubs.py)
TYPES = {
    'journal-article': ('article', 'journal-article'),
    'book': ('book', 'book'),
    'book-chapter': ('incollection', 'chapter'),
    'report': ('techreport', 'report'),
    'working-paper': ('techreport', 'report'),
    'dissertation-thesis': ('phdthesis', 'thesis'),
    'conference-abstract': ('misc', 'talk'),
    'conference-paper': ('inproceedings', 'conference-paper'),
    'software': ('misc', 'software'),
    'book-review': ('misc', 'book-review'),
    'other': ('misc', 'other'),
}


def get(path):
    req = urllib.request.Request(API + path, headers={'Accept': 'application/json'})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)


def norm(s):
    return re.sub(r'[^a-z0-9]+', ' ', (s or '').lower()).strip()


def bib_text(s):
    s = html.unescape(s or '')
    s = re.sub(r'[{}\\]', '', s).replace('&', r'\&')
    return re.sub(r'\s+', ' ', s).strip()


def doi_of(work):
    for i in (work.get('external-ids') or {}).get('external-id') or []:
        if i['external-id-type'] == 'doi':
            d = i['external-id-value'].strip().lower()
            return re.sub(r'^https?://(dx\.)?doi\.org/', '', d)
    return ''


def value(node):
    return ((node or {}).get('value') or '').strip()


def parse_citation(work):
    """Extra fields (volume, pages, ...) from the BibTeX ORCID stores, if any."""
    cite = (work.get('citation') or {})
    if cite.get('citation-type') != 'bibtex' or not cite.get('citation-value'):
        return {}
    try:
        parser = BibTexParser(common_strings=True)
        parser.ignore_nonstandard_types = False
        entries = bibtexparser.loads(cite['citation-value'], parser).entries
    except Exception:
        return {}
    return entries[0] if entries else {}


def name_to_bib(name):
    name = bib_text(name)
    if ',' in name or ' ' not in name:
        return name
    first, last = name.rsplit(' ', 1)
    return f'{last}, {first}'


def authors_of(work, cite, is_talk):
    names = [value(c.get('credit-name')) for c in
             (work.get('contributors') or {}).get('contributor') or []]
    names = [n for n in names if n]
    if names:
        return ' and '.join(name_to_bib(n) for n in names)
    return bib_text(cite.get('author', '')) or ('Reades, Jonathan' if is_talk else '')


def to_entry(work):
    kind = work.get('type')
    if kind not in TYPES:
        return None
    entry_type, output = TYPES[kind]
    cite = parse_citation(work)
    pub = work.get('publication-date') or {}
    fields = {
        'author': authors_of(work, cite, output == 'talk'),
        'title': bib_text(value((work.get('title') or {}).get('title'))),
        'year': value(pub.get('year')) or bib_text(cite.get('year', '')),
        'output': output,
        'orcid-put-code': str(work['put-code']),
    }
    month = value(pub.get('month'))
    if month:
        fields['month'] = month
    doi = doi_of(work)
    if doi:
        fields['doi'] = doi
    elif output != 'talk' and value(work.get('url')):
        fields['url'] = value(work['url'])
    venue = bib_text(value(work.get('journal-title')))
    if entry_type == 'article':
        fields['journal'] = venue or bib_text(cite.get('journal', ''))
    elif entry_type in ('incollection', 'inproceedings'):
        fields['booktitle'] = venue or bib_text(cite.get('booktitle', ''))
    elif venue:
        fields['howpublished'] = venue
    for f in ('volume', 'number', 'pages', 'publisher', 'institution', 'school'):
        if cite.get(f):
            fields[f] = bib_text(cite[f])
    if 'pages' in fields:
        fields['pages'] = re.sub(r'\s*[-–—]+\s*', '--', fields['pages'])
    fields = {k: v for k, v in fields.items() if v}
    if not fields.get('title') or not fields.get('author'):
        return None
    return entry_type, f"orcid{work['put-code']}", fields


def known_works():
    """DOIs and (title, is_talk) pairs already present in hand-maintained bib files."""
    dois, titles = set(), []
    for path in glob.glob(os.path.join(DATA, '*.bib')):
        if os.path.abspath(path) == OUT:
            continue
        with open(path, encoding='utf-8') as f:
            parser = BibTexParser(common_strings=True)
            parser.ignore_nonstandard_types = False
            for e in bibtexparser.load(f, parser).entries:
                if e.get('doi'):
                    dois.add(e['doi'].strip().lower())
                titles.append((norm(e.get('title')), e.get('output') == 'talk'))
    return dois, titles


def ignored():
    if not os.path.exists(IGNORE):
        return set()
    with open(IGNORE, encoding='utf-8') as f:
        lines = (line.split('#')[0].strip().lower() for line in f)
        return {line for line in lines if line}


def same_title(a, b):
    """Near-identical, or one is a 3+ word prefix of the other (ORCID often drops subtitles)."""
    short, long_ = sorted((a, b), key=len)
    if len(short.split()) >= 3 and long_.startswith(short):
        return True
    return difflib.SequenceMatcher(None, a, b).ratio() >= SIMILAR


def duplicate(fields, dois, titles):
    if fields.get('doi', '').lower() in dois:
        return True
    t, talk = norm(fields['title']), fields['output'] == 'talk'
    return any(talk == other_talk and same_title(t, other) for other, other_talk in titles)


def part_of_known(fields, titles):
    """A chapter of a book that is already listed (e.g. your own monograph)."""
    book = norm(fields.get('booktitle'))
    return bool(book) and any(not talk and same_title(book, other) for other, talk in titles)


def not_by_me(work):
    names = [value(c.get('credit-name')) for c in
             (work.get('contributors') or {}).get('contributor') or []]
    return bool(names) and not any('reades' in n.lower() for n in names)


def render(entry_type, key, fields):
    body = ',\n'.join(f'\t{k} = {{{v}}}' for k, v in sorted(fields.items()))
    return f'@{entry_type}{{{key},\n{body}}}\n'


def main():
    groups = get('/works')['group']
    codes = [g['work-summary'][0]['put-code'] for g in groups]
    works = []
    for i in range(0, len(codes), 100):  # the bulk endpoint takes at most 100
        batch = get('/works/' + ','.join(map(str, codes[i:i + 100])))['bulk']
        works += [b['work'] for b in batch if 'work' in b]

    skip = ignored()
    dois, titles = known_works()
    out, counts = [], {'duplicate': 0, 'ignored': 0, 'unsupported': 0, 'not by me': 0}
    for work in sorted(works, key=lambda w: w['put-code']):
        parsed = to_entry(work)
        if not parsed:
            counts['unsupported'] += 1
            print(f'  skipped (no authors or type): {value((work.get("title") or {}).get("title"))}')
            continue
        entry_type, key, fields = parsed
        if not_by_me(work):
            counts['not by me'] += 1
        elif fields.get('doi', '') in skip or fields['orcid-put-code'] in skip:
            counts['ignored'] += 1
        elif duplicate(fields, dois, titles) or part_of_known(fields, titles):
            counts['duplicate'] += 1
        else:
            out.append(render(entry_type, key, fields))
            # later ORCID works with this DOI/title are the same work
            if fields.get('doi'):
                dois.add(fields['doi'].lower())
            titles.append((norm(fields['title']), fields['output'] == 'talk'))

    header = (f'%% Generated by scripts/sync_orcid.py from https://orcid.org/{ORCID_ID}. Do not edit.\n'
              '%% To correct an entry, move it into pubs.bib or talks.bib; to hide one, list its\n'
              '%% orcid-put-code or DOI in orcid-ignore.txt.\n\n')
    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(header + '\n'.join(out))
    print(f'sync_orcid: {len(works)} works on ORCID, {len(out)} written to data/orcid.bib '
          f'({counts["duplicate"]} already in other bib files, {counts["ignored"]} ignored, '
          f'{counts["unsupported"]} unsupported, {counts["not by me"]} not by me)')


if __name__ == '__main__':
    sys.exit(main())
