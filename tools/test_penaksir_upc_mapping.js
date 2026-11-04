'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const Alias = require('../lib/sotk-job-aliases.js');

const fixtures = [
  { org: '12472', unitType: 'UPC/UPS', jobCode: 'PPC', jobName: 'Penaksir UPC', positionName: 'Penaksir UPC pada UPC SUKARESMI pada Kantor Cabang Cikarang', positionType: 'Definitif' },
  { org: '12391', unitType: 'UPC/UPS', jobCode: 'PPC', jobName: 'Penaksir UPC', positionName: 'Penaksir UPC pada UPC KONDANG JAYA pada Kantor Cabang Karawang', positionType: 'Masa Evaluasi' },
  { org: '60125', unitType: 'UPC/UPS', jobCode: 'PPC', jobName: 'Penaksir UPC', positionName: 'Penaksir UPS pada UPS CIPAYUNG pada Kantor CPS Dewi Sartika', positionType: 'Masa Evaluasi' }
];

// Test the exact alias conditions observed in the uploaded employee workbook.
for (const employee of fixtures) {
  const before = { ...employee };
  const mapped = Alias.normalizeCurrentJob({
    level: 'C', unitType: employee.unitType, jobCode: employee.jobCode,
    jobName: employee.jobName, positionName: employee.positionName
  });
  assert.equal(mapped.jobCode, 'PSR');
  assert.equal(mapped.jobName, 'Penaksir');
  assert.equal(mapped.alias, 'PPC_TO_PSR');
  assert.deepEqual(employee, before, 'Raw employee input must remain unchanged');
  assert.equal(Alias.matchesLegacyPositionPrefix('PSR', 'Penaksir UPC/S', employee.positionName), true);
}

// The same text must not be remapped outside UPC/UPS or for a different code.
assert.equal(Alias.normalizeCurrentJob({
  level: 'C', unitType: 'CP/CPS', jobCode: 'PPC', jobName: 'Penaksir UPC',
  positionName: 'Penaksir UPC pada Kantor Cabang X'
}).jobCode, 'PPC');
assert.equal(Alias.normalizeCurrentJob({
  level: 'C', unitType: 'UPC/UPS', jobCode: 'XYZ', jobName: 'Penaksir UPC',
  positionName: 'Penaksir UPC pada UPC X'
}).jobCode, 'XYZ');
assert.equal(Alias.normalizeCurrentJob({
  level: 'C', unitType: 'UPC/UPS', jobCode: 'PPC', jobName: 'Penaksir UPC',
  positionName: 'Pengelola Agunan 1 pada UPC X'
}).jobCode, 'PPC');
assert.equal(Alias.matchesLegacyPositionPrefix('AO', 'Penaksir UPC/S', 'Penaksir UPC pada UPC X'), false);

// Cross-check all three uploaded examples against the actual SOTK preload.
const browserWindow = {};
vm.runInNewContext(fs.readFileSync(path.join(__dirname, '..', 'data.js'), 'utf8'), { window: browserWindow });
const P = browserWindow.SOTK_PRELOAD;
assert.ok(P && Array.isArray(P.SOTK_CABANG) && Array.isArray(P.UNIT_MASTER_CABANG));
const cabHeaders = P.SOTK_CABANG_H;
const unitHeaders = P.UNIT_MASTER_CABANG_H;
const asObjects = (headers, rows) => rows.map(row => Object.fromEntries(headers.map((h, i) => [h, row[i]])));
const cab = asObjects(cabHeaders, P.SOTK_CABANG);
const units = asObjects(unitHeaders, P.UNIT_MASTER_CABANG);
for (const employee of fixtures) {
  const unit = units.find(row => String(row.UNIT_KEY) === employee.org);
  assert.ok(unit, `Unit Master missing for ${employee.org}`);
  assert.equal(unit.UNIT_TYPE, 'UPC/UPS');
  const formasi = cab.find(row => String(row['ORG CODE']) === employee.org && String(row['JOB CODE']) === 'PSR');
  assert.ok(formasi, `Penaksir/PSR formasi missing for ${employee.org}`);
  assert.equal(formasi['JOB NAME'], 'Penaksir');
}

console.log('PASS: 3 contoh Penaksir UPC/UPS (PPC) dipetakan ke keluarga formasi PSR/Penaksir; raw fields, non-UPC, dan kode lain tetap aman; referensi SOTK per outlet cocok.');
