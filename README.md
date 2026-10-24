# jreades.github.io

Portfolio site built with [Quarto](https://quarto.org) and published to GitHub Pages by `.github/workflows/publish.yml`.

## Build locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
quarto preview
```

## Where things live

| What | Where |
| --- | --- |
| Look and feel (colours, fonts, grid, hero bleed) | `styles/theme.scss`, tokens at the top |
| Publications and talks | `data/pubs.bib`, `data/talks.bib`, grouped by each entry's `output` field by `scripts/build_pubs.py` |
| Essays | `posts/*.qmd` (imported once from reades.com; now edited by hand) |
| Photos | originals in `img/scenes/` (local only); `python scripts/duotone.py` reads `img/duotone/duotone.md` and writes the cropped duotones beside it |
| Open data tasks | `data/TODO-data.md`, `posts/MISSING-IMAGES.md` |

`output` values: `journal-article`, `book`, `chapter`, `report-chapter`, `report`, `white-paper`, `thesis`, `talk`. Entries without one fall back to a group based on the BibTeX entry type.
