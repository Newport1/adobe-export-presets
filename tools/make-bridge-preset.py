#!/usr/bin/env python3
"""
Generate an Adobe Bridge export preset (.xml).

Bridge presets are a flat list of <data key="..." value="..."/> elements under a
<preset> root. No BOM, LF endings, 8-space indent. See
../docs/bridge-export-presets.md for the full key table and confidence levels.

Import the result in Bridge via Export panel -> preset menu -> Import Preset,
or drop it into:
    macOS   ~/Library/Application Support/Adobe/Bridge <ver>/ExportPreset/
    Windows %APPDATA%\\Adobe\\Bridge <ver>\\ExportPreset\\
A direct drop may need a Bridge restart; importing does not.

Examples:
    # Instagram 4:5, crop to fill
    python3 make-bridge-preset.py --name "IG 4x5" --size 1080 1350 --fill \\
        --subfolder IG_1080x1350 --dest ~/Downloads

    # Web previews, long edge 2048, no crop
    python3 make-bridge-preset.py --name "Web 2048" --size 2048 2048 --fit \\
        --subfolder web --dest ~/Downloads --quality 9

NOTE ON PRINT: Bridge cannot set a colour space on JPEG export - there is no
jpegColorSpace key in the schema. If the output is going to a print lab, use
../tools/print-export.jsx instead, which converts and embeds a profile.
"""

import argparse
import sys
from pathlib import Path

FORMATS = {"jpeg": "0", "png": "1", "tiff": "2", "dng": "3"}

# Written in this exact order. Bridge's own presets use it, so keeping it makes
# a generated file diffable against one exported from the UI.
KEY_ORDER = [
    "bridgeVersion", "name", "icon", "isDefaultPreset", "uri",
    "conversionQuality", "destinationPath", "conflictSavingOptions",
    "saveToSubfolder", "subfolderName", "exportToFolderOption",
    "constrainToFitOption", "resizeOption", "resizeOptionType", "resizeMetric",
    "resolutionMetric", "defaultImage", "resizeWidth", "resizeHeight",
    "enlargeSelected", "resolution", "scalingOption",
    "constraintToFitDimension", "scalingPercentage", "scalingAlgorithm",
    "includeOriginalMetadata", "includeOriginalMetadataValue", "noLocationInfo",
    "metadataTemplateSelected", "metadataTemplateName",
    "metadataTemplateOperation", "additionalKeywordsEntered",
    "exportToFormatOption", "jpegExtension",
    "pngBitDepth", "pngColorSpace", "pngSaveTransparency",
    "tiffCompression", "tiffColorSpace", "tiffBitDepth", "tiffSaveTransparency",
    "dngJpegPreview", "dngEmbedOriginal", "dngDeleteOriginal",
    "credentialsEnabled", "credentialsAccounts", "credentialsProducer",
    "credentialsEditsActivity", "credentialsStorageMethod",
]

DEFAULTS = {
    "bridgeVersion": "16.0",
    "name": "Untitled preset",
    "icon": "S_Preset_16_N",
    "isDefaultPreset": "0",
    "uri": "",
    "conversionQuality": "10",
    "destinationPath": "",
    "conflictSavingOptions": "0",
    "saveToSubfolder": "1",
    "subfolderName": "export",
    "exportToFolderOption": "1",
    # Both of these are set together: which one actually gates resizing has not
    # been isolated yet, and a preset that resizes needs whichever it is.
    "constrainToFitOption": "1",
    "resizeOption": "1",
    "resizeOptionType": "2",
    "resizeMetric": "0",
    "resolutionMetric": "1",
    "defaultImage": "0",
    "resizeWidth": "1080.00",
    "resizeHeight": "1350.00",
    "enlargeSelected": "0",
    "resolution": "300",
    "scalingOption": "1",
    "constraintToFitDimension": "1080.00",
    "scalingPercentage": "100",
    "scalingAlgorithm": "2",
    "includeOriginalMetadata": "1",
    "includeOriginalMetadataValue": "0",
    "noLocationInfo": "1",
    "metadataTemplateSelected": "0",
    "metadataTemplateName": "",
    "metadataTemplateOperation": "0",
    "additionalKeywordsEntered": "",
    "exportToFormatOption": "0",
    "jpegExtension": "0",
    "pngBitDepth": "1", "pngColorSpace": "0", "pngSaveTransparency": "1",
    "tiffCompression": "0", "tiffColorSpace": "0", "tiffBitDepth": "1",
    "tiffSaveTransparency": "0",
    "dngJpegPreview": "1", "dngEmbedOriginal": "0", "dngDeleteOriginal": "0",
    "credentialsEnabled": "0", "credentialsAccounts": "0",
    "credentialsProducer": "0", "credentialsEditsActivity": "0",
    "credentialsStorageMethod": "0",
}

INDENT = " " * 8


def esc(v):
    """XML attribute-value escaping. Bridge writes raw text, but a name with an
    ampersand or a path with a quote would produce malformed XML."""
    return (str(v).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def build(params):
    lines = ['<?xml version="1.0" encoding="utf-8"?>', "<preset>"]
    for key in KEY_ORDER:
        lines.append('%s<data key="%s" value="%s"/>' % (INDENT, key, esc(params[key])))
    lines.append("</preset>")
    return "\n".join(lines) + "\n"     # LF, trailing newline, no BOM


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--name", required=True, help="Preset name shown in the Export panel")
    p.add_argument("--size", nargs=2, type=float, required=True, metavar=("W", "H"))
    p.add_argument("--dest", required=True,
                   help="Absolute destination path. Bridge hardcodes this into the preset.")
    p.add_argument("--subfolder", default="export")
    p.add_argument("--no-subfolder", action="store_true")
    fit = p.add_mutually_exclusive_group()
    fit.add_argument("--fill", action="store_true", help="Crop to fill the box (default)")
    fit.add_argument("--fit", action="store_true", help="Letterbox, never crop")
    p.add_argument("--format", choices=list(FORMATS), default="jpeg")
    p.add_argument("--quality", type=int, default=10, metavar="1-12",
                   help="JPEG quality on Bridge's 1-12 scale (default 10)")
    p.add_argument("--resolution", type=int, default=300, help="PPI tag (default 300)")
    p.add_argument("--allow-enlarge", action="store_true",
                   help="Permit upscaling of undersized originals. Off by default, and you")
    p.add_argument("--keep-location", action="store_true",
                   help="Keep GPS metadata. OFF by default - do not enable for public output.")
    p.add_argument("--bridge-version", default="16.0")
    p.add_argument("-o", "--out", help="Output path (default: <name>.xml in cwd)")
    args = p.parse_args()

    if not (1 <= args.quality <= 12):
        sys.exit("error: --quality is Bridge's 1-12 scale, not 0-100")
    dest = Path(args.dest).expanduser()
    if not dest.is_absolute():
        sys.exit("error: --dest must be an absolute path; Bridge stores it verbatim")

    w, h = args.size
    params = dict(DEFAULTS)
    params.update({
        "bridgeVersion": args.bridge_version,
        "name": args.name,
        "destinationPath": str(dest),
        "saveToSubfolder": "0" if args.no_subfolder else "1",
        "subfolderName": "" if args.no_subfolder else args.subfolder,
        "resizeWidth": "%.2f" % w,
        "resizeHeight": "%.2f" % h,
        # Tracks resizeWidth in every reference preset, including the landscape
        # one where width happened to be the LONG edge - so it is not max(w,h).
        "constraintToFitDimension": "%.2f" % w,
        "scalingOption": "0" if args.fit else "1",
        "conversionQuality": str(args.quality),
        "resolution": str(args.resolution),
        "exportToFormatOption": FORMATS[args.format],
        "enlargeSelected": "1" if args.allow_enlarge else "0",
        "noLocationInfo": "0" if args.keep_location else "1",
    })

    out = Path(args.out) if args.out else Path(args.name.replace(" ", "_") + ".xml")
    out.write_text(build(params), encoding="utf-8", newline="")
    print("Wrote %s" % out)
    print("  format   %s  (exportToFormatOption=%s)" % (args.format.upper(), FORMATS[args.format]))
    print("  size     %g x %g, %s" % (w, h, "Fit" if args.fit else "Fill"))
    print("  dest     %s%s" % (dest, "" if args.no_subfolder else "/" + args.subfolder))
    if args.keep_location:
        print("  WARNING: GPS metadata will be retained in exported files.")
    if args.format != "jpeg":
        print("  note: non-JPEG output. Check the %s* keys in the docs - this generator" % args.format)
        print("        leaves them at defaults and they have not been mapped." )


if __name__ == "__main__":
    main()
