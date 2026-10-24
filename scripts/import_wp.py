"""One-off import of posts from the WordPress REST API into posts/*.qmd.

Usage: python scripts/import_wp.py [base_url]
Downloads every post, converts the HTML to Markdown with Pandoc (bundled with
Quarto), copies referenced images into posts/img/ and writes Quarto front matter.
Re-running overwrites posts/*.qmd, so edit imported posts only after you are done.
"""
import html
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request

BASE = (sys.argv[1] if len(sys.argv) > 1 else 'http://www.reades.com/wp').rstrip('/')
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
POSTS = os.path.join(ROOT, 'posts')
IMG = os.path.join(POSTS, 'img')
API = f'{BASE}/?rest_route=/wp/v2'
MISSING = []


def get(url, binary=False):
    with urllib.request.urlopen(url, timeout=30) as r:
        data = r.read()
    return data if binary else json.loads(data)


def fetch_all(kind):
    out, page = [], 1
    while True:
        batch = get(f'{API}/{kind}&per_page=100&page={page}')
        out += batch
        if len(batch) < 100:
            return out
        page += 1


def pandoc(src):
    return subprocess.run(
        ['quarto', 'pandoc', '-f', 'html', '-t', 'markdown-smart-raw_html-native_divs-native_spans-fenced_divs-bracketed_spans',
         '--wrap=none'],
        input=src, capture_output=True, text=True, check=True).stdout


def localise_images(body, slug):
    """Download wp-content images referenced in the HTML and point at posts/img/."""
    def repl(m):
        url = html.unescape(m.group(2))
        if 'wp-content' not in url and not url.startswith(BASE):
            return m.group(0)
        name = os.path.basename(urllib.parse.urlparse(url).path)
        dest = os.path.join(IMG, name)
        if not os.path.exists(dest):
            try:
                data = get(urllib.parse.urljoin(BASE + '/', url), binary=True)
            except Exception as e:
                MISSING.append(f'{slug}: {url} ({e})')
                return f'{m.group(1)}img/{name}'
            with open(dest, 'wb') as f:
                f.write(data)
        return f'{m.group(1)}img/{name}'
    return re.sub(r'(<img[^>]*?\ssrc=["\'])([^"\']+)', repl, body)


def main():
    os.makedirs(IMG, exist_ok=True)
    cats = {c['id']: html.unescape(c['name']) for c in fetch_all('categories')}
    posts = fetch_all('posts')
    media = {m['id']: m['source_url'] for m in fetch_all('media')}
    for p in posts:
        slug = p['slug']
        title = html.unescape(p['title']['rendered']).replace('"', '\\"')
        names = [cats[i] for i in p['categories'] if cats.get(i) not in ('Uncategorized', 'Front Page', 'Place')]
        body = localise_images(p['content']['rendered'], slug)
        md = pandoc(body).strip()
        excerpt = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', '', html.unescape(p['excerpt']['rendered']))).strip()
        fm = ['---', f'title: "{title}"', f'date: {p["date"][:10]}']
        if names:
            fm.append('categories: [' + ', '.join(f'"{n}"' for n in names) + ']')
        if excerpt:
            fm.append('description: "' + excerpt.replace('"', '\\"')[:240] + '"')
        feat = media.get(p.get('featured_media'))
        if feat:
            name = os.path.basename(urllib.parse.urlparse(feat).path)
            if not os.path.exists(os.path.join(IMG, name)):
                with open(os.path.join(IMG, name), 'wb') as f:
                    f.write(get(feat, binary=True))
            fm.append(f'image: img/{name}')
        fm.append(f'wp-url: {p["link"]}')
        fm.append('---')
        with open(os.path.join(POSTS, f'{slug}.qmd'), 'w', encoding='utf-8') as f:
            f.write('\n'.join(fm) + '\n\n' + md + '\n')
    print(f'import_wp: {len(posts)} posts -> posts/')
    report = os.path.join(POSTS, 'MISSING-IMAGES.md')
    if MISSING:
        with open(report, 'w', encoding='utf-8') as f:
            f.write('# Images referenced by posts but not available on the old server\n\n' + '\n'.join(f'- {m}' for m in MISSING) + '\n')
        print(f'  {len(MISSING)} images missing, listed in posts/MISSING-IMAGES.md')


if __name__ == '__main__':
    main()
