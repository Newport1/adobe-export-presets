/**
 * print-export.jsx
 * Photoshop batch export: curated edits -> lab-ready print masters + web previews + a resolution manifest.
 *
 * WHY THIS IS A SCRIPT AND NOT A BRIDGE EXPORT PRESET
 * ---------------------------------------------------
 * Use a Bridge export preset for screen delivery - it is faster and native, and
 * the format IS hand-authorable (see ../docs/bridge-export-presets.md and
 * ../tools/make-bridge-preset.py).
 *
 * Use this script for PRINT, for one reason: Bridge's JPEG export exposes a
 * single setting, quality. There is no colour-space control on JPEG at all -
 * Color Space appears only under PNG and TIFF, and the preset schema confirms
 * it, carrying pngColorSpace and tiffColorSpace but no jpegColorSpace. Print
 * labs require an embedded RGB profile; WHCC warns that untagged files give
 * "unpredictable color". A Bridge JPEG preset cannot guarantee one.
 *
 * This script converts to sRGB and embeds the profile explicitly, and emits the
 * resolution manifest a print catalog needs. The two tools are complements, not
 * alternatives.
 *
 * WHAT IT PRODUCES, next to your source folder:
 *   _export/print-masters/<name>.jpg   full resolution, no resampling, sRGB,
 *                                      profile embedded, quality 12, 300 PPI tag
 *   _export/web/<name>_web.jpg         long edge 2048, sRGB, quality 9
 *   _export/manifest.csv               per image: pixels, aspect, megapixels, and
 *                                      PASS/FAIL for every print size you sell
 *
 * The manifest is the point. It answers "which sizes can this file honestly be
 * sold at" with arithmetic instead of optimism, and it is the input to the
 * catalog generator described in PRINT-FULFILLMENT-HANDOFF.md.
 *
 * WHAT IT DELIBERATELY DOES NOT DO
 *   - It never crops. Every EHP size is 2:3, which is the native frame, so no
 *     crop is needed there. Drylake mixes 4:5 (16x20, 24x30), 3:4 (30x40) and
 *     2:3 (24x36, 40x60) - those crops are an authorship decision and a script
 *     should not make them for you. The manifest tells you which sizes need one.
 *   - It never upscales. A file that cannot hold 40x60 is reported as failing
 *     40x60, not silently interpolated up to it.
 *   - It never writes to your originals. Each file is opened, exported as a
 *     copy, and closed without saving.
 *
 * HOW TO RUN (Windows, no admin, no restart)
 *   Photoshop > File > Scripts > Browse...  and pick this file.
 *   To get it in the menu permanently instead, drop it in
 *   C:\Program Files\Adobe\Adobe Photoshop 2025\Presets\Scripts\ (needs admin)
 *   and restart Photoshop; it then appears under File > Scripts.
 *
 * Tested against: written for Photoshop CC 2019+ ExtendScript. NOT executed by
 * its author - run it on three files before you run it on ninety.
 */

#target photoshop

// ---------------------------------------------------------------------------
// CONFIG - edit these
// ---------------------------------------------------------------------------

// WHCC accepts sRGB, Adobe RGB (1998) and P3, and says "if you are unsure, you
// probably want sRGB IEC61966-2.1". Change to "Adobe RGB (1998)" only if you
// actually soft-proof. The string must match Photoshop's profile name exactly.
var OUTPUT_PROFILE = "sRGB IEC61966-2.1";

var MASTER_QUALITY   = 12;    // WHCC asks for JPEG quality 10 or higher
var WEB_QUALITY      = 9;
var WEB_LONG_EDGE    = 2048;  // px
var MASTER_PPI       = 300;   // metadata only - no resampling is performed
var SHARPEN_WEB      = true;  // output sharpening on the downsized web preview
var DPI_FLOOR        = 240;   // below this, do not sell the size
var DPI_PREFERRED    = 300;   // WHCC's stated target

// Every size either store sells. label, inches long, inches short, which site.
var PRINT_SIZES = [
  { label: "8x12",  w:  8, h: 12, site: "EHP",     ratio: "2:3" },
  { label: "12x18", w: 12, h: 18, site: "EHP",     ratio: "2:3" },
  { label: "16x24", w: 16, h: 24, site: "EHP",     ratio: "2:3" },
  { label: "20x30", w: 20, h: 30, site: "EHP",     ratio: "2:3" },
  { label: "24x36", w: 24, h: 36, site: "both",    ratio: "2:3" },
  { label: "16x20", w: 16, h: 20, site: "Drylake", ratio: "4:5" },
  { label: "24x30", w: 24, h: 30, site: "Drylake", ratio: "4:5" },
  { label: "30x40", w: 30, h: 40, site: "Drylake", ratio: "3:4" },
  { label: "40x60", w: 40, h: 60, site: "Drylake", ratio: "2:3" }
];

var VALID_EXT = "jpg,jpeg,tif,tiff,psd,png,dng,nef";

// ---------------------------------------------------------------------------

function main() {
  if (!isPhotoshop()) {
    alert("Run this from Photoshop (File > Scripts > Browse...), not from Bridge.");
    return;
  }

  var srcFolder = Folder.selectDialog("Select the folder of curated, edited photos");
  if (srcFolder === null) { return; }

  var files = collectImages(srcFolder);
  if (files.length === 0) {
    alert("No images found in:\n" + srcFolder.fsName + "\n\nLooked for: " + VALID_EXT);
    return;
  }

  var outRoot   = new Folder(srcFolder.fsName + "/_export");
  var outMaster = new Folder(outRoot.fsName + "/print-masters");
  var outWeb    = new Folder(outRoot.fsName + "/web");
  mkdirp(outRoot); mkdirp(outMaster); mkdirp(outWeb);

  // Preserve and suppress dialogs so a stray profile-mismatch prompt cannot
  // stall an unattended run halfway through.
  var savedDialogs = app.displayDialogs;
  var savedRuler   = app.preferences.rulerUnits;
  app.displayDialogs      = DialogModes.NO;
  app.preferences.rulerUnits = Units.PIXELS;

  var rows = [];
  var okCount = 0, failCount = 0;
  var errors = [];

  for (var i = 0; i < files.length; i++) {
    var f = files[i];
    var doc = null;
    try {
      doc = app.open(f);

      // Normalise: flatten, 8-bit, RGB, converted to the output profile with an
      // embedded tag. Order matters - convert the profile BEFORE dropping to
      // 8-bit so the conversion has the extra precision to work with.
      if (doc.mode !== DocumentMode.RGB) { doc.changeMode(ChangeMode.RGB); }
      if (doc.layers.length > 1 || doc.activeLayer.isBackgroundLayer === false) { doc.flatten(); }
      try {
        doc.convertProfile(OUTPUT_PROFILE, Intent.RELATIVECOLORIMETRIC, true, true);
      } catch (profErr) {
        errors.push(f.name + ": profile convert failed (" + profErr + ") - exported in its original space");
      }
      if (doc.bitsPerChannel !== BitsPerChannelType.EIGHT) {
        doc.bitsPerChannel = BitsPerChannelType.EIGHT;
      }

      var pxW = doc.width.as("px");
      var pxH = doc.height.as("px");

      // Tag 300 PPI without touching pixels. ResampleMethod.NONE is what makes
      // this a metadata change rather than an interpolation.
      doc.resizeImage(undefined, undefined, MASTER_PPI, ResampleMethod.NONE);

      var base = stripExt(f.name);

      // --- print master: full resolution, nothing thrown away ---
      saveJpeg(doc, new File(outMaster.fsName + "/" + base + ".jpg"), MASTER_QUALITY);

      // --- web preview: downsized copy ---
      var longEdge = Math.max(pxW, pxH);
      if (longEdge > WEB_LONG_EDGE) {
        var scale = WEB_LONG_EDGE / longEdge;
        doc.resizeImage(
          UnitValue(Math.round(pxW * scale), "px"),
          UnitValue(Math.round(pxH * scale), "px"),
          72,
          ResampleMethod.BICUBICSHARPER
        );
        if (SHARPEN_WEB) {
          try { doc.activeLayer.applyUnSharpMask(60, 0.6, 3); } catch (shErr) { /* non-fatal */ }
        }
      }
      saveJpeg(doc, new File(outWeb.fsName + "/" + base + "_web.jpg"), WEB_QUALITY);

      rows.push(buildRow(f.name, pxW, pxH));
      okCount++;
    } catch (e) {
      failCount++;
      errors.push(f.name + ": " + e);
      rows.push(csvEsc(f.name) + ",ERROR,,,,," + repeatCommas(PRINT_SIZES.length));
    } finally {
      if (doc !== null) {
        try { doc.close(SaveOptions.DONOTSAVECHANGES); } catch (closeErr) { /* already gone */ }
      }
    }
  }

  writeManifest(new File(outRoot.fsName + "/manifest.csv"), rows);

  app.displayDialogs         = savedDialogs;
  app.preferences.rulerUnits = savedRuler;

  var msg = "Done.\n\n"
    + okCount + " exported, " + failCount + " failed\n\n"
    + "Masters : " + outMaster.fsName + "\n"
    + "Web     : " + outWeb.fsName + "\n"
    + "Manifest: " + outRoot.fsName + "\\manifest.csv\n\n"
    + "Open the manifest before listing anything - it says which sizes each\n"
    + "file can actually hold at " + DPI_FLOOR + " DPI.";
  if (errors.length > 0) {
    msg += "\n\nProblems:\n" + errors.slice(0, 12).join("\n");
    if (errors.length > 12) { msg += "\n...and " + (errors.length - 12) + " more"; }
  }
  alert(msg);
}

// --- manifest -------------------------------------------------------------

function buildRow(name, pxW, pxH) {
  var longPx  = Math.max(pxW, pxH);
  var shortPx = Math.min(pxW, pxH);
  var mp      = (pxW * pxH) / 1000000;
  var ratio   = simplifyRatio(longPx, shortPx);

  var cells = [
    csvEsc(name),
    pxW,
    pxH,
    round1(mp),
    ratio
  ];

  for (var i = 0; i < PRINT_SIZES.length; i++) {
    var s = PRINT_SIZES[i];
    // Compare long edge to long edge and short to short - orientation agnostic.
    var sLong  = Math.max(s.w, s.h);
    var sShort = Math.min(s.w, s.h);
    var dpi = Math.min(longPx / sLong, shortPx / sShort);
    var verdict;
    if (dpi >= DPI_PREFERRED)   { verdict = "YES " + Math.floor(dpi); }
    else if (dpi >= DPI_FLOOR)  { verdict = "OK " + Math.floor(dpi); }
    else                        { verdict = "NO " + Math.floor(dpi); }
    cells.push(verdict);
  }
  return cells.join(",");
}

function writeManifest(file, rows) {
  var head = ["file", "px_w", "px_h", "megapixels", "native_ratio"];
  for (var i = 0; i < PRINT_SIZES.length; i++) {
    head.push(PRINT_SIZES[i].label + " (" + PRINT_SIZES[i].ratio + " " + PRINT_SIZES[i].site + ")");
  }
  file.encoding = "UTF-8";
  file.open("w");
  file.writeln("# YES = at or above " + DPI_PREFERRED + " DPI. OK = " + DPI_FLOOR + "-" + DPI_PREFERRED
             + " DPI, sellable. NO = below " + DPI_FLOOR + " DPI, do not list. Number is achievable DPI.");
  file.writeln("# DPI assumes the FULL frame is used. A size whose ratio differs from native_ratio");
  file.writeln("# needs a crop first, which lowers the real DPI - re-check those by hand.");
  file.writeln(head.join(","));
  for (var r = 0; r < rows.length; r++) { file.writeln(rows[r]); }
  file.close();
}

// --- helpers --------------------------------------------------------------

function saveJpeg(doc, file, quality) {
  var opts = new JPEGSaveOptions();
  opts.quality           = quality;
  opts.embedColorProfile = true;   // WHCC: untagged files print unpredictably
  opts.formatOptions     = FormatOptions.STANDARDBASELINE;
  opts.matte             = MatteType.NONE;
  doc.saveAs(file, opts, true, Extension.LOWERCASE);  // true = save as copy
}

function collectImages(folder) {
  var exts = VALID_EXT.split(",");
  var all = folder.getFiles();
  var out = [];
  for (var i = 0; i < all.length; i++) {
    if (!(all[i] instanceof File)) { continue; }
    var n = all[i].name.toLowerCase();
    if (n.charAt(0) === ".") { continue; }          // skip ._ resource forks etc
    for (var e = 0; e < exts.length; e++) {
      if (endsWith(n, "." + exts[e])) { out.push(all[i]); break; }
    }
  }
  return out;
}

function simplifyRatio(a, b) {
  var x = Math.round(a), y = Math.round(b);
  var g = gcd(x, y);
  var rx = x / g, ry = y / g;
  // Collapse awkward exact ratios to the nearest familiar one for readability.
  var known = [[3,2,"3:2"],[4,3,"4:3"],[5,4,"5:4"],[16,9,"16:9"],[1,1,"1:1"],[2,1,"2:1"]];
  var val = a / b;
  for (var i = 0; i < known.length; i++) {
    if (Math.abs(val - (known[i][0] / known[i][1])) < 0.01) { return known[i][2]; }
  }
  if (rx > 40 || ry > 40) { return round2(val) + ":1"; }
  return rx + ":" + ry;
}

function gcd(a, b) { while (b) { var t = b; b = a % b; a = t; } return a; }
function round1(n) { return Math.round(n * 10) / 10; }
function round2(n) { return Math.round(n * 100) / 100; }
function endsWith(s, suffix) { return s.length >= suffix.length && s.substr(s.length - suffix.length) === suffix; }
function stripExt(n) { var i = n.lastIndexOf("."); return i > 0 ? n.substring(0, i) : n; }
function csvEsc(s) { return '"' + String(s).replace(/"/g, '""') + '"'; }
function repeatCommas(n) { var s = ""; for (var i = 0; i < n; i++) { s += ","; } return s; }
function mkdirp(f) { if (!f.exists) { f.create(); } }
function isPhotoshop() {
  try { return String(app.name).indexOf("Photoshop") !== -1; } catch (e) { return false; }
}

main();
