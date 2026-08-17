# adobe-export-presets

**Which Adobe export presets can be authored as files, which cannot, and the exact formats — for people automating photo export pipelines.**

Adobe's export/batch settings live in at least four different mechanisms with four different levels of authorability. Some are plain text with a documented-by-inspection schema. Some are undocumented binary that must be recorded by hand. Adobe documents none of this. This repo is an attempt to write it down.

Everything here was verified on **2026-08-17** against Adobe's shipped scripts and current published documentation. Where something is unverified it says so.

---

## The short version

| Mechanism | Format | Author as a file? | Notes |
|---|---|---|---|
| **Photoshop ExtendScript** | `.jsx`, plain text | ✅ **Yes** | Full control. The reliable answer for almost every pipeline. |
| **Photoshop Image Processor settings** | `.xml`, plain text | ✅ **Yes** | Real, verified schema. Brittle parser — see below. |
| **Bridge Output module presets** | `.xml`, plain text | ✅ Yes | Contact Sheet / PDF only. Different feature from the Export panel. |
| **Bridge Export panel presets** | `.xml`, plain text | ✅ **Yes** | 49-key flat schema, documented in [`docs/bridge-export-presets.md`](docs/bridge-export-presets.md). Import via Export panel → preset menu. |
| **Photoshop Actions** | `.atn`, binary | ❌ No | Undocumented binary. Must be recorded in the Actions panel. |
| **Droplets** | `.exe` (Windows) | ❌ No | Compiled wrapper around an Action. |

## The one thing most people get wrong

**Bridge's Export panel cannot set a colour space on JPEG.** Its JPEG options are quality and nothing else — Color Space appears only under PNG and TIFF ([Adobe: Supported export file formats](https://helpx.adobe.com/bridge/desktop/share-and-export/supported-export-file-formats.html)). There has been [an open feature request](https://adobebridge.uservoice.com/forums/905323-feature-request/suggestions/41739760-convert-profile-to-srgb-in-export-tab) since October 2020 to add it, still unimplemented.

If your output goes to a print lab, this matters. WHCC, for example, [requires an embedded RGB profile](https://www.whcc.com/help/color-management/icc-profiles/) and states that without one "you will have unpredictable color in your prints."

So: Bridge Export is fine for web previews when your sources are already sRGB. It is not a print path. Use a `.jsx` for anything colour-critical.

---

## What's in here

### `tools/print-export.jsx`
A Photoshop batch export script. Point it at a folder and it emits, into `_export/`:

- **print masters** — full resolution, no resampling, converted to sRGB with the profile embedded, quality 12, tagged 300 PPI
- **web previews** — long edge 2048, sRGB, quality 9, output-sharpened
- **`manifest.csv`** — per image: pixel dimensions, megapixels, native aspect ratio, and a PASS/OK/FAIL verdict against every print size you sell

The manifest is the interesting part. It answers "which sizes can this file honestly be sold at" with arithmetic rather than optimism.

Run it with **File → Scripts → Browse…** — no admin rights, no restart. To get it in the menu permanently, drop it in Photoshop's `Presets/Scripts/` folder and restart.

It never crops, never upscales, and never writes to your originals.

### `tools/make-image-processor-xml.py`
Generates a `Image Processor.xml` settings file for Photoshop's built-in Image Processor, so you can produce batch settings without clicking through the dialog. Schema documented in [`docs/image-processor-xml.md`](docs/image-processor-xml.md).

### `tools/make-bridge-preset.py`
Generates an Adobe Bridge export preset. Verified against real Bridge-authored presets: the generated file matches them key-for-key, in order, with the same byte conventions (no BOM, LF, 8-space indent).

```bash
python3 make-bridge-preset.py --name "IG 4x5" --size 1080 1350 --fill \
    --subfolder IG_1080x1350 --dest ~/Downloads
```

Import via **Export panel → preset menu → Import Preset**.

### `docs/`
- [`bridge-export-presets.md`](docs/bridge-export-presets.md) — the Export panel preset schema, all 49 keys, and a worked failure analysis
- [`image-processor-xml.md`](docs/image-processor-xml.md) — the verified Image Processor schema
- [`print-resolution.md`](docs/print-resolution.md) — the DPI arithmetic, and why it usually says no

### `examples/`
Ready-to-import presets: Instagram 4:5, 3:4 and landscape, plus a 2048px web preview, and a sample Image Processor settings file.

---

## Help wanted

The schema is mapped but not complete. About a dozen keys never varied across the available samples, so their enums are unknown — `resizeOptionType`, `scalingAlgorithm`, `conflictSavingOptions`, the `png*`/`tiff*`/`dng*` blocks, and the Content Credentials group.

[`docs/bridge-export-presets.md`](docs/bridge-export-presets.md) has a one-field-at-a-time diff method for mapping them. Each mapped enum is a small, easily-reviewed PR. Presets from other Bridge versions are also useful — everything here is from 16.0.

---

## Licence

MIT. See [LICENSE](LICENSE).

Not affiliated with or endorsed by Adobe. "Adobe", "Photoshop" and "Bridge" are trademarks of Adobe Inc.
