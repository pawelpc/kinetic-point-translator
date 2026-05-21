#!/usr/bin/env node
// Test harness for point-translator.html
// Extracts the transform function from the HTML file and runs it against the example CSVs.

const fs = require('fs');
const path = require('path');

const PROJ_DIR = __dirname;
const HTML_PATH = path.join(PROJ_DIR, 'point-translator.html');

// --- Extract the transform code block from the HTML file ---
const html = fs.readFileSync(HTML_PATH, 'utf8');
const m = html.match(/\/\/ === TRANSFORM_BEGIN ===([\s\S]*?)\/\/ === TRANSFORM_END ===/);
if (!m) {
  console.error('FAIL: could not find TRANSFORM_BEGIN / TRANSFORM_END markers in ' + HTML_PATH);
  process.exit(1);
}
// Evaluate in this scope so transform() becomes available
eval(m[1]); // eslint-disable-line no-eval

// --- Helpers ---
function readUtf8(p) {
  return fs.readFileSync(p, 'utf8');
}

function diffLines(expected, actual) {
  const a = expected.split(/\r?\n/);
  const b = actual.split(/\r?\n/);
  const max = Math.max(a.length, b.length);
  const diffs = [];
  for (let i = 0; i < max; i++) {
    const ea = a[i] === undefined ? '<<missing>>' : a[i];
    const eb = b[i] === undefined ? '<<missing>>' : b[i];
    if (ea !== eb) diffs.push({ line: i + 1, expected: ea, actual: eb });
  }
  return diffs;
}

function blockCounts(outputCsv) {
  const lines = outputCsv.split(/\r?\n/).filter(l => l.length > 0);
  const counts = { X: 0, Y: 0, Z: 0 };
  for (const ln of lines) {
    const cells = ln.split(',');
    if (cells.length >= 2 && (cells[1] === 'X' || cells[1] === 'Y' || cells[1] === 'Z')) {
      counts[cells[1]]++;
    }
  }
  return { total: lines.length, counts };
}

// --- Test 1: full diff against the known-good output ---
function runDiffTest(inputName, expectedName) {
  console.log('--- Test 1: ' + inputName + ' (diff vs known-good output) ---');
  const inputPath = path.join(PROJ_DIR, inputName);
  const expectedPath = path.join(PROJ_DIR, expectedName);
  const input = readUtf8(inputPath);
  const expected = readUtf8(expectedPath);

  let output;
  try {
    output = transform(input); // eslint-disable-line no-undef
  } catch (err) {
    console.log('FAIL: transform threw: ' + err.message);
    return false;
  }

  // If the expected output omits the trailing newline, normalize both
  const expNorm = expected.replace(/\r\n/g, '\n');
  const outNorm = output.replace(/\r\n/g, '\n');

  const diffs = diffLines(expNorm, outNorm);
  if (diffs.length === 0) {
    console.log('PASS: output exactly matches expected (' + outNorm.split('\n').length + ' lines).');
    return true;
  }

  // Allow a trivial mismatch only on the trailing newline / final blank line
  const onlyTrailing = diffs.every(d =>
    (d.expected === '' && d.actual === '<<missing>>') ||
    (d.actual === '' && d.expected === '<<missing>>')
  );
  if (onlyTrailing) {
    console.log('PASS (trivial trailing-newline difference only).');
    return true;
  }

  console.log('FAIL: ' + diffs.length + ' line(s) differ. Showing up to 10:');
  diffs.slice(0, 10).forEach(d => {
    console.log('  line ' + d.line + ':');
    console.log('    expected: ' + JSON.stringify(d.expected));
    console.log('    actual:   ' + JSON.stringify(d.actual));
  });
  return false;
}

// --- Test 2: structural validation against example 2 ---
function runStructureTest(inputName) {
  console.log('--- Test 2: ' + inputName + ' (structural verification) ---');
  const input = readUtf8(path.join(PROJ_DIR, inputName));

  // Count expected N from input row 4
  const rows = input.split(/\r?\n/).map(l => l.split(','));
  let expectedN = 0;
  const r4 = rows[3] || [];
  for (let i = 1; i < r4.length; i += 3) {
    const v = (r4[i] == null ? '' : String(r4[i])).trim();
    if (v === '') break;
    expectedN++;
  }
  // Count data rows from input
  let dataRowCount = 0;
  for (let r = 7; r < rows.length; r++) {
    const row = rows[r] || [];
    if (row.length === 0) continue;
    const any = row.some(c => (c == null ? '' : String(c)).trim() !== '');
    if (any) dataRowCount++;
  }

  let output;
  try {
    output = transform(input); // eslint-disable-line no-undef
  } catch (err) {
    console.log('FAIL: transform threw: ' + err.message);
    return false;
  }

  const info = blockCounts(output);
  console.log('  Detected N (points): ' + expectedN);
  console.log('  Detected data rows:  ' + dataRowCount);
  console.log('  Output total lines:  ' + info.total + ' (expected ' + (5 + 3 * dataRowCount) + ')');
  console.log('  X / Y / Z block sizes: ' + info.counts.X + ' / ' + info.counts.Y + ' / ' + info.counts.Z);

  // Check header
  const outLines = output.split(/\r?\n/);
  const row4 = outLines[3].split(',');
  const row5 = outLines[4].split(',');
  const headerOk =
    row4[0] === 'point' && row4[1] === '' && row4.length === expectedN + 2 &&
    row5[0] === 'Time in sec' && row5[1] === '' && row5.length === expectedN + 2;

  const widthOk = outLines
    .filter(l => l.length > 0)
    .every(l => l.split(',').length === expectedN + 2);

  const blocksOk =
    info.counts.X === dataRowCount &&
    info.counts.Y === dataRowCount &&
    info.counts.Z === dataRowCount;

  const ok = headerOk && widthOk && blocksOk && info.total === 5 + 3 * dataRowCount;
  console.log(ok ? 'PASS: structure is correct.' : 'FAIL: structure issue detected.');
  if (!ok) {
    console.log('  headerOk=' + headerOk + ' widthOk=' + widthOk + ' blocksOk=' + blocksOk);
  }
  return ok;
}

// --- Run ---
const r1 = runDiffTest('Point Array example 1.csv', 'Point Array example 1 output.csv');
console.log('');
const r2 = runStructureTest('Point Array example 2.csv');

console.log('\n=== Summary ===');
console.log('Test 1 (example 1 diff): ' + (r1 ? 'PASS' : 'FAIL'));
console.log('Test 2 (example 2 structure): ' + (r2 ? 'PASS' : 'FAIL'));
process.exit((r1 && r2) ? 0 : 1);
