---
# Settings for scripts/duotone.py. Edit, then run:  python scripts/duotone.py
# Only images whose settings (or source file) changed are re-done; add --force to redo all.
#
# Per-image overrides go under `images:` using the file name as the key.

palette:            # names usable for shadow / mid / highlight; or give any "#rrggbb"
  deep:  "#1F3540"
  slate: "#35505A"
  teal:  "#587077"
  mist:  "#9FB0B3"
  sky:   "#C9D1CF"
  paper: "#E4E4DD"
  rust:  "#B3402A"

defaults:
  shadow: deep      # colour that black maps to
  highlight: paper  # colour that white maps to
  mid: null         # optional third colour for a tritone, e.g. teal
  blackpoint: 15    # 0-255: greys at or below this become pure shadow colour. Raise to darken.
  whitepoint: 240   # 0-255: greys at or above this become pure highlight colour. Lower to lighten.
  midpoint: 127     # where `mid` sits between the two (only if mid is set)
  gamma: 1.0        # >1 darkens midtones, <1 lightens them (applied before colouring)
  cutoff: 1         # % of darkest/lightest pixels clipped by auto-contrast; 0 turns it off
  strength: 0.85    # 1 = pure duotone; lower lets the original colour show through
  saturation: 0.5   # saturation of the original colour layer under the duotone (0 = grey)
  width: 2400       # output width in px (never enlarges)
  aspect: null      # optional crop, e.g. "21:9" or "4:5"
  focus: [0.5, 0.5] # crop centre as fractions of width, height
  quality: 85       # JPEG quality

images:
  IMG_3203.jpg:
    strength: 0.7
    saturation: 0.7
#  IMG_3250.jpg:
#    blackpoint: 40
---

Notes: keep scene photos in this folder; duotones are written to `img/duotone/`.
Originals are never modified.
