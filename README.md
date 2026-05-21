# Kinetic Point Translator

A standalone, single-file HTML app that transforms Kinetic Engine Trans Point Array CSV files from an interleaved `X, Y, Z` layout into a coordinate-grouped layout (separate X, Y, and Z blocks).

## Use the hosted app

Open it in any modern browser — no install, no server, no dependencies:

**[point-translator.html](point-translator.html)**

(Or use the redirect at the repo root: `/`)

Steps:
1. Click the file picker and choose a Kinetic Engine Trans Point Array CSV.
2. The page validates the file (point count vs. data-row triplet count) and either reports a clear error or triggers a download of `<input-filename>_output.csv`.

## Files

| File | Purpose |
|------|---------|
| `point-translator.html` | The standalone app. All CSS/JS inline. Open directly in a browser. |
| `index.html`            | Redirect to `point-translator.html` for GitHub Pages root. |
| `test-translator.js`    | Node.js test harness — extracts the transform from the HTML and diffs against the known-good output. Run with `node test-translator.js`. |
| `_verify.py`            | Python port of the same transform, used to verify when Node.js isn't installed. Run with `python _verify.py`. |
| `Point Array example 1.csv` / `example 2.csv` | Sample input files. |
| `Point Array example 1 output.csv` | Known-good output for example 1, used by the diff test. |

## Input / output format

**Input** — fixed 7-row header, then data rows. Header rows:

1. `Project, …` — metadata
2. `File, …` — metadata
3. `Kinetic Engine Trans Point Array Data` — label
4. `point, 1, , , 2, , , 3, …` — point numbers at every 3rd column
5. `Time, 5m 18.043109s, …` — human-readable timestamps (dropped in output)
6. `Time in sec, 318.043109, 5, 18.043109s, …` — actual seconds at every 3rd column
7. `PHYS, PHYS, …` — type label (dropped in output)

Each data row: `Name, X₁, Y₁, Z₁, X₂, Y₂, Z₂, …`.

**Output** — 5 header rows (the 3 metadata rows, then `point` and `Time in sec` rows with values in consecutive columns) followed by three coordinate blocks: all X rows, then all Y rows, then all Z rows. Numeric precision and scientific notation are preserved exactly.

## Validation

Before transforming, the program checks that:

- N point numbers can be detected in row 4 at columns B, E, H, …
- The first data row contains exactly `3 × N` non-empty value cells

If either check fails, an error is shown on the page with expected vs. actual counts and no output file is produced.
