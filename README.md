# jreades.github.io

Portfolio site built with [Quarto](https://quarto.org) and published to GitHub Pages by `.github/workflows/publish.yml`.

## Build locally

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
quarto preview
```

| What | Where |
| --- | --- |
| Look and feel (colours, fonts, grid, hero bleed) | `styles/theme.scss`, tokens at the top |
| Publications and talks | `data/pubs.bib`, `data/talks.bib`, grouped by each entry's `output` field by `scripts/build_pubs.py` |
| ORCID publications | `data/orcid.bib`, regenerated weekly from [ORCID](https://orcid.org/0000-0002-1443-9263) by `scripts/sync_orcid.py` via `.github/workflows/sync-orcid.yml`, which opens a PR. Never edit it by hand: move an entry into `pubs.bib`/`talks.bib` to correct it (it is then skipped), or list its put-code or DOI in `data/orcid-ignore.txt` to hide it. Needs Settings > Actions > General > "Allow GitHub Actions to create and approve pull requests" |
| Essays | `posts/*.qmd` (imported once from reades.com; now edited by hand) |
| Photos | originals in `img/scenes/` (local only); `python scripts/duotone.py` reads `img/duotone/duotone.md` and writes the cropped duotones beside it |
| Open data tasks | `data/TODO-data.md`, `posts/MISSING-IMAGES.md` |

`output` values: `journal-article`, `book`, `chapter`, `report-chapter`, `report`, `white-paper`, `thesis`, `talk`. Entries without one fall back to a group based on the BibTeX entry type.
