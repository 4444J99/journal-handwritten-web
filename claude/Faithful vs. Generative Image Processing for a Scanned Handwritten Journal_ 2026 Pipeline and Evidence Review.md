# Faithful vs. Generative Processing for a Scanned Handwritten Journal (state of the art, late 2026)

**Bottom line: use only deterministic, documented classical processing for every use where the letterforms matter (transcription checks, font harvesting, copyright deposit). Treat learned super-resolution, especially diffusion upscalers, as a separately labelled display-only layer. If the physical notebook still exists, a fresh 400–600 ppi capture beats any upscaler for every purpose.** Published 2025–2026 research shows that generative SR invents, merges and drops strokes in text. No method that "adds detail" can be verified against ink that was never sampled.

## TL;DR
- **Faithful (keep for transcription, font and deposit):** geometric correction (deskew, dewarp), background flattening, tone curves, mild denoising, soft ink/paper separation, and classical interpolation (Lanczos/bicubic) are all deterministic and auditable. Run them with OpenCV, scikit-image, libvips, ImageMagick or ScanTailor Advanced, and record the recipe in a manifest.
- **Inventive (display tier only, clearly labelled):** Real-ESRGAN, SwinIR/HAT (GAN variants) and diffusion upscalers such as SUPIR or SeedVR2 produce plausible strokes that are not in the source. A 2026 study built a dataset of more than 3.2M text crops specifically because diffusion SR "often produce[s] text hallucinations: non-existent or distorted text." Use ×2 at most, only on clean source pixels, and only after the checks in the trial plan below. Avoid SUPIR (non-commercial licence) for a sellable artwork.
- **Best payoff:** if the notebook is available, rescan at 400 ppi (FADGI 4-star for manuscripts) or 600 ppi (Metamorfoze for originals smaller than A5). Use 16-bit colour with a target, then run Kraken/eScriptorium (fine-tuned on your own lines) plus a frontier vision-language model as two independent second opinions on the 306 uncertain readings.

## Key Findings

### 1. What counts as "faithful"
FADGI's Code of Ethics is a useful yardstick. It accepts "contrast and brightness adjustments, dodging, burning" but says enhancements such as "digital infill… over sharpening… removal of blemishes… and other transformative image processing" should be avoided. It also recommends metadata documenting any processing.\[1\] For FADGI 4-star masters, "no software de-skew is permitted," and "no image retouching is permitted to master files," while "image processing techniques are approved for the creation of access files."\[2\] This matches your three tiers: an untouched master, a documented access derivative, and a separate display derivative.

### 2. Generative SR demonstrably invents text
- **TGSR (Samsung AIC-Toronto et al., arXiv 2610.14281, 2026)** states that diffusion SR priors "often produce text hallucinations: non-existent or distorted text." The causes it identifies are "when the generative prior overrides insufficient evidence in the low-resolution (LR) input, or when the content falls outside the prior distribution (e.g., unseen fonts… scripts)."\[3\] A personal hand is by definition outside the prior. TGSR's fix is to steer unreliable text regions back toward "a non-diffusion upsampled LR image."\[3\] In other words, the faithful fallback is classical interpolation.
- **TADiSR (arXiv 2506.04641, 2025)** reports that on handwritten text, competing methods (R-ESRGAN, HAT, SeeSR, SUPIR, OSEDiff) "result in missing or merged strokes." It also says generic diffusion SR methods "tend to produce more severe stroke distortions, sometimes resulting in completely unrecognizable patterns."\[4\]\[5\] This evidence is qualitative only.
- **Task-driven document SR (arXiv 2506.06953, 2025)** observes that SR makes "faint strokes become bolder," which is exactly the letter-thickening risk. It notes that "higher ratios often lead to unstable optimization and hallucinated content," and every SR variant scored *worse than bicubic* on PSNR, SSIM and LPIPS.\[6\]
- **Text-specific SR** (TextZoom/TSRN, arXiv 2005.03341) is trained on cropped scene-text words. It improves recognizer accuracy, but its goal is legibility to a recognizer, not stroke fidelity.\[7\] The diffusion text-SR literature (arXiv 2312.08886) notes that even MARCONet "will still generate some inaccurate and unpleasant strokes."\[8\]
- **Gap in the evidence:** I found no published 2023–2026 study reporting HTR character error rate (CER) before and after Real-ESRGAN/SwinIR/HAT/diffusion SR on a handwriting dataset such as IAM. The handwriting-specific evidence is qualitative. You will need to measure it on your own pages (see the trial plan).

### 3. Capture beats upscaling
- **FADGI 3rd ed. (May 2023):** for unbound manuscripts and rare materials, 3-star is ≥294 ppi and 4-star is ≥396 ppi with 16-bit.\[9\] FADGI also says "image capture resolutions above 400 ppi may be appropriate for some materials."\[10\] FADGI calls 3-star the sensible baseline for most projects.\[11\]
- **Metamorfoze v2.0 (April 2025):** 300 ppi for originals ≥A5 and 600 ppi for originals smaller than A5. Its basic principle is that "all visible information in the original must be visible in the preservation master."\[12\]
- A typical pocket or A5 journal therefore points to **600 ppi, 16-bit RGB TIFF, with a colour target in frame, even diffuse lighting, and the page held flat** (glass or a V-cradle). Physical rescanning adds real ink information. Upscaling can only interpolate (faithful but soft) or guess (sharp but invented).

### 4. HTR as a second opinion
- **Vision-language models (VLMs):** in the *Journal of Documentation* benchmark (Crosilla et al., 2025, arXiv 2503.15195), GPT-4o-mini scored **1.71% CER on IAM** (modern English). The authors conclude that "proprietary LLM models are the best performing, in particular on modern handwriting." They also found that LLMs "do not possess a significant capability for self-correction."\[13\] A 2026 forms benchmark (Pather, Fouché et al., arXiv 2604.16504, on 49 real South African maternity case records) found free-text fields far harder: the best model, Gemini 3.1, reached a free-text CER of 0.31 (WER 0.50), and GPT-5.4 had the lowest hallucination rate (6%). The lesson is that clean journal lines can be read very well, but VLMs can also confidently "normalize" what you actually wrote.
- **Trainable open-source engines:** Kraken/eScriptorium fine-tune on your own line ground truth. Transkribus (PyLaia engine, a proprietary service) states that "25–50 transcribed pages are enough to start training."\[14\] It also says that for a single consistent hand, "15–30 pages of Ground Truth typically achieve good results (CER under 5%)."\[15\] These are vendor claims. Independent studies show that validation-set CER often understates real test CER: in a 2023 MDPI *Heritage* study of the multilingual Valkema archive, a Transkribus English model fine-tuned on 87 pages reported 2.1% validation CER but measured 11.1% CER (SD 12.8%) on the real test set.
- **For your 306 uncertain readings:** treat agreement between two independent engines (a fine-tuned Kraken model and a VLM) as supporting evidence, and treat disagreement as a flag for human re-reading. Never let either engine overwrite your reading automatically.

## Comparison table

| Method / tool | Faithfulness | Quality for handwriting | Speed (123 pages) | Install in Linux sandbox | Licence / commercial notes |
|---|---|---|---|---|---|
| Lanczos/bicubic resize (libvips, Pillow, ImageMagick) | **Faithful** (deterministic, adds no detail) | Soft above ×2 | Seconds | pip/apt | libvips LGPL-2.1+; Pillow/ImageMagick permissive\[16\] |
| Deskew, crop, background flattening, tone curves (OpenCV, scikit-image) | **Faithful** | Excellent if parameters are conservative | Seconds–minutes | pip | Apache-2.0 / BSD |
| ScanTailor Advanced (deskew, content box, illumination normalisation, manual/auto dewarp)\[17\] | **Faithful** (geometric resampling) | Very good; mixed/colour output preserves tone | Minutes, GUI or CLI | apt/build; easier as a local GUI on macOS | GPL (tool only; outputs unaffected) |
| page-dewarp (cubic sheet model) | **Faithful** (parametric warp) | Good on smooth curl; can fail on sparse handwriting | Fast | pip | MIT |
| UVDoc / uvdoc-onnx (neural grid unwarp) | **Mostly faithful** (learned geometry, but pixels are resampled, not generated) | Good on curl/crumple; verify line straightness | Fast (ONNX, CPU) | `pip install uvdoc-onnx` (weights bundled) | MIT |
| DocRes (dewarp, deshadow, appearance, binarize)\[18\] | **Learned:** geometric/deshadow tasks are low-risk; appearance/deblur/binarize can alter strokes | Strong on benchmarks | GPU preferred | Code on GitHub; weights on OneDrive (likely blocked) | MIT code; no separate weights licence |
| Sauvola/Niblack local thresholds (scikit-image) | **Faithful** but hard binary | Good; prone to thinning or broken hairlines | Seconds | pip | BSD |
| Learned binarization (SauvolaNet, GDB, DocRes) | Learned; mostly stays on observed ink | Best scores on DIBCO benchmarks | GPU helpful | GitHub | Varies; check each repo |
| Soft alpha ink layer (background division + tone curve) | **Faithful** (keeps greyscale edges) | Best for compositing/recolouring | Seconds | pip | Your own code |
| Potrace (outline tracing) | Faithful **at source scale**; smooths edges | Excellent for fonts/vector display | Fast | apt / pip wrappers | **GPL-2.0** (tool only; traced outputs are yours)\[19\]\[20\] |
| VTracer | Faithful at source scale; colour aware | Good; more nodes | Fast | `pip install vtracer` | MIT\[21\] |
| AutoTrace centerline / skeletonization | **Less faithful:** discards stroke width | Useful only for monoline/stroke animation | Fast | apt/build | GPL program / LGPL library\[22\] |
| Real-ESRGAN (x2plus/x4plus, ncnn-vulkan) | **Invents** texture/strokes | Crisp; risk of thickening and merging | Fast on GPU/Vulkan; slow on CPU | Weights on **GitHub releases** | BSD-3-Clause\[23\]\[24\] |
| SwinIR / HAT | Classical-PSNR models: mild; GAN variants: **invent** | High PSNR (classical) | Slow on CPU | SwinIR weights on GitHub releases; HAT on Google Drive/Baidu (likely blocked) | Apache-2.0 code |
| Diffusion upscalers (SUPIR, SeedVR2, PASD) | **Invent most** | Very sharp, high hallucination risk on text | Very slow; needs a 24 GB+ GPU | Mostly Hugging Face | SUPIR **non-commercial**; SeedVR2 Apache-2.0\[25\]\[26\]\[27\] |
| Kraken / eScriptorium HTR | n/a (reads text, doesn't change pixels) | Strong once fine-tuned on your hand | Training: GPU or Apple Silicon helpful | pip / Docker | Apache-2.0 (Kraken) |
| Transkribus | n/a | Strong; easy training | Cloud | Web only | Proprietary, credit-based\[28\] |
| VLMs (Gemini, GPT, Claude, Qwen-VL) | n/a; can **hallucinate readings** | Best zero-shot on modern English | API | API (may be blocked in sandbox) | Proprietary API terms; Qwen open weights |

## Details

### A. Classical, faithful cleanup (recommended defaults)
1. **Work from the best source per page.** For each page, compare pixel dimensions of the web crop and the corresponding September 2015 spread, and choose the higher-resolution one as the source for derivatives. Record the choice in the manifest. Note that the September 2015 spreads already have a capture date that is different from the pages' writing dates.
2. **Geometry.** Apply deskew as a single rotation at the highest bit depth, with one Lanczos resample (or a 90° lossless rotation if possible). For spreads, use ScanTailor Advanced to split pages and run manual or auto dewarp; its GPU dewarp path is designed to be "bit-exact with the CPU output."\[29\] For photographed curls, use page-dewarp or UVDoc via `uvdoc-onnx`, which bundles MIT weights and needs no torch.\[30\] Do all geometric operations in one combined warp so the image is resampled only once.
3. **Lighting and background normalisation.** Estimate the paper background with a large median filter, morphological closing or a Gaussian blur (window larger than the stroke width), then divide the image by it. This is the same idea as ScanTailor's "normalize illumination" option.\[31\] Keep 16-bit through this step.
4. **Contrast.** Use a global tone curve or levels adjustment. Avoid CLAHE with strong clip limits on the faithful tier, because it can amplify paper grain into pseudo-strokes.
5. **Denoise and sharpen.** Use a light bilateral or non-local-means denoise, and at most a small-radius unsharp mask. FADGI lists "over sharpening" among enhancements to avoid. Record the amounts in the manifest.
6. **Bleed-through/show-through.** The reliable methods are *non-blind*: they need both recto and verso scans, registered to each other, and they classify pixels using the joint recto-verso intensity histogram.\[32\] Examples are Rowley-Brooke et al., CVPR 2013, and the blind-source-separation and sparse-inpainting work by Tonazzini et al.\[33\]\[34\]\[35\] Because your spreads show facing pages, not reverse sides, you probably lack registered versos. Faint show-through can usually be pushed under the paper tone with a background-division plus tone curve. Do not use inpainting for the faithful tier, because inpainting is infill.
7. **Colour vs greyscale.** Keep RGB for masters and the faithful tier: ink colour, pencil vs pen, and coloured ruling all carry information. Ruled lines can often be separated by colour (blue/red ruling vs black/blue ink). Do this in a channel or Lab colour space, and only in derivatives. Never remove ruling where it crosses ink, because that is infill.
8. **Binarization evidence.** Plain Sauvola remains a solid baseline but does not win DIBCO. For example, on DIBCO 2011 Sauvola scores F-measure 82.1 vs Howe 91.7, and learned methods (GDB, SauvolaNet, DeepOtsu) lead on recent DIBCO sets. DeepOtsu's authors note that their method "misses the weak ink strokes."\[36\] For your purposes, prefer a soft alpha (section B) over any hard binarization. Use binarization only as a QA tool and as font-tracing input.

### B. Transparent ink layer (soft matting)
After background division, map the luminance L to ink opacity with a smooth ramp: α = clip((L_paper − L) / (L_paper − L_ink), 0, 1), optionally with a gamma. Then store the ink colour (or a single recolourable value) plus α as a 16-bit RGBA PNG/TIFF. This keeps anti-aliased edges, pressure variation and hairlines that hard thresholds destroy. It is deterministic and invertible enough to audit: composited back over the estimated paper, it should reproduce the cleaned page within a small error. For the canvas piece this is the best "faithful" display asset. It recolours cleanly and composites at any zoom up to the source resolution.

### C. Vectorization
- **Outline tracing (Potrace, VTracer)** preserves stroke width and is the right choice for fonts, because fonts are filled outlines. Potrace's own FAQ says to "scan your image at a higher resolution… in greyscale, and use… mkbitmap" before tracing.\[37\] In other words, vector quality is capped by source resolution. Potrace is GPL-2.0, but the output SVGs are not encumbered.
- **Where tracing helps:** infinite zoom without pixelation, small file sizes and clean font contours.
- **Where it harms:** it smooths corner jitter, ink pooling and pen texture. Its output looks "cleaner than the paper," which is a stylisation. Label vector display layers accordingly.
- **Centerline tracing** (AutoTrace, skeletonize) throws away stroke width. Potrace explicitly does not do it.\[37\]\[38\] Use it only for stroke-order or animation effects, never for font masters or deposits.

### D. AI super-resolution: practical limits and hosting
- **Where invention starts:** with sources at or below roughly 150 ppi, or where x-height is under about 10–12 px, the model lacks the evidence to resolve letter identity. That is exactly where TGSR locates hallucination ("on extremely small text, precision more than doubles" once suppressed).\[39\] At 300 ppi and above, a ×2 PSNR-oriented model (SwinIR classical, RealESRNet) is mostly sharpening. GAN and diffusion models still add texture. These thresholds are my engineering judgement extrapolated from the scene-text literature, not a published handwriting benchmark. Verify them with the trial plan.
- **Scale factors:** ×2 is the sensible ceiling for any display use. ×4 is where published SR work reports instability and hallucination. Diffusion upscalers should be presumed to invent at any scale.
- **Weights access from the sandbox:**
  - Real-ESRGAN `.pth` files and the realesrgan-ncnn-vulkan binaries are on **GitHub releases** (BSD-3).\[23\]\[40\]\[41\]
  - SwinIR weights are on GitHub releases (Apache-2.0).\[42\]
  - HAT weights are on Google Drive/Baidu.\[43\]
  - DocRes weights are on OneDrive.\[44\]
  - SUPIR, SeedVR2 and TrOCR are primarily on **Hugging Face**.\[45\]\[46\]
  - Expect the last three groups to be blocked in the sandbox. Run them **locally on the Mac**. Real-ESRGAN ncnn-vulkan has a macOS build; SeedVR2 needs about 24 GB+ of VRAM and is impractical on most Macs.\[25\]
  - None of the official SwinIR, HAT or DocRes repos states a separate licence for the weights. The permissive readings come from third-party catalogues, so record the exact weight file hash and source URL.\[47\]\[48\]
- **Licensing for a sellable artwork:** SUPIR's declaration restricts use "strictly for non-commercial purposes" without written permission, so exclude it.\[27\] Real-ESRGAN (BSD-3) and SeedVR2 (Apache-2.0) are permissive.\[49\]\[50\] Separately, a display image whose detail was generated by AI is not your handwriting. Keep it out of anything presented as the original.

### E. HTR workflow for the 306 uncertain readings
1. Segment lines with Kraken's baseline segmenter, or reuse your existing line boxes.
2. **Ground truth:** you already have a verified transcription. Export the certain lines (excluding the 306) as ALTO/PAGE XML, which yields hundreds to thousands of lines from one hand. That exceeds both the Digital Relics practitioner claim that "a few hundred lines of a single scribe's hand" can produce a strong Kraken model and Kraken's official training guidance that a small-script model "requires at least 800 lines."
3. Fine-tune Kraken (`ketos train` from a base model) on a GPU or Apple Silicon machine.\[51\] Hold out about 10% of pages for an honest CER, and report test CER, not validation CER.
4. Run the fine-tuned model and one VLM (with a prompt instructing literal, diplomatic transcription that marks strike-throughs and insertions) on the 306 line crops. **Use the faithful-tier crops, never upscaled ones.**
5. **Realistic expectations:** for modern mixed cursive and print from one writer, single-digit CER on clean lines is plausible once fine-tuned. Strike-throughs, interlinear insertions and marginalia will dominate the errors, and VLMs tend to silently "correct" spelling. Uncertain readings are, by selection, the hardest lines, so expect machine agreement on perhaps a minority of them. Treat that as a hypothesis to measure, not a promise.
6. **Preprocessing and HTR:** modern HTR engines are trained on greyscale/colour line images. Mild background flattening helps; hard binarization and aggressive sharpening usually don't. Older studies found that SR mainly helps recognisers when the source is very low resolution: Pandey & Ramakrishnan (arXiv 1701.08835) raised OCR word accuracy on 75 dpi Tamil images from 59.6% (bicubic) to 62.9%, and that was for printed text.

### F. Handwriting-to-font pipeline
- **Source:** the faithful tier at the highest native resolution available (or a new 600 ppi scan), never upscaled images.
- **Harvesting:** for each target glyph, collect 3–10 real instances from the journal using the transcription alignment, i.e., search the verified text for "X", "Q", "&" and so on, and crop from the line boxes. Normalise only by scale and baseline. Do not redraw.
- **Weak glyphs** (X, digits, Q, Z, V, K, G, !, ;, ", (, ), &): these are rare in prose, so the journal may hold only a few instances. Where it holds none, the honest options are (a) a new sample sheet written by the author with the same pen and paper type (Calligraphr-style template), or (b) leaving them as designed glyphs and documenting that. AI-synthesised letterforms should not stand in.
- **Tracing:** use the 16-bit alpha layer, threshold at the 50% opacity contour, then trace with Potrace (in FontForge's autotrace import or via the CLI) or VTracer. Keep stroke width. Use modest corner and curve smoothing, check the node count, and compare each traced outline against the source bitmap overlay.
- **Assembly:** use FontForge (GPL; scriptable in Python) or fontTools/ufoLib2 (MIT) to build a UFO and compile with fontmake. Put the harvested variants into a `calt` cycling scheme (a deterministic rotation, so adjacent repeats differ) plus ligatures for frequent joins (th, st, ff). This mirrors how commercial handwriting fonts use contextual alternates.\[52\]\[53\]\[54\]

### G. Web delivery and the three-tier structure
- **Tiling:** `vips dzsave` writes DeepZoom, Zoomify, Google or **IIIF (v2 and v3) layouts** directly, and can `--skip-blanks`.\[55\]\[56\] Pyramidal TIFF (`vips tiffsave --tile --pyramid`) suits an IIIF image server.\[57\] OpenSeadragon displays DZI/IIIF statically, with no server needed.
- **Formats:** handwriting is high-contrast, edge-dominated content where lossy codecs ring or blur at stroke edges. Use lossless WebP or PNG for the alpha ink tiles. For colour page tiles, use WebP/AVIF at high quality and inspect deep-zoom tiles at 100% for halos. I could not source a handwriting-specific WebP-vs-AVIF benchmark, so decide visually in the trial.
- **Manifest per derivative:** record the master SHA-256 (already have), derivative SHA-256, tier (`master` / `faithful` / `display-generative` / `display-vector`), source file (page crop vs spread), ordered list of operations with every parameter, tool names and exact versions (`pip freeze`, `vips --version`, git commit), model weight file and its SHA-256 (for AI tiers), date, platform and random seed. Generate derivatives with a script so the recipe is the code. Byte-level reproducibility of float operations across machines is not guaranteed, so record platform, verify with perceptual tolerances, and treat the master hash as the immutable anchor.
- **Copyright deposit PDFs:** for unpublished works the Copyright Office accepts an uploaded electronic complete copy (PDF is an accepted format) and "strongly encourages" digital deposits for unpublished works.\[58\]\[59\] Use faithful-tier page images plus the text layer. Excluding any AI-upscaled imagery also avoids the separate question of disclosing AI-generated material in a registration. This is not legal advice.

## Recommendations: end-to-end pipeline

**Tier 0 – Master (untouched).** Originals plus the existing SHA-256 manifest. Mount read-only and verify hashes before and after every run. If rescanning: 600 ppi (pages <A5) or 400 ppi, 16-bit RGB TIFF, colour target, flat, even light, no in-scanner sharpening. The new scans become additional masters with their own hashes.

**Tier 1 – Faithful (transcription, font, deposit, HTR).**
1. Choose the best source (page crop vs spread) by measured resolution.
2. Run one combined geometric transform (deskew + split + optional dewarp: ScanTailor Advanced, page-dewarp or UVDoc), resampled once with Lanczos.
3. Apply background division (illumination flattening), a global tone curve and optional light NL-means denoise. No inpainting, no infill.
4. Outputs:
   - (a) a 16-bit RGB TIFF "clean page";
   - (b) a 16-bit RGBA soft ink layer;
   - (c) a QA-only binarized mask (Sauvola);
   - (d) line crops for HTR;
   - (e) deposit PDF = Tier 1 images + text.

**Tier 2 – Display.**
- **2a (vector, preferred for the canvas at extreme zoom):** a Potrace/VTracer SVG from the Tier-1 alpha, labelled "vector rendering."
- **2b (raster):** a Tier-1 alpha upscaled ×2 with Lanczos, then tiled with `vips dzsave --layout iiif3`.
- **2c (optional, generative):** Real-ESRGAN x2plus or SwinIR, run on the Mac, only for pages that pass the trial checks. Store it in a separate folder, label it in the manifest and UI as "AI-enhanced, not the original ink," and never feed it back into Tiers 1 or 2a.

## Trial plan (about one to two days)
1. **Select 8 pages:** 3 clean, 2 with dense small writing, 1 with strike-throughs and insertions, 1 with visible show-through or ruling, and 1 page that exists both as a crop and in a spread.
2. **Produce for each page:** Tier-1 clean; Lanczos ×2; Real-ESRGAN x2plus; SwinIR (classical and real-GAN) ×2. Optionally add one diffusion upscaler run locally, as a negative control.
3. **Objective checks for invention:**
   - **Downsample consistency:** shrink every ×2 output back to source size with the same kernel and compute PSNR, SSIM and max absolute difference against the source. Lanczos passes almost perfectly; large residuals mean added content. Save the residual heat-maps.
   - **Ink topology:** binarize source and output (at matched scale) with the same Sauvola parameters. Compare connected-component counts (merges and splits), Euler number (closed loops in e/a/o) and skeleton length.
   - **Stroke width:** median and 90th-percentile stroke width from the distance transform on the skeleton. A rise of more than about 10% indicates thickening.
   - **HTR delta:** run the fine-tuned Kraken model and the VLM on identical line crops from each variant. If CER improves only on the SR version, check whether the "improvement" is the model reading invented strokes. Compare against your verified transcription.
   - **Blind visual A/B:** the author reviews randomized crops at 400% and flags any letter that "isn't how I wrote it."
4. **Decision rule:** a generative method is allowed in Tier 2c only if it produces zero author-flagged letterform changes, no topology changes on the test pages, and stroke-width drift within about 10%. Otherwise ship Lanczos plus vector.
5. **Also test:** lossless WebP vs high-quality AVIF tiles at the deepest zoom level for halos and file size.

## Caveats and risks
- **Evidence strength:**
  - *Well established:* generative SR hallucinates text, especially small or out-of-distribution text (multiple 2025–2026 papers); FADGI and Metamorfoze capture specifications; Potrace's limits; the licences listed.
  - *Uncertain or anecdotal:* the ppi and x-height thresholds where invention starts on handwriting (no handwriting CER benchmark exists); vendor CER claims (Transkribus); third-party weight-licence readings; the reported August 2026 Kraken 7.1 multilingual base models (secondary source only).\[60\]
- **Upscaling cannot recover information** that the web crops discarded. If the spreads are higher resolution, they are your real masters for those pages.
- **Dewarping models are learned.** UVDoc only resamples, but a wrong warp field can still bend letterforms. Check line straightness and overlay against the source.
- **VLM readings can be fluent and wrong,** and the 2025 benchmark found they don't reliably self-correct.\[13\] Never auto-accept them.
- **Sandbox constraints:** Hugging Face, Google Drive, OneDrive and Baidu-hosted weights may be unreachable. Real-ESRGAN and SwinIR (GitHub releases) and uvdoc-onnx (pip) are the safe in-sandbox options. Run Kraken training, diffusion models and VLM checks locally or through API access you control.
- **Licensing:** avoid SUPIR (non-commercial). Potrace, ScanTailor, AutoTrace and FontForge are GPL tools; their outputs are yours, but don't embed or redistribute the tools inside a sold product without GPL compliance. libvips is LGPL.\[16\]\[22\]\[61\] Record every weight file's source and hash.
- **Reproducibility:** pin versions. Floating-point outputs can differ slightly across CPU/GPU, so the manifest should record the platform and accept tolerance-based verification for derivatives. Bit-exactness is guaranteed only for the masters.

## Sources

1. <https://www.digitizationguidelines.gov/guidelines/FADGI%20Technical%20Guidelines%20for%20Digitizing%20Cultural%20Heritage%20Materials_3rd%20Edition_05092023.pdf>
2. [i June 2022 DRAFT 3.5 Technical Guidelines for Digitizing](https://www.digitizationguidelines.gov/guidelines/DRAFT%20Technical%20Guidelines%20for%20Digitizing%20Cultural%20Heritage%20Materials%20-%203rd%20Edition.pdf)
3. <https://arxiv.org/html/2610.14281>
4. [Text-Aware Real-World Image Super-Resolution via Diffusion Model with Joint Segmentation Decoders](https://arxiv.org/html/2506.04641)
5. [Text-Aware Real-World Image Super-Resolution via Diffusion Model with Joint Segmentation Decoders](https://arxiv.org/pdf/2506.04641)
6. <https://arxiv.org/pdf/2506.06953>
7. [Scene Text Image Super-Resolution in the Wild](https://arxiv.org/pdf/2005.03341)
8. [Diffusion-based Blind Text Image Super-Resolution](https://arxiv.org/pdf/2312.08886)
9. [What DPI to Scan Old Documents: 300, 400 or 600?](https://www.tryleo.ai/resources/archives-digitization-and-metadata-workflows/what-dpi-to-scan-old-documents)
10. [1 RECORDS MODERNIZATION INSIGHTS FADGI Guidelines and Compliance](https://www.fbcinc.com/source/virtualhall_images/2024_Virtual_Events/USDA_Innovation/QAI/AsktheExpert_FADGI_whitepaper_061124.pdf)
11. [Reduce, Reuse, ReFADGI: Updates to FADGI Standards for 2023](https://andersonarchival.com/blog/2023-fadgi-updates/)
12. [Version 2.0 - Preservation Imaging](https://preservationimaging.com/version-2/)
13. [Benchmarking large language models for handwritten text recognition](https://doi.org/10.1108/JD-03-2025-0082)
14. [AI Model Training — Train Custom HTR Models](https://www.transkribus.org/ai-training)
15. [Character Error Rate (CER) — The Standard Metric for Transcription Accuracy](https://www.transkribus.org/character-error-rate-cer-explained)
16. [github.com](https://github.com/Stravito/libvips)
17. [Ubuntu Manpage: scantailor-cli - a post-processing tool for scanned pages](https://manpages.ubuntu.com/manpages/bionic/man1/scantailor-cli.1.html)
18. [\[2405.04408\] DocRes: A Generalist Model Toward Unifying Document Image Restoration Tasks](https://arxiv.org/abs/2405.04408)
19. [GitHub - skyrpex/potrace: \[mirror\] Tool for tracing a bitmap, which means, transforming a bitmap into a smooth, scalable image · GitHub](https://github.com/skyrpex/potrace)
20. [Potrace](https://potrace.sourceforge.net/)
21. [VTracer: Python Binding](https://pypi.org/project/vtracer/)
22. [How Image Tracing Works: Inside Image Trace, Potrace and VTracer](https://www.vktrstudio.com/insights/how-image-tracing-works)
23. [GitHub - xinntao/Real-ESRGAN: Real-ESRGAN aims at developing Practical Algorithms for General Image/Video Restoration. · GitHub](https://github.com/xinntao/real-esrgan)
24. [Real-ESRGAN Guide (2026): Weights, Downloads, GUI, ncnn-vulkan](https://aireiter.com/blog/real-esrgan-guide-download-gui)
25. [SeedVR2 Upscaler for Video and Images](https://weirdwonderfulai.art/resources/seedvr2-upscaler-for-video-and-images/)
26. [SUPIR vs SeedVR2: Image Restoration or Video](https://seedvr2.net/supir-vs-seedvr2)
27. [GitHub - Fanghua-Yu/SUPIR: SUPIR aims at developing Practical Algorithms for Photo-Realistic Image Restoration In the Wild. Our new online demo is also released at suppixel.ai. · GitHub](https://github.com/Fanghua-Yu/SUPIR)
28. [Assessing advanced handwritten text recognition engines for digitizing historical documents](https://link.springer.com/article/10.1007/s42803-025-00100-0)
29. [Run the dewarp area mapping on the GPU by harshmaur · Pull Request #5 · harshmaur/scantailor-advanced · GitHub](https://github.com/harshmaur/scantailor-advanced/pull/5)
30. [GitHub - klopstack/uvdoc-onnx: UVDoc document dewarping (crumpled-paper flattening) via ONNX Runtime — no torch required. MIT-licensed model + MIT glue, bundled parity-checked weights. · GitHub](https://github.com/klopstack/uvdoc-onnx)
31. [scantailor-cli(1) — scantailor — Debian testing — Debian Manpages](https://manpages.debian.org/testing/scantailor/scantailor-cli.1)
32. [(PDF) A Non-parametric Framework for Document Bleed-through Removal](https://www.academia.edu/77251576/A_Non_parametric_Framework_for_Document_Bleed_through_Removal)
33. [A Non-Parametric Framework for Document Bleed-Through Removal](https://openaccess.thecvf.com/content_cvpr_2013/papers/Rowley-Brooke_A_Non-parametric_Framework_2013_CVPR_paper.pdf)
34. [Fast correction of bleed-through distortion in grayscale documents by a blind source separation technique](https://www.researchgate.net/publication/225117978_Fast_correction_of_bleed-through_distortion_in_grayscale_documents_by_a_blind_source_separation_technique)
35. [Non-Local Sparse Image Inpainting for Document Bleed-Through Removal](https://doi.org/10.3390/jimaging4050068)
36. [DeepOtsu: Document Enhancement and Binarization using Iterative Deep Learning](https://arxiv.org/pdf/1901.06081)
37. [Peter Selinger: Potrace FAQ - SourceForge](https://potrace.sourceforge.net/faq.html)
38. [Centerline trace - Potrace / Discussion / Help](https://sourceforge.net/p/potrace/discussion/300717/thread/0f6c5b22/)
39. [TGSR: Text-Grounded Diffusion for Faithful Image Super-Resolution](https://arxiv.org/html/2610.14281v1)
40. [Release Models v1 · AbdifatahWebDev/b-models · GitHub](https://github.com/AbdifatahWebDev/b-models/releases/tag/models-v1)
41. [https://github.com/xinntao/Real-ESRGAN](https://awesome.ecosyste.ms/projects/github.com/xinntao/Real-ESRGAN)
42. [GitHub - JingyunLiang/SwinIR: SwinIR: Image Restoration Using Swin Transformer (official repository) · GitHub](https://github.com/JingyunLiang/SwinIR)
43. [GitHub - XPixelGroup/HAT: CVPR2023 - Activating More Pixels in Image Super-Resolution Transformer TPAMI - HAT: Hybrid Attention Transformer for Image Restoration · GitHub](https://github.com/XPixelGroup/HAT)
44. [GitHub - ZZZHANG-jx/DocRes: \[CVPR 2024\] DocRes: A Generalist Model Toward Unifying Document Image Restoration Tasks](https://github.com/ZZZHANG-jx/DocRes)
45. [ByteDance-Seed/SeedVR2-3B · Hugging Face](https://huggingface.co/ByteDance-Seed/SeedVR2-3B)
46. [ByteDance-Seed/SeedVR2-7B · Hugging Face](https://huggingface.co/ByteDance-Seed/SeedVR2-7B)
47. [SwinIR: run 4x image super-resolution in LibreYOLO](https://www.libreyolo.com/docs/models/swinir)
48. [8x SwinIR-M-x8 (classicalSR-DIV2K-s64w8) - OpenModelDB](https://openmodeldb.info/models/8x-classicalSR-DIV2K-s64w8-SwinIR-M)
49. [Real-ESRGAN/LICENSE at master · xinntao/Real-ESRGAN · GitHub](https://github.com/xinntao/Real-ESRGAN/blob/master/LICENSE)
50. [GitHub - ByteDance-Seed/SeedVR: Repo for SeedVR2 (ICLR2026) & SeedVR (CVPR2025 Highlight) · GitHub](https://github.com/ByteDance-Seed/SeedVR)
51. [Train Your Own OCR/HTR Models with Kraken, part 1](https://digitalorientalist.com/2023/09/26/train-your-own-ocr-htr-models-with-kraken-part-1/)
52. [Creating Connecting Handwritten Fonts](https://www.high-logic.com/font-editor/fontcreator/tutorials/creating-handwritten-fonts-with-contextual-alternates)
53. [FontCrafter: Create Your Handwriting Font for Free](https://arcade.pirillo.com/fontcrafter.html)
54. [Handwritten Fonts: The 23 Best, and Why Most Look Fake](https://www.designrush.com/best-designs/logo/handwritten-fonts)
55. [Vips](https://www.libvips.org/API/8.17/making-image-pyramids.html)
56. [Vips.Image.dzsave - libvips](https://www.libvips.org/API/8.17/method.Image.dzsave.html)
57. [Images](https://iipimage.sourceforge.io/documentation/images)
58. [Circular 2 Copyright Registration](https://www.copyright.gov/circs/circ02.pdf)
59. [Copyright Submission Guidelines](https://www.legalzoom.com/articles/copyright-submission-guidelines)
60. [Transcribing Handwritten Documents // Reliable AI for Humanists](http://amaranth.unm.edu/reliable-ai//sessions/transcribing-handwritten-documents/)
61. [Potrace](https://en.wikipedia.org/wiki/Potrace)
