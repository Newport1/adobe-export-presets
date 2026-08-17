# Adobe Bridge export presets — the file format

**Status: solved.** Bridge export presets are plain XML, they can be hand-authored, and Bridge imports them through the UI.

This page documents the format for **Bridge 16.0** (2026). Adobe documents none of it.

## Correcting the record

Earlier drafts of this repo claimed the format was undocumented-and-therefore-unauthorable, on the strength of one community report of a failed file transplant. **That was wrong on both counts.** There is a documented-by-inspection XML format, and Bridge has a first-class **Export panel → preset menu → Import Preset** command. The one thing that remains true is the JPEG colour-space gap — and the schema below now proves it, since there is a `pngColorSpace` and a `tiffColorSpace` key but no `jpegColorSpace`.

## The format

```xml
<?xml version="1.0" encoding="utf-8"?>
<preset>
        <data key="bridgeVersion" value="16.0"/>
        <data key="name" value="IG 4x5 FullRes 1080x1350 Fill"/>
        ...
</preset>
```

- Root element `<preset>`. No namespace, no attributes.
- Exactly one child type: `<data key="..." value="..."/>` — a flat, ordered list of **49 keys**. No nesting, no repeats.
- `<?xml version="1.0" encoding="utf-8"?>` declaration.
- **No BOM.** LF line endings. 8-space indent. Trailing newline.
- Every value is a string, including numbers and booleans. Dimensions carry two decimals (`1080.00`, not `1080`).

Note the contrast with [Image Processor XML](image-processor-xml.md), which *requires* a BOM and tabs. Two Adobe formats, opposite conventions. Don't cross-contaminate them.

## Where they live

**macOS**
```
~/Library/Application Support/Adobe/Bridge 2025/ExportPreset/
~/Library/Application Support/Adobe/Bridge 2026/ExportPreset/
```

**Windows**
```
%APPDATA%\Adobe\Bridge <version>\ExportPreset\
C:\Program Files\Adobe\Adobe Bridge <version>\ExportPreset\   (factory presets)
```

You can drop files in directly, or import through the Export panel's preset menu. Importing is the reliable route — a direct drop may need a Bridge restart to be picked up, which is the most likely explanation for the "copying the XML doesn't work" reports in the forums.

## The 49 keys

Values below are from three real presets. **Confidence is marked** — `verified` means observed varying across samples with a known effect, `inferred` means deduced from key ordering or naming, `unknown` means it never varied.

### Identity
| Key | Example | Confidence |
|---|---|---|
| `bridgeVersion` | `16.0` | verified — the only version marker |
| `name` | `IG 4x5 FullRes 1080x1350 Fill` | verified — display name in the panel |
| `icon` | `S_Preset_16_N` | unknown — identical in all samples |
| `isDefaultPreset` | `0` | inferred — 1 presumably marks a factory preset |
| `uri` | *(empty)* | unknown |

### Destination
| Key | Example | Confidence |
|---|---|---|
| `destinationPath` | `/Users/you/Downloads` | verified — **absolute path, hardcoded.** Repoint after import. |
| `exportToFolderOption` | `1` | inferred — 0 = original file location, 1 = specific folder |
| `saveToSubfolder` | `1` | verified |
| `subfolderName` | `IG_1080x1350` | verified |
| `conflictSavingOptions` | `0` | inferred — 0/1/2 = unique filename / overwrite / skip |

### Format — **this is where the bugs are**
| Key | Example | Confidence |
|---|---|---|
| `exportToFormatOption` | `2` | **verified by output** — `0`=JPEG, `1`=PNG, `2`=TIFF, `3`=DNG |
| `conversionQuality` | `10` | verified — JPEG quality on Bridge's 1–12 scale. Written even when the format isn't JPEG. |
| `jpegExtension` | `0` | inferred — `.jpg` vs `.jpeg` |
| `pngBitDepth`, `pngColorSpace`, `pngSaveTransparency` | `1`,`0`,`1` | unknown |
| `tiffCompression`, `tiffColorSpace`, `tiffBitDepth`, `tiffSaveTransparency` | `0`,`0`,`1`,`0` | unknown |
| `dngJpegPreview`, `dngEmbedOriginal`, `dngDeleteOriginal` | `1`,`0`,`0` | unknown |

**There is no `jpegColorSpace` key.** PNG and TIFF each have one; JPEG does not. This is the schema-level confirmation that Bridge cannot set a colour space on JPEG export — matching Adobe's own docs and the [open feature request from October 2020](https://adobebridge.uservoice.com/forums/905323-feature-request/suggestions/41739760-convert-profile-to-srgb-in-export-tab).

### Sizing
| Key | Example | Confidence |
|---|---|---|
| `constrainToFitOption` | `0` | **suspected master resize toggle** — see below |
| `resizeOption` | `1` | inferred |
| `resizeOptionType` | `2` | inferred — long edge / short edge / W&H |
| `resizeWidth`, `resizeHeight` | `1080.00`, `1350.00` | verified |
| `constraintToFitDimension` | `1080.00` | verified — **tracks `resizeWidth`**, not the long edge; it stayed 1080.00 even in the 1080×566 landscape preset. Note the spelling: `constraint`, not `constrain` as in the key above. |
| `scalingOption` | `1` | **verified** — `1` = Fill (crop), `0` = Fit (letterbox) |
| `scalingPercentage` | `100` | inferred |
| `scalingAlgorithm` | `2` | inferred — bilinear / bicubic / bicubic sharper |
| `enlargeSelected` | `0` | verified — `0` never upscales |
| `resizeMetric`, `resolutionMetric` | `0`, `1` | inferred — px vs other units |
| `resolution` | `300` | verified — PPI tag; irrelevant for screen output |
| `defaultImage` | `0` | unknown |

### Metadata
| Key | Example | Confidence |
|---|---|---|
| `includeOriginalMetadata` | `1` | verified |
| `includeOriginalMetadataValue` | `0` | inferred — which subset |
| `noLocationInfo` | `1` | verified — **`1` strips GPS on export.** Leave it at 1 for anything public. |
| `metadataTemplateSelected`, `metadataTemplateName`, `metadataTemplateOperation` | `0`, *(empty)*, `0` | inferred |
| `additionalKeywordsEntered` | *(empty)* | verified — semicolon-separated |

### Content Credentials
`credentialsEnabled`, `credentialsAccounts`, `credentialsProducer`, `credentialsEditsActivity`, `credentialsStorageMethod` — all `0`. Unknown.

## Worked failure analysis

A real preset set produced **full-resolution TIFFs** into a folder named `IG_1080x1350`, instead of 1080×1350 JPEGs. Two fields explain it exactly:

1. **`exportToFormatOption` = `2` → TIFF, not JPEG.** The format-specific key blocks appear in the order jpeg → png → tiff → dng, implying `0`=JPEG. A preset intended to make JPEGs must set this to `0`.
2. **`constrainToFitOption` = `0` while `resizeWidth`/`resizeHeight` were populated.** The dimensions were inert; Bridge emitted native resolution.

This isn't speculation — the output folder was inspected and contained 35–78 MB TIFFs at the camera's native 6048×4024, in a directory whose name matches the preset's `subfolderName`. The preset and its output were matched, and both fields' effects are visible in the result.

**A working JPEG preset therefore needs `exportToFormatOption=0`, and the resize path enabled.**

The generator in [`../tools/make-bridge-preset.py`](../tools/make-bridge-preset.py) sets both, and additionally sets `resizeOption=1` and `constrainToFitOption=1` together, since which of those two is the real gate is not yet isolated.

## Isolating the remaining unknowns

The unknown keys are cheap to map, and the method is the same for all of them. **Change one field at a time.**

1. In Bridge, create a preset and export it (or copy the file out of `ExportPreset/`).
2. Change exactly one setting in the UI. Save. Export again.
3. `diff` the two files. The line that changed is that setting's key, and you've learned one value of its enum.
4. Repeat for each enum value.

Two settings changed at once and you cannot attribute either. The three samples that produced this document differ by only 3–4 lines each, which is precisely why they were readable.

Highest-value fields still to map: `constrainToFitOption` vs `resizeOption` (which one actually gates resizing), `resizeOptionType`, `scalingAlgorithm`, and `conflictSavingOptions`.

## Practical guidance

Bridge export presets are excellent for **screen delivery** — Instagram sizes, web previews, contact sheets. Fast, native, no scripting.

They are **not** a print path, because of the missing `jpegColorSpace`. A print lab needs a known embedded profile; WHCC for example [states plainly](https://www.whcc.com/help/color-management/icc-profiles/) that without one "you will have unpredictable color in your prints." For print output, use [`../tools/print-export.jsx`](../tools/print-export.jsx), which converts and embeds explicitly.

Use both. They solve different problems.
