const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');

const source = fs.readFileSync(path.join(__dirname, '..', 'app.js'), 'utf8');
const match = source.match(/function filterOutletClassRows\(rows, selectedClass\)\s*\{[\s\S]*?\n\}/);
assert.ok(match, 'The application must expose its outlet class filtering helper');
const classFilterCall = source.indexOf('cur=filterOutletClassRows(cur,st.kelasUpcUps)');
const cascadeOptions = source.indexOf('L.forEach((lb,i)=>{', classFilterCall);
assert.ok(classFilterCall >= 0 && cascadeOptions > classFilterCall,
  'The selected class must be applied before cascading location options are generated');
const context = {};
vm.runInNewContext(`${match[0]}\nthis.filterOutletClassRows = filterOutletClassRows;`, context);

const rows = [
  { kelasUpcUps: 'U1', p: ['Area A', 'UPC SATU'] },
  { kelasUpcUps: ' U1 ', p: ['Area B', 'UPS DUA'] },
  { kelasUpcUps: 'U2', p: ['Area A', 'UPC TIGA'] },
  { kelasUpcUps: 'u3', p: ['Area C', 'UPS EMPAT'] },
  { kelasUpcUps: '', p: ['Area A', 'CP LIMA'] }
];

const u1 = context.filterOutletClassRows(rows, 'U1');
assert.deepEqual(Array.from(u1, r => r.p[1]), ['UPC SATU', 'UPS DUA']);
assert.equal(context.filterOutletClassRows(rows, 'u2').length, 1);
assert.equal(context.filterOutletClassRows(rows, 'U4').length, 0);
assert.equal(context.filterOutletClassRows(rows, '').length, rows.length);

// The Outlet dropdown is built from the already-filtered rows in panel().
const outletOptions = [...new Set(u1.map(r => r.p[1]))].sort();
assert.deepEqual(outletOptions, ['UPC SATU', 'UPS DUA']);
assert.ok(!outletOptions.includes('UPC TIGA'), 'Outlet options from U2 must not leak into U1');
assert.ok(!outletOptions.includes('UPS EMPAT'), 'Outlet options from U3 must not leak into U1');

console.log('PASS: filter U1-U4 membatasi hasil dan opsi Outlet secara konsisten; normalisasi huruf/spasi dan kondisi tanpa filter juga benar.');
