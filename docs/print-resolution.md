# Print resolution — the arithmetic, and why it usually says no

The single most useful thing an export pipeline can do is refuse to offer a print size the file cannot hold. This page is the arithmetic behind `manifest.csv` in [`../tools/print-export.jsx`](../tools/print-export.jsx).

## The formula

```
achievable_dpi = min( long_edge_px / long_edge_in , short_edge_px / short_edge_in )
```

Take the **minimum**, not the average and not the long edge alone. The binding constraint is whichever edge runs out first, and for a 3:2 frame into a 4:5 print that is always the short edge.

Compare long-to-long and short-to-short so the result is orientation-agnostic.

## Thresholds

| DPI | Verdict |
|---|---|
| ≥ 300 | The target. Every lab's stated optimum. |
| 240–299 | Sellable. Indistinguishable from 300 at any normal viewing distance. |
| 200–239 | Marginal. Defensible for large pieces viewed at distance; state it honestly. |
| < 200 | Don't list it. |

These are conventions, not lab rules. **WHCC, for example, publishes no minimum PPI at all** — their [Image Resolution page](https://www.whcc.com/help/file-prep/image-resolution/) says "generally speaking, the original file needs to be as close to the desired print size as possible when it's at 300ppi", then gives a viewing-distance procedure for printing *larger* than that optimum. The only hard PPI figure anywhere on their site is 1200 PPI for engraving — which shows they do state minimums when they have one.

So 240 is a self-imposed floor. Pick yours deliberately and write it down.

## What this means in practice

Pixels needed at 240 DPI:

| Print size | Pixels required | Megapixels |
|---|---|---|
| 8×12 | 1920 × 2880 | 5.5 |
| 12×18 | 2880 × 4320 | 12.4 |
| 16×20 | 3840 × 4800 | 18.4 |
| 16×24 | 3840 × 5760 | 22.1 |
| 20×30 | 4800 × 7200 | 34.6 |
| 24×36 | 5760 × 8640 | 49.8 |
| 30×40 | 7200 × 9600 | 69.1 |
| **40×60** | **9600 × 14400** | **138.2** |

Read that last row again. **A 40×60 at 240 DPI needs 138 megapixels.** A 45MP body reaches 137 DPI. A 102MP medium-format back reaches 194. Nothing in normal circulation fills a 40×60 natively.

This is why print stores quietly ship upscaled files. That can be a legitimate choice — WHCC themselves recommend AI upscaling for going beyond the optimum size — but it should be a **stated** choice, not something the pipeline does silently.

## Cropping costs more than people expect

A 3:2 frame into a 4:5 print (16×20, 24×30) throws away ~17% of the long edge. A 3:2 into 3:4 (30×40) throws away ~25%.

Worse, the crop doesn't buy you DPI. Cropping a 6048×4024 frame to 4:5 gives 5030×4024 — and 5030/20 = 251, exactly the same as the uncropped short-edge constraint of 4024/16 = 251. You lost a third of the image for nothing.

**If your source is uniformly one aspect ratio, build the ladder from sizes in that ratio.** For 3:2 that's 4×6, 8×12, 12×18, 16×24, 20×30, 24×36 — and the pipeline never has to make a crop decision, which is an authorship judgement a script should not be making anyway.

## Telephoto work caps low

Wildlife, aviation and sports frames are usually cropped in post — sometimes heavily. A 24MP body cropped to half the frame is a 12MP file, which caps at 12×18 and cannot reach 16×24.

That isn't a defect, it's the nature of the work. It does mean the product is small-to-mid format, and that revenue has to come from **finishing** — mounting, lamination, framing, metal — rather than from size. Finishing needs no additional pixels.
