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

## How the transform works

All the logic lives between the `// === TRANSFORM_BEGIN ===` / `// === TRANSFORM_END ===` markers inside `point-translator.html` — roughly 100 lines of vanilla JS, no libraries. The pipeline runs entirely in the browser when a file is selected.

### 1. Read the file
`FileReader.readAsText(file)` reads the selected CSV as a UTF-8 string. Status messages (`Reading…`, `Success…`, error) are written to a `<div id="status">` so the user gets feedback without opening the console.

### 2. Parse CSV (`parseCSV`)
- Detects a leading UTF-8 BOM (`﻿`), records its presence in a `hadBOM` flag, and strips it.
- Splits the text on `\r?\n` and pops trailing fully-empty lines.
- Splits each line on `,`. No quoted-field handling is needed — the input format guarantees plain comma-delimited values, possibly negative or in scientific notation (e.g. `-5.70E-05`).
- Returns `{ rows, hadBOM }`.

### 3. Detect the point count `N`
Scans **row 4** starting at column B (index 1) in strides of 3 — i.e. columns B, E, H, K, … Each non-empty cell is taken as a point number. Scanning stops at the first empty cell. `N` is the number found. Throws if `N === 0`.

### 4. Extract the per-point time values
Walks **row 6** (`Time in sec`). For each of the `N` points it takes the cell at index `1 + p*3` — the first value of each triplet group, which is the actual seconds figure. The 2nd and 3rd values in each triplet (minute and "Xs"-suffixed breakdown) are intentionally ignored.

### 5. Collect data rows
From row 8 onward, skips rows that are completely blank (every cell empty after trimming). The remaining rows are kept in their original order. Throws if zero data rows were found.

### 6. Validate the first data row
The validation gate that runs **before** any output is generated. The first data row must satisfy both:
- Non-empty cells after column A are divisible by 3, **and**
- That count is exactly `3 × N`.

If either fails, the transform throws an `Error` with the expected vs. actual counts; the page shows the error and **no output file is downloaded**.

### 7. Build the output rows
- **Rows 1–3** (`Project`, `File`, `Kinetic Engine…`) are passed through `trimPadHeaderRow`: trailing empty cells are removed, then the row is padded with empties up to width `N + 2`. This matches the byte-exact layout of the known-good output, where all rows share the same column count.
- **Row 4** is rebuilt as `['point', '', 1, 2, …, N]`.
- **Row 5** is rebuilt as `['Time in sec', '', t₁, t₂, …, tₙ]` using the values from step 4.
- **Data section** — three coordinate blocks emitted in order **X, Y, Z**. For each block, every collected data row is re-emitted as `[Name, coord, v₁, v₂, …, vₙ]`, where `vₖ` is read from the input data row at index `1 + (k-1)*3 + coordIndex`. So with `coordIndex = 0`, you pluck out X₁, X₂, …; with `1`, Y₁, Y₂, …; with `2`, Z₁, Z₂, …

### 8. Serialize and re-attach BOM
Rows are joined with `,` to form lines, lines joined with `\n`, and a trailing `\n` appended. If the input had a BOM, the same BOM character is prepended to the output so the output file round-trips identically to a Kinetic Engine-produced file.

### 9. Trigger a download
The result string is wrapped in a `Blob` of type `text/csv;charset=utf-8`. The script creates a hidden `<a>` with a `download` attribute set to `<input-filename>_output.csv`, programmatically clicks it, then revokes the object URL. No server round-trip — the file is built and saved entirely on the client.

### What the transform deliberately does **not** do

- **No number parsing.** All cell values stay as strings, end-to-end. Scientific notation and significant-digit precision are preserved exactly as they appear in the input.
- **No reordering of data rows** within a block — point names appear in the same order they appear in the input.
- **No external dependencies, no build step, no network calls.** Everything is inline in one HTML file so it works offline and from a `file://` URL.
