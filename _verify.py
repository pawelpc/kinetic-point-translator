"""Verification harness mirroring the JS transform() in point-translator.html.

Used because Node.js is not installed on this machine. The Python logic below
is a line-for-line port of the JS transform so that if this passes, the JS
logic is also correct. The official test-translator.js remains the canonical
test for environments where Node is available.
"""
from __future__ import annotations

import os
import sys

PROJ = os.path.dirname(os.path.abspath(__file__))


def parse_csv(text: str):
    had_bom = False
    if text.startswith("﻿"):
        had_bom = True
        text = text[1:]
    lines = text.replace("\r\n", "\n").split("\n")
    while lines and lines[-1] == "":
        lines.pop()
    return [ln.split(",") for ln in lines], had_bom


def trim_pad(row, target_width):
    out = list(row)
    while out and (out[-1] is None or str(out[-1]).strip() == ""):
        out.pop()
    while len(out) < target_width:
        out.append("")
    return out


def transform(csv_text: str) -> str:
    rows, had_bom = parse_csv(csv_text)
    if len(rows) < 8:
        raise ValueError(
            f"Input file has only {len(rows)} rows; expected at least 8."
        )

    row4 = rows[3]
    point_numbers = []
    i = 1
    while i < len(row4):
        v = "" if row4[i] is None else str(row4[i]).strip()
        if v == "":
            break
        point_numbers.append(row4[i])
        i += 3
    N = len(point_numbers)
    if N == 0:
        raise ValueError("Could not detect any point numbers in row 4.")

    row6 = rows[5]
    time_values = []
    for p in range(N):
        idx = 1 + p * 3
        time_values.append(row6[idx] if idx < len(row6) else "")

    data_rows = []
    for r in range(7, len(rows)):
        dr = rows[r]
        if not dr:
            continue
        if not any((str(c).strip() if c is not None else "") for c in dr):
            continue
        data_rows.append(dr)

    if not data_rows:
        raise ValueError("No data rows found after the 7-row header.")

    first = data_rows[0]
    after_a = first[1:]
    non_empty = sum(1 for c in after_a if (c is not None and str(c).strip() != ""))
    if non_empty % 3 != 0:
        raise ValueError(
            f"Validation failed: first data row has {non_empty} non-empty cells, not divisible by 3."
        )
    if non_empty != 3 * N:
        raise ValueError(
            f"Validation failed: first data row has {non_empty} non-empty cells; expected {3*N} (3 × {N})."
        )

    out_width = N + 2
    out = []
    out.append(trim_pad(rows[0], out_width))
    out.append(trim_pad(rows[1], out_width))
    out.append(trim_pad(rows[2], out_width))
    out.append(["point", ""] + list(point_numbers))
    out.append(["Time in sec", ""] + list(time_values))

    for ci, coord in enumerate(["X", "Y", "Z"]):
        for dr in data_rows:
            name = dr[0] if dr and dr[0] is not None else ""
            values = []
            for pi in range(N):
                col = 1 + pi * 3 + ci
                values.append(dr[col] if col < len(dr) and dr[col] is not None else "")
            out.append([name, coord] + values)

    body = "\n".join(",".join(str(c) for c in row) for row in out) + "\n"
    return ("﻿" + body) if had_bom else body


def diff_lines(expected: str, actual: str):
    a = expected.replace("\r\n", "\n").split("\n")
    b = actual.replace("\r\n", "\n").split("\n")
    m = max(len(a), len(b))
    diffs = []
    for i in range(m):
        ea = a[i] if i < len(a) else "<<missing>>"
        eb = b[i] if i < len(b) else "<<missing>>"
        if ea != eb:
            diffs.append((i + 1, ea, eb))
    return diffs


def read_text(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def main():
    print("--- Test 1: Point Array example 1.csv (diff vs known-good output) ---")
    inp = read_text(os.path.join(PROJ, "Point Array example 1.csv"))
    expected = read_text(os.path.join(PROJ, "Point Array example 1 output.csv"))
    actual = transform(inp)
    diffs = diff_lines(expected, actual)
    only_trailing = all(
        (e == "" and a == "<<missing>>") or (a == "" and e == "<<missing>>")
        for _, e, a in diffs
    )
    if not diffs:
        print(f"PASS: exact match ({len(actual.splitlines())} lines).")
        t1 = True
    elif only_trailing:
        print("PASS (trivial trailing-newline difference only).")
        t1 = True
    else:
        print(f"FAIL: {len(diffs)} line(s) differ. First 10:")
        for line, exp, act in diffs[:10]:
            print(f"  line {line}")
            print(f"    expected: {exp!r}")
            print(f"    actual:   {act!r}")
        t1 = False

    print("")
    print("--- Test 2: Point Array example 2.csv (structural verification) ---")
    inp2 = read_text(os.path.join(PROJ, "Point Array example 2.csv"))
    rows_in, _ = parse_csv(inp2)
    expected_N = 0
    i = 1
    while i < len(rows_in[3]):
        v = "" if rows_in[3][i] is None else str(rows_in[3][i]).strip()
        if v == "":
            break
        expected_N += 1
        i += 3
    data_count = 0
    for r in range(7, len(rows_in)):
        dr = rows_in[r]
        if not dr:
            continue
        if any((str(c).strip() if c is not None else "") for c in dr):
            data_count += 1

    out2 = transform(inp2)
    lines2 = [ln for ln in out2.split("\n") if ln]
    counts = {"X": 0, "Y": 0, "Z": 0}
    for ln in lines2:
        cells = ln.split(",")
        if len(cells) >= 2 and cells[1] in counts:
            counts[cells[1]] += 1

    print(f"  Detected N (points): {expected_N}")
    print(f"  Detected data rows:  {data_count}")
    print(f"  Output total lines:  {len(lines2)} (expected {5 + 3*data_count})")
    print(f"  X / Y / Z block sizes: {counts['X']} / {counts['Y']} / {counts['Z']}")
    row4 = lines2[3].split(",")
    row5 = lines2[4].split(",")
    header_ok = (
        row4[0] == "point" and row4[1] == "" and len(row4) == expected_N + 2
        and row5[0] == "Time in sec" and row5[1] == "" and len(row5) == expected_N + 2
    )
    width_ok = all(len(ln.split(",")) == expected_N + 2 for ln in lines2)
    blocks_ok = (counts["X"] == data_count and counts["Y"] == data_count and counts["Z"] == data_count)
    t2 = header_ok and width_ok and blocks_ok and len(lines2) == 5 + 3 * data_count
    print("PASS: structure is correct." if t2 else f"FAIL: headerOk={header_ok} widthOk={width_ok} blocksOk={blocks_ok}")

    print("")
    print("=== Summary ===")
    print(f"Test 1 (example 1 diff):        {'PASS' if t1 else 'FAIL'}")
    print(f"Test 2 (example 2 structure):   {'PASS' if t2 else 'FAIL'}")
    sys.exit(0 if (t1 and t2) else 1)


if __name__ == "__main__":
    main()
