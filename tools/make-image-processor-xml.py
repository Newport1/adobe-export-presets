#!/usr/bin/env python3
"""
Generate a Photoshop "Image Processor.xml" settings file.

Photoshop's Image Processor reads its saved settings with a hand-rolled line
parser, not an XML parser. That means the output has to match its writer
exactly: a UTF-8 BOM, one <tag>value</tag> per line, tab-indented, wrapped in
<ImageProcessor>. Reformat it and the parser silently misreads it.

See ../docs/image-processor-xml.md for the schema and its provenance.

Usage:
    python3 make-image-processor-xml.py --source ~/edits --dest ~/out \
        --jpeg --quality 12 --convert-srgb --resize 2048 2048 -o "Image Processor.xml"
"""

import argparse
import sys

# Written in this order. The reader tolerates any order, but matching the
# writer's field order keeps a generated file diffable against a real one.
FIELD_ORDER = [
    "version", "useopen", "includesub", "source", "open", "saveinsame", "dest",
    "jpeg", "psd", "tiff", "lzw", "converticc", "q", "max",
    "jpegresize", "jpegw", "jpegh",
    "psdresize", "psdw", "psdh",
    "tiffresize", "tiffw", "tiffh",
    "runaction", "actionset", "action",
    "info", "icc", "keepstructure",
]

DEFAULTS = {
    "version": "3.0",
    "useopen": "false", "includesub": "false", "source": "", "open": "false",
    "saveinsame": "false", "dest": "",
    "jpeg": "true", "psd": "false", "tiff": "false", "lzw": "true",
    "converticc": "true", "q": "10", "max": "false",
    "jpegresize": "false", "jpegw": "0", "jpegh": "0",
    "psdresize": "false", "psdw": "0", "psdh": "0",
    "tiffresize": "false", "tiffw": "0", "tiffh": "0",
    "runaction": "false", "actionset": "", "action": "",
    "info": "", "icc": "true", "keepstructure": "false",
}


def build(params):
    """Return the exact byte layout Photoshop's reader expects."""
    lines = ["<ImageProcessor>"]
    for key in FIELD_ORDER:
        lines.append("\t<%s>%s</%s>" % (key, params[key], key))
    lines.append("</ImageProcessor>")
    # Writer uses writeln, so every line including the last ends with a newline.
    return "﻿" + "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", required=True, help="Folder of images to process")
    p.add_argument("--dest", help="Output folder. Omit to save alongside the originals.")
    p.add_argument("--include-subfolders", action="store_true")
    p.add_argument("--jpeg", action="store_true", help="Emit JPEG (default if no format given)")
    p.add_argument("--psd", action="store_true")
    p.add_argument("--tiff", action="store_true")
    p.add_argument("--no-lzw", action="store_true", help="Disable LZW on TIFF output")
    p.add_argument("--quality", type=int, default=10, metavar="1-12",
                   help="JPEG quality (default 10; WHCC asks for 10 or higher)")
    p.add_argument("--convert-srgb", action="store_true",
                   help="Convert Profile to sRGB. NOTE: Photoshop applies this to JPEG ONLY - "
                        "PSD and TIFF output are not converted regardless of this flag.")
    p.add_argument("--no-icc", action="store_true",
                   help="Do not embed an ICC profile. Leave this off for print work - "
                        "labs need the profile to know what space the file is in.")
    p.add_argument("--resize", nargs=2, type=int, metavar=("W", "H"),
                   help="Fit within W x H pixels, applied to every enabled format")
    p.add_argument("--action", nargs=2, metavar=("SET", "ACTION"),
                   help="Run a Photoshop action on each file")
    p.add_argument("--copyright", default="", help="Copyright string written to metadata")
    p.add_argument("-o", "--out", default="Image Processor.xml")
    args = p.parse_args()

    if not (1 <= args.quality <= 12):
        sys.exit("error: --quality must be 1-12 (Photoshop's scale, not 0-100)")

    params = dict(DEFAULTS)
    params["source"] = args.source
    params["includesub"] = "true" if args.include_subfolders else "false"

    if args.dest:
        params["dest"] = args.dest
        params["saveinsame"] = "false"
    else:
        params["saveinsame"] = "true"

    want_jpeg = args.jpeg or not (args.psd or args.tiff)
    params["jpeg"] = "true" if want_jpeg else "false"
    params["psd"] = "true" if args.psd else "false"
    params["tiff"] = "true" if args.tiff else "false"
    params["lzw"] = "false" if args.no_lzw else "true"
    params["q"] = str(args.quality)
    params["converticc"] = "true" if args.convert_srgb else "false"
    params["icc"] = "false" if args.no_icc else "true"
    params["info"] = args.copyright

    if args.resize:
        w, h = args.resize
        for fmt in ("jpeg", "psd", "tiff"):
            if params[fmt] == "true":
                params[fmt + "resize"] = "true"
                params[fmt + "w"] = str(w)
                params[fmt + "h"] = str(h)

    if args.action:
        params["runaction"] = "true"
        params["actionset"], params["action"] = args.action

    with open(args.out, "w", encoding="utf-8", newline="") as fh:
        fh.write(build(params))

    print("Wrote %s" % args.out)
    if args.convert_srgb and (args.psd or args.tiff):
        print("  note: --convert-srgb affects JPEG output only. Your PSD/TIFF files will")
        print("        keep their source colour space (tagged, but not converted).")
    if args.no_icc:
        print("  warning: ICC embedding is off. Print labs treat untagged files as")
        print("           unpredictable colour.")


if __name__ == "__main__":
    main()
