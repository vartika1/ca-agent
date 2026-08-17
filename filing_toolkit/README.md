# filing_toolkit — driving the offline utility & the browser

Two small drivers used during the assisted-filing sitting (macOS).

```bash
python3 -m venv /tmp/itdvenv && /tmp/itdvenv/bin/pip install pyobjc-framework-Quartz
```

- **`drive.py`** — drives `/Applications/ITDe-Filing-2026.app` (Wails/WKWebView)
  with synthetic Quartz events. The utility exposes no DOM, so screenshots are
  the only feedback channel.
- **`chrome_drive.py`** — drives Chrome using window-fraction coords (retina-safe).

## Token discipline — read this before driving anything

Screenshots are the biggest token cost in a filing. Rough cost of one image
(≈ width × height ⁄ 750 tokens):

| capture | size | ≈ tokens |
|---|---|---|
| full window PNG | 1280×748 | ~1,280 |
| **default (50% JPEG)** | 640×374 | **~320** |
| **cropped panel** | 400×200 | **~110** |

So the rules:

1. **Never screenshot after every click.** Use `batch` to run a whole sequence
   in one call, then take ONE verification shot:
   ```bash
   drive.py batch 'click 640 300; paste 700 350 "125000"; key return; sleep 0.5'
   drive.py shot                      # one check, not four
   ```
2. **Crop to what you need.** Verifying a single figure or an error banner?
   `drive.py shot --crop 300,120,600,200` costs ~10% of a full window.
3. **Default scale is already 0.5 JPEG** — only pass `--full` when reading
   genuinely fine detail (rare).
4. **Prefer text over pixels.** For the *browser*, don't screenshot at all —
   read the DOM as text (see `SKILL.md` §A). Screenshots are for the utility,
   which has no other channel.
5. **Let the utility do the checking.** Its Internal Validation lists every
   error as text — run it and read the list, instead of eyeballing 24 schedules
   one screenshot at a time. Then run `scripts/preflight_itr_check.py` for the
   portal-side defects it misses.

## Note on the JSON

Build the return JSON and **import** it into the utility — do not fill screens
field-by-field. Importing is both far cheaper in tokens and the route that
produces a correctly *signed* upload file.
