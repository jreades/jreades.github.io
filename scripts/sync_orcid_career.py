"""Mirror ORCID affiliations (employment, education, service, ...) into data/orcid-career.json.

The file is a straight copy of what ORCID holds, in a stable order, so a git diff shows only
what changed on ORCID. scripts/build_career.py merges it with data/career.yml at render time.
"""
import json
import os
import sys

from sync_orcid import ROOT, get

OUT = os.path.join(ROOT, 'data', 'orcid-career.json')

# ORCID endpoint -> kind recorded on each item
ENDPOINTS = {
    'employments': 'employment',
    'invited-positions': 'invited-position',
    'educations': 'education',
    'qualifications': 'qualification',
    'services': 'service',
    'memberships': 'membership',
    'distinctions': 'distinction',
}


def year(date):
    y = ((date or {}).get('year') or {}).get('value')
    return int(y) if y else None


def items(endpoint, kind):
    for group in get('/' + endpoint).get('affiliation-group') or []:
        for summary in group['summaries']:
            for key, s in summary.items():
                if key.endswith('-summary'):
                    yield {
                        'kind': kind,
                        'put_code': s['put-code'],
                        'role': (s.get('role-title') or '').strip(),
                        'org': ((s.get('organization') or {}).get('name') or '').strip(),
                        'dept': (s.get('department-name') or '').strip(),
                        'start': year(s.get('start-date')),
                        'end': year(s.get('end-date')),
                    }


def main():
    out = [i for endpoint, kind in ENDPOINTS.items() for i in items(endpoint, kind)]
    out.sort(key=lambda i: (i['kind'], i['put_code']))
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write('\n')
    print(f'sync_orcid_career: {len(out)} affiliations -> data/orcid-career.json')


if __name__ == '__main__':
    sys.exit(main())
