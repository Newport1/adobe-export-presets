# Photoshop Image Processor settings XML

**Status: verified schema.** This one really is a plain-text file you can author.

Photoshop's Image Processor (**File → Scripts → Image Processor**, or **Tools → Photoshop → Image Processor** from Bridge) has Save/Load buttons for its settings. What it writes is XML.

Everything below was derived by reading Adobe's shipped `Image Processor.jsx`. Adobe does not document it.

## Default location

The script builds the path as `app.preferencesFolder + "/" + "Image Processor" + ".xml"`:

**Windows**
```
C:\Users\<user>\AppData\Roaming\Adobe\Adobe Photoshop <version>\Adobe Photoshop <version> Settings\Image Processor.xml
```

**macOS**
```
~/Library/Preferences/Adobe Photoshop <version> Settings/Image Processor.xml
```

Save/Load also accept an arbitrary path via a file dialog, filtered to `*.xml`.

## The format

Root element is `<ImageProcessor>` — the script's own title with spaces stripped. The writer is:

```javascript
saveFile.write("\uFEFF");
saveFile.writeln( "<" + scriptNameForXML + ">" );
for ( var p in this.params ) {
    saveFile.writeln( "\t<" + p + ">" + this.params[p] + "</" + p + ">" );
}
saveFile.writeln( "</" + scriptNameForXML + ">" );
```

Three consequences, and they are the whole reason this page exists:

1. **UTF-8 BOM required.** The file starts with `\uFEFF`.
2. **Exactly one tag per line, tab-indented.** The reader is a hand-rolled line parser, not an XML parser.
3. **Do not reformat.** Pretty-printing, attributes, nested elements, comments, or two tags on one line will break it. It is XML-shaped, not XML.

## Parameters

```
version  useopen  includesub  source  open  saveinsame  dest
jpeg  psd  tiff  lzw  converticc  q  max
jpegresize  jpegw  jpegh
psdresize  psdw  psdh
tiffresize  tiffw  tiffh
runaction  actionset  action
info  icc  keepstructure
```

Booleans are written as `true` / `false`. Paths are written as the platform path.

## The gotcha that matters for print

`converticc` — "Convert Profile to sRGB" — is referenced in exactly one place in the processing code: **inside the JPEG branch.** PSD and TIFF output get **no** sRGB conversion regardless of the setting.

`icc` (Include ICC Profile) does apply to all three formats.

So if you use Image Processor to produce TIFFs for a lab, the profile is embedded but *not converted* — you get whatever space the source was in, tagged honestly. That is fine if your sources are consistent and fatal if they aren't.

## Other limitations

- Output goes to fixed subfolders `/JPEG/`, `/PSD/`, `/TIFF/` under the destination. Not configurable.
- No custom filenames or suffixes.
- No sharpening.
- One resize per format, via `FitImage(w, h)`.

If any of those matter, use a `.jsx` instead — see [`../tools/print-export.jsx`](../tools/print-export.jsx).

## Generating one

[`../tools/make-image-processor-xml.py`](../tools/make-image-processor-xml.py) writes a conforming file:

```bash
python3 make-image-processor-xml.py \
    --source "/path/to/edits" \
    --dest   "/path/to/out" \
    --jpeg --quality 12 --convert-srgb \
    --resize 2048 2048 \
    -o "Image Processor.xml"
```

## Verify before you trust it

This schema was read from Adobe's shipped script, but versions drift. Before relying on a generated file:

1. Open Image Processor in your Photoshop, set two distinctive options, click **Save**.
2. Compare that file to a generated one.
3. If they differ structurally, the version on your disk wins — please open an issue with the diff.
